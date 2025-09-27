"""
convert one run's raw logs to clean CSVs and plots
inputs (using --run-id prefix):
  <run_id>_iperf.json
  <run_id>_rtt.txt
  <run_id>_cwnd.txt

outputs:
  <run_id>_throughput.csv  (time_s,throughput_mbps,retrans)
  <run_id>_rtt.csv         (time_s,rtt_ms)
  <run_id>_cwnd.csv        (time_s,cwnd_bytes,rtt_ms,bytes_in_flight)
  <run_id>_throughput.png
  <run_id>_rtt.png
  <run_id>_cwnd.png
  appends one metadata summary row to results.csv

how to use:
  (only after ensuring that the inputs <run_id>_iperf.json, <run_id>_rtt.txt, <run_id>_cwnd.txt exist)
  python3 analysis.py --run-id {id}


"""

import argparse, json, os, re, statistics, math, csv
import numpy as np
import matplotlib.pyplot as plt

# ---------- helpers ----------
def load_run_metadata(run_id: int, runs_csv: str) -> dict:
    with open(runs_csv, newline="") as f:
        for row in csv.DictReader(f):
            if int(row["run_id"]) == run_id:
                return {
                    "run_id": str(int(row["run_id"])),
                    "scenario": row["scenario"],
                    "link_setup": row["link_setup"],
                    "tcp_flavor": row["tcp_flavor"],
                    "background": row["background"],
                    "bidir": "yes" if row["bidir"].lower() in ("yes","true","1") else "no",
                    "trial": row["trial"],
                }
    raise ValueError(f"run_id {run_id} not found in {runs_csv}")

def write_csv(path, header, rows):
    newfile = not os.path.exists(path)
    with open(path, 'a') as f:
        if newfile:
            f.write(','.join(header) + '\n')
        for r in rows:
            f.write(','.join('' if v is None else str(v) for v in r) + '\n')

def plot_series(x, y, xlabel, ylabel, title, out_png):
    fig = plt.figure()
    plt.plot(x, y)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)

def percentile(sorted_vals, p):
    if not sorted_vals:
        return float('nan')
    k = (len(sorted_vals)-1) * p
    f = int(k)
    c = min(f+1, len(sorted_vals)-1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c]-sorted_vals[f]) * (k - f)


# ---------- parsers ----------

def parse_iperf_json(path):
    with open(path) as f:
        data = json.load(f)
    series = []
    retrans_list = []
    for itv in data.get("intervals", []):
        s = itv.get("sum", {})
        t0 = s.get("start", 0.0)
        mbps = (s.get("bits_per_second", 0.0) or 0.0)/1e6
        r = s.get("retransmits", 0) or 0
        series.append((t0, mbps, r))
        retrans_list.append(r)
    tputs = [x[1] for x in series]
    t_mean = statistics.fmean(tputs)
    t_p90  = percentile(sorted(tputs), 0.90)
    t_p95  = percentile(sorted(tputs), 0.95) 
    retrans_total = sum(retrans_list)
    return series, t_mean, t_p90, t_p95, retrans_total


def parse_rtt_txt(path):
    rtt_vals = []
    ts_pat   = re.compile(r'^\[(\d+\.\d+)\]')                 # ping -D timestamp
    val_pat  = re.compile(r'time[=<]([\d\.]+)\s*ms')          # per-echo RTT
    # summary lines at the end:
    txrx_pat = re.compile(r'(\d+)\s+packets transmitted,\s+(\d+)\s+received')
    loss_pat = re.compile(r'([\d\.]+)%\s+packet loss')

    tx = rx = None
    loss_percent = None

    with open(path) as f:
        for line in f:
            # collect per-echo RTT samples
            m = val_pat.search(line)
            if m:
                rtt = float(m.group(1))
                ts_match = ts_pat.match(line.strip())
                ts = float(ts_match.group(1)) if ts_match else None
                rtt_vals.append((ts, rtt))
                continue

            # capture the final ping statistics
            m_txrx = txrx_pat.search(line)
            if m_txrx:
                tx, rx = int(m_txrx.group(1)), int(m_txrx.group(2))
                continue

            m_loss = loss_pat.search(line)
            if m_loss:
                loss_percent = float(m_loss.group(1))
                continue

    plain = [v for _, v in rtt_vals]
    r_mean = statistics.fmean(plain) if plain else float("nan")
    r_p90  = percentile(sorted(plain), 0.90) if plain else float("nan")
    r_p95  = percentile(sorted(plain), 0.95) if plain else float("nan")

    # build rows with relative time axis
    if rtt_vals and rtt_vals[0][0] is not None:
        t0 = rtt_vals[0][0]
        rows = [(round((ts - t0), 3), v) for ts, v in rtt_vals]
    else:
        # fall back to 0.2s spacing if no -D timestamps
        rows, t = [], 0.0
        for _, v in rtt_vals:
            rows.append((round(t, 3), v))
            t += 0.2

    # if loss % line wasn't present but tx/rx were, compute it
    if loss_percent is None and tx and tx > 0 and rx is not None:
        loss_percent = (tx - rx) * 100.0 / tx

    return rows, r_mean, r_p90, r_p95, loss_percent


def parse_cwnd_txt(cwnd_txt_path):
    rows = []
    cur = {"cwnd_bytes": None, "rtt_ms": None}

    def flush_snapshot(t_index):
        if any(v is not None for v in cur.values()):
            rows.append([float(t_index), cur["cwnd_bytes"], cur["rtt_ms"]])

    re_cwnd = re.compile(r"\bcwnd:(\d+)\b")
    re_rtt  = re.compile(r"\brtt:([0-9]+(?:\.[0-9]+)?)")  # first number before slash

    t_index = 0
    with open(cwnd_txt_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                flush_snapshot(t_index)
                cur = {"cwnd_bytes": None, "rtt_ms": None}
                t_index += 1
                continue

            m = re_cwnd.search(line)
            if m:
                cur["cwnd_bytes"] = int(m.group(1))

            m = re_rtt.search(line)
            if m:
                cur["rtt_ms"] = float(m.group(1))

        # flush last block if file didn’t end with a blank line
        flush_snapshot(t_index)

    cw_vals = [r[1] for r in rows if r[1] is not None]
    cw_med = float(np.median(cw_vals)) if cw_vals else 0.0
    cw_p95 = float(np.percentile(cw_vals, 95)) if cw_vals else 0.0

    return rows, cw_med, cw_p95


def main():

    # changed it to one time run

    os.makedirs("logs", exist_ok=True)
    runs_file = "runs.csv" 
    results_file = "results.csv"
    for run in range(1, 57):
    
        base = os.path.join("logs",  f"{(run):02d}")

        iperf_json = base + '_iperf.json'
        rtt_txt = base + '_rtt.txt'
        cwnd_txt = base + '_cwnd.txt'

        # STEP1: get throughput averages
        t_series, t_mean, t_p90, t_p95, retrans_total = parse_iperf_json(iperf_json)
        write_csv(base + '_throughput.csv', ['time_s','throughput_mbps','retrans'], t_series)

        # STEP2: get rtt averages
        rtt_rows, r_mean, r_p90, r_p95, loss_percent= parse_rtt_txt(rtt_txt)
        write_csv(base + '_rtt.csv', ['time_s','rtt_ms'], rtt_rows)

        # STEP3: get cwnd averages
        cwnd_rows, cw_med, cw_p95 = parse_cwnd_txt(cwnd_txt)
        write_csv(base + '_cwnd.csv', ['time_s','cwnd_bytes','rtt_ms'], cwnd_rows)


        # STEP4: plot
        # throughput
        if t_series:
            tx = [r[0] for r in t_series]
            ty = [r[1] for r in t_series]
            plot_series(tx, ty, 'time (s)', 'throughput (Mbps)', 'Throughput over time', base + '_throughput.png')
        # rtt
        if rtt_rows:
            rx = [r[0] for r in rtt_rows]
            ry = [r[1] for r in rtt_rows]
            plot_series(rx, ry, 'time (s)', 'RTT (ms)', 'RTT over time', base + '_rtt.png')
        # cwnd
        if cwnd_rows:
            cx = [r[0] for r in cwnd_rows]
            cy = [r[1] if r[1] is not None else math.nan for r in cwnd_rows]
            plot_series(cx, cy, 'time (s)', 'cwnd (bytes)', 'CWND over time', base + '_cwnd.png')

        # get row info from runs.csv
        meta = load_run_metadata(run, runs_file)

        meta_cols = [
            "run_id","scenario","link_setup","tcp_flavor","background","bidir","trial",
            "mean_throughput_mbps","p90_throughput_mbps","p95_throughput_mbps",
            "mean_rtt_ms","p90_rtt_ms","p95_rtt_ms",
            "loss_percent","median_cwnd_bytes","p95_cwnd_bytes"
        ]

        row = [[
            meta["run_id"], meta["scenario"], meta["link_setup"], meta["tcp_flavor"],
            meta["background"], meta["bidir"], meta["trial"],
            f"{t_mean:.3f}", f"{t_p90:.3f}", f"{t_p95:.3f}",
            f"{r_mean:.3f}", f"{r_p90:.3f}", f"{r_p95:.3f}",
            f"{loss_percent:.6f}"
            f"{cw_med:.0f}", f"{cw_p95:.0f}"
        ]]

        write_csv(results_file, meta_cols, row)



if __name__ == '__main__':
    main()
