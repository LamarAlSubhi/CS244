import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

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
    for path in sorted(logs_dir.glob("client_*.csv")):
        df = pd.read_csv(path)

        # pick the delay column (it always starts with "delay(")
        delay_col = [c for c in df.columns if c.startswith("delay(")][0]
        owd_ms = pd.to_numeric(df[delay_col]) / 1e6  # ns → ms

        row = {
            "file": path.name,
            "samples": len(owd_ms),
            "owd_ms_mean": float(owd_ms.mean()),
            "owd_ms_std": float(owd_ms.std(ddof=1)),
            "owd_ms_p50": float(owd_ms.median()),
            "owd_ms_p95": float(owd_ms.quantile(0.95)),
            "owd_ms_min": float(owd_ms.min()),
            "owd_ms_max": float(owd_ms.max()),
        }
        rows.append(row)

        if args.plots:
            plt.figure()
            plt.plot(range(len(owd_ms)), owd_ms.values)
            plt.xlabel("packet seq")
            plt.ylabel("OWD (ms)")
            plt.title(path.name)
            outp = plots_dir / f"{path.stem}_owd.png"
            plt.tight_layout()
            plt.savefig(outp)
            plt.close()

    summary = pd.DataFrame(rows).sort_values("file")
    out_csv = logs_dir / "summary_delay.csv"
    summary.to_csv(out_csv, index=False)
    print(f"[OK] Wrote {out_csv}\n")
    print(summary.to_string(index=False))

if __name__ == "__main__":
    main()