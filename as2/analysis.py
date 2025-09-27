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

import argparse, json, os, re, statistics, math, glob
import matplotlib.pyplot as plt

# ---------- helpers ----------

def find_base_for_run(run_id: int, logs_dir: str) -> str:
    pattern = os.path.join(logs_dir, f"{run_id:02d}_iperf.json")
    candidates = sorted(glob.glob(pattern))
    
    iperf_json = candidates[0]
    base = iperf_json[:-len('_iperf.json')]
    
    return base

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
    ts_pat = re.compile(r'^\[(\d+\.\d+)\]')  # ping -D timestamp
    val_pat = re.compile(r'time[=<]([\d\.]+)\s*ms')
    with open(path) as f:
        for line in f:
            m = val_pat.search(line)
            if not m:
                continue
            rtt = float(m.group(1))
            ts_match = ts_pat.match(line.strip())
            ts = float(ts_match.group(1))
            rtt_vals.append((ts, rtt))
    plain = [v for _, v in rtt_vals]
    r_mean = statistics.fmean(plain)
    r_p90  = percentile(sorted(plain), 0.90)
    r_p95  = percentile(sorted(plain), 0.95)

    # build rows with relative time axis
    if rtt_vals and rtt_vals[0][0] is not None:
        t0 = rtt_vals[0][0]
        rows = [(round(ts - t0, 3), v) for ts, v in rtt_vals]
    else:
        # fall back to 0.2s spacing if no -D timestamps
        rows, t = [], 0.0
        for _, v in rtt_vals:
            rows.append((round(t, 3), v))
            t += 0.2

    return rows, r_mean, r_p90, r_p95


def parse_cwnd_txt(path):
    rows = []
    cur_ts = None
    cwnd_pat = re.compile(r'cwnd:(\d+)')
    rtt_pat  = re.compile(r'rtt:(\d+\.?\d*)')
    infl_pat = re.compile(r'bytes_inflight:(\d+)')
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.isdigit():
                cur_ts = int(line)
                continue
            if cur_ts is None:
                continue
            m_c = cwnd_pat.search(line)
            m_r = rtt_pat.search(line)
            m_i = infl_pat.search(line)
            if m_c or m_r or m_i:
                cw = int(m_c.group(1))
                rt = float(m_r.group(1))
                bi = int(m_i.group(1))
                rows.append((cur_ts, cw, rt, bi))
    cw_vals = [r[1] for r in rows]
    cw_med = statistics.median(cw_vals)
    cw_p95 = percentile(sorted(cw_vals), 0.95)
    # normalize time
    if rows:
        t0 = rows[0][0]
        rows = [(r[0]-t0, r[1], r[2], r[3]) for r in rows]
    return rows, cw_med, cw_p95


def main():
    ap = argparse.ArgumentParser(description="analyze one run's logs into CSVs and plots and append one metadata row")
    ap.add_argument('--run-id', type=int, required=True)
    ap.add_argument('--logs-dir', default='logs')
    ap.add_argument('--file', default='results.csv')
    args = ap.parse_args()

    os.makedirs(args.logs_dir, exist_ok=True)
    base = find_base_for_run(args.run_id, args.logs_dir)

    iperf_json = args.base + '_iperf.json'
    rtt_txt = args.base + '_rtt.txt'
    cwnd_txt = args.base + '_cwnd.txt'

    # STEP1: get throughput averages
    t_series, t_mean, t_p90, t_p95, retrans_total = parse_iperf_json(iperf_json)
    write_csv(args.base + '_throughput.csv', ['time_s','throughput_mbps','retrans'], t_series)

    # STEP2: get rtt averages
    rtt_rows, r_mean, r_p90, r_p95 = parse_rtt_txt(rtt_txt)
    write_csv(args.base + '_rtt.csv', ['time_s','rtt_ms'], rtt_rows)

    # STEP3: get cwnd averages
    cwnd_rows, cw_med, cw_p95 = parse_cwnd_txt(cwnd_txt)
    write_csv(args.base + '_cwnd.csv', ['time_s','cwnd_bytes','rtt_ms','bytes_in_flight'], cwnd_rows)


    # STEP4: plot
    # throughput
    if t_series:
        tx = [r[0] for r in t_series]
        ty = [r[1] for r in t_series]
        plot_series(tx, ty, 'time (s)', 'throughput (Mbps)', 'Throughput over time', args.base + '_throughput.png')
    # rtt
    if rtt_rows:
        rx = [r[0] for r in rtt_rows]
        ry = [r[1] for r in rtt_rows]
        plot_series(rx, ry, 'time (s)', 'RTT (ms)', 'RTT over time', args.base + '_rtt.png')
    # cwnd
    if cwnd_rows:
        cx = [r[0] for r in cwnd_rows]
        cy = [r[1] if r[1] is not None else math.nan for r in cwnd_rows]
        plot_series(cx, cy, 'time (s)', 'cwnd (bytes)', 'CWND over time', args.base + '_cwnd.png')

    # get row info from runs.csv
    parts = base.split('_')
    run_id     = parts[0]
    scenario   = parts[1]
    link_setup = parts[2]
    tcp_flavor = parts[3]
    background = parts[4]
    bidir      = 'yes' if parts[5]=='bidir' else 'no'
    trial      = parts[6]

    meta_cols = [
        'run_id','scenario','link_setup','tcp_flavor','background','bidir','trial',
        'mean_throughput_mbps','p90_throughput_mbps','p95_throughput_mbps',
        'mean_rtt_ms','p90_rtt_ms','p95_rtt_ms',
        'retrans_total','median_cwnd_bytes','p95_cwnd_bytes'
    ]

    # build full row with new analysis
    row = [[
    run_id, scenario, link_setup, tcp_flavor, background, bidir, trial,
    f"{t_mean:.3f}", f"{t_p90:.3f}", f"{t_p95:.3f}",
    f"{r_mean:.3f}", f"{r_p90:.3f}", f"{r_p95:.3f}",
    str(retrans_total),
    f"{cw_med:.0f}", f"{cw_p95:.0f}"
    ''
]]

    write_csv(args.file, meta_cols, row)

    # After write_csv(...)
try:
    import pandas as pd
    df = pd.read_csv(args.file)
    num_cols = [
        'mean_throughput_mbps','p90_throughput_mbps','p95_throughput_mbps',
        'mean_rtt_ms','p90_rtt_ms','p95_rtt_ms',
        'retrans_total','median_cwnd_bytes','p95_cwnd_bytes'
    ]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    key = ['scenario','link_setup','tcp_flavor','background','bidir']
    def agg_fn(g):
        out = {'runs_count': g.shape[0]}
        for c in num_cols:
            out[c] = g[c].sum(skipna=True) if c == 'retrans_total' else g[c].mean(skipna=True)
        return pd.Series(out)
    agg = df.groupby(key, dropna=False).apply(agg_fn).reset_index()
    agg[['scenario','link_setup','tcp_flavor','background','bidir','runs_count'] + num_cols] \
        .to_csv('results_agg.csv', index=False)
except Exception as e:
    print("Aggregation skipped:", e)


if __name__ == '__main__':
    main()
