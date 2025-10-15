import json, re, csv, math
from pathlib import Path
from statistics import mean

BASE_DIR  = Path(__file__).resolve().parent
LOGS_DIR  = BASE_DIR / "logs"
PLOTS_DIR = BASE_DIR / "plots"
OUT_CSV   = PLOTS_DIR / "summary.csv"

PING_RE = re.compile(r"time=([\d\.]+)\s*ms")

def iperf_stats(run_dir: Path):
    ip = run_dir / "iperf.json"
    try:
        j = json.loads(ip.read_text())
    except Exception:
        return (None, None)
    gbps = []
    for iv in j.get("intervals", []):
        s = iv.get("sum") or (iv.get("streams", [{}])[0])
        bps = s.get("bits_per_second")
        if bps is not None:
            gbps.append(float(bps)/1e9)
    return ((mean(gbps), max(gbps)) if gbps else (None, None))

def ping_stats(run_dir: Path):
    p = run_dir / "ping.txt"
    txt = p.read_text(errors="ignore")
    ms = [float(m.group(1)) for m in PING_RE.finditer(txt)]
    ms_sorted = sorted(ms)

    idx = max(0, math.ceil(0.95 * len(ms_sorted)) - 1)
    p95 = ms_sorted[idx]
    return (mean(ms), p95)

def parse_rowcsv(run_dir: Path):
    rc = run_dir / "row.csv"
    lines = rc.read_text().strip().splitlines()
    if len(lines) < 2:
        return {}
    hdr, vals = lines[0], lines[1]
    keys = [h.strip() for h in hdr.split(",")]
    vls  = [v.strip() for v in vals.split(",")]
    return dict(zip(keys, vls))

def main():

    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for run_dir in sorted(d for d in LOGS_DIR.iterdir() if d.is_dir()):
        meta = parse_rowcsv(run_dir)
        # fallbacks
        iface = meta.get("iface") or ("wlo1" if "wlo1" in run_dir.name else ("enp0s3" if "enp0s3" in run_dir.name else ""))
        case  = meta.get("case", "")
        tq    = meta.get("txqueuelen")
        txr   = meta.get("tx_ring")
        rxr   = meta.get("rx_ring")

        avg_t, max_t = iperf_stats(run_dir)
        avg_rtt, p95 = ping_stats(run_dir)

        def _to_int(s):
            try: return int(s)
            except: return ""

        rows.append({
            "run": run_dir.name,
            "iface": iface,
            "case": case,
            "txqueuelen": _to_int(tq),
            "tx_ring": _to_int(txr),
            "rx_ring": _to_int(rxr),
            "avg_tput_gbps": (round(avg_t,3) if avg_t is not None else ""),
            "max_tput_gbps": (round(max_t,3) if max_t is not None else ""),
            "avg_rtt_ms":    (round(avg_rtt,2) if avg_rtt is not None else ""),
            "p95_rtt_ms":    (round(p95,2) if p95 is not None else ""),
        })

    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"wrote {OUT_CSV}")

if __name__ == "__main__":
    main()