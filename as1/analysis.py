#!/usr/bin/env python3
"""
analysis_full.py — full analysis for OWD assignment.

Each log CSV has a header like:
  seq,time_sent,time_received,delay(offset=XYZ),payload_bytes

Filename encodes config:
  client_<iface>_p<payload>_i<interval>_c<count>.csv

Outputs:
  - logs/summary_full.csv with mean/std/p95/jitter/loss
  - logs/plots/*: individual plots per log + combined wifi vs eth
"""

import argparse, re
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

FNAME_RE = re.compile(
    r"""client_
        (?P<iface>[A-Za-z0-9_-]+)
        _p(?P<payload>\d+)
        _i(?P<interval>\d+)
        _c(?P<count>\d+)
        .*\.csv$""",
    re.VERBOSE,
)

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs-dir", default="./logs")
    ap.add_argument("--plots", action="store_true")
    return ap.parse_args()

def main():
    args = parse_args()
    logs_dir = Path(args.logs_dir)
    plots_dir = logs_dir / "plots"
    if args.plots:
        plots_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    grouped = {}  # key = (payload, interval) → {iface: df}

    for path in sorted(logs_dir.glob("client_*.csv")):
        m = FNAME_RE.search(path.name)
        if not m: 
            continue
        meta = m.groupdict()
        iface   = meta["iface"]
        payload = int(meta["payload"])
        interval= int(meta["interval"])
        expected= int(meta["count"])

        df = pd.read_csv(path)
        delay_col = [c for c in df.columns if c.startswith("delay(")][0]
        owd_ms = pd.to_numeric(df[delay_col]) / 1e6

        # packet loss (seq should go 0..expected-1)
        received = len(df)
        loss_pct = 100 * (1 - received/expected)

        row = {
            "file": path.name,
            "iface": iface,
            "payload_B": payload,
            "interval_ms": interval,
            "count_expected": expected,
            "count_received": received,
            "loss_pct": loss_pct,
            "owd_ms_mean": float(owd_ms.mean()),
            "owd_ms_std": float(owd_ms.std(ddof=1)),
            "owd_ms_p50": float(owd_ms.median()),
            "owd_ms_p95": float(owd_ms.quantile(0.95)),
            "owd_ms_min": float(owd_ms.min()),
            "owd_ms_max": float(owd_ms.max()),
        }
        rows.append(row)

        # group for combined plots
        key = (payload, interval)
        grouped.setdefault(key, {})[iface] = owd_ms

        # individual plot
        if args.plots:
            plt.figure()
            plt.plot(range(len(owd_ms)), owd_ms.values)
            plt.xlabel("packet seq")
            plt.ylabel("OWD (ms)")
            plt.title(path.name)
            plt.tight_layout()
            plt.savefig(plots_dir / f"{path.stem}_owd.png")
            plt.close()

    # summary table
    summary = pd.DataFrame(rows).sort_values(["payload_B","interval_ms","iface"])
    out_csv = logs_dir / "summary_full.csv"
    summary.to_csv(out_csv, index=False)
    print(f"[OK] Wrote {out_csv}\n")
    print(summary[["iface","payload_B","interval_ms","owd_ms_mean","owd_ms_std","owd_ms_p95","loss_pct"]].to_string(index=False))

    # combined plots wifi vs eth
    if args.plots:
        for (payload, interval), data in grouped.items():
            if len(data) < 2: 
                continue
            plt.figure()
            for iface, owd_ms in data.items():
                plt.plot(range(len(owd_ms)), owd_ms.values, label=iface)
            plt.xlabel("packet seq")
            plt.ylabel("OWD (ms)")
            plt.title(f"OWD over time (payload={payload}B, interval={interval}ms)")
            plt.legend()
            plt.tight_layout()
            fname = f"compare_p{payload}_i{interval}.png"
            plt.savefig(plots_dir / fname)
            plt.close()

if __name__ == "__main__":
    main()