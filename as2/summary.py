"""
this aggregates numbers from trials A and B into 1 representing that scenario
"""

import argparse
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

KEY = ['scenario','link_setup','tcp_flavor','background','bidir']

NUM_COLS = [
    'mean_throughput_mbps','p90_throughput_mbps','p95_throughput_mbps',
    'mean_rtt_ms','p90_rtt_ms','p95_rtt_ms',
    'retrans_total','median_cwnd_bytes','p95_cwnd_bytes'
]

def safe_numeric(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    return df

def aggregate_results(results_csv: Path, out_csv: Path) -> pd.DataFrame:
    if not results_csv.exists() or results_csv.stat().st_size == 0:
        agg_cols = KEY + ['runs_count'] + NUM_COLS
        pd.DataFrame(columns=agg_cols).to_csv(out_csv, index=False)
        return pd.DataFrame(columns=agg_cols)

    df = pd.read_csv(results_csv)
    df = safe_numeric(df, NUM_COLS)

    def agg_fn(g: pd.DataFrame) -> pd.Series:
        out = {'runs_count': g.shape[0]}
        for c in NUM_COLS:
            if c == 'retrans_total':
                out[c] = g[c].sum(skipna=True)
            else:
                out[c] = g[c].mean(skipna=True)
        return pd.Series(out)

    agg = df.groupby(KEY, dropna=False).apply(agg_fn).reset_index()
    agg.to_csv(out_csv, index=False)
    return agg

def write_pairs(results_csv: Path, out_csv: Path) -> pd.DataFrame:
    if not results_csv.exists() or results_csv.stat().st_size == 0:
        pd.DataFrame().to_csv(out_csv, index=False)
        return pd.DataFrame()

    df = pd.read_csv(results_csv)
    df = safe_numeric(df, NUM_COLS)

    wide = df.pivot_table(
        index=KEY, columns='trial',
        values=['mean_throughput_mbps','mean_rtt_ms','retrans_total'],
        aggfunc='first'
    ).reset_index()

    wide.to_csv(out_csv, index=False)
    return wide

def scenario_label(fields) -> str:
    vals = [str(x) for x in fields]
    return "_".join(vals)

def plot_overlay(results_csv: Path, logs_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    if not results_csv.exists() or results_csv.stat().st_size == 0:
        return

    df = pd.read_csv(results_csv)

    for fields, grp in df.groupby(KEY, dropna=False):
        label = scenario_label(fields)

        # throughput
        plt.figure()
        made = False
        for _, row in grp.sort_values(by='trial').iterrows():
            rid = int(row['run_id'])
            thr_path = logs_dir / f"{rid}_throughput.csv"
            if thr_path.exists():
                try:
                    thr = pd.read_csv(thr_path)
                    if {'time_s','throughput_mbps'}.issubset(thr.columns):
                        plt.plot(thr['time_s'], thr['throughput_mbps'], label=f"trial {row['trial']}")
                        made = True
                except Exception as e:
                    print(f"[warn] skipping {thr_path}: {e}")
        if made:
            plt.xlabel("Time (s)")
            plt.ylabel("Throughput (Mbps)")
            plt.title(label + " — throughput")
            plt.legend()
            plt.tight_layout()
            plt.savefig(out_dir / f"{label}_throughput.png")
        plt.close()

        # rtt
        plt.figure()
        made = False
        for _, row in grp.sort_values(by='trial').iterrows():
            rid = int(row['run_id'])
            rtt_path = logs_dir / f"{rid}_rtt.csv"
            if rtt_path.exists():
                try:
                    rtt = pd.read_csv(rtt_path)
                    if {'time_s','rtt_ms'}.issubset(rtt.columns):
                        plt.plot(rtt['time_s'], rtt['rtt_ms'], label=f"trial {row['trial']}")
                        made = True
                except Exception as e:
                    print(f"[warn] skipping {rtt_path}: {e}")
        if made:
            plt.xlabel("Time (s)")
            plt.ylabel("RTT (ms)")
            plt.title(label + " — RTT")
            plt.legend()
            plt.tight_layout()
            plt.savefig(out_dir / f"{label}_rtt.png")
        plt.close()

        # cwnd
        plt.figure()
        made = False
        for _, row in grp.sort_values(by='trial').iterrows():
            rid = int(row['run_id'])
            cw_path = logs_dir / f"{rid}_cwnd.csv"
            if cw_path.exists():
                try:
                    cw = pd.read_csv(cw_path)
                    if {'time_s','cwnd_bytes'}.issubset(cw.columns):
                        plt.plot(cw['time_s'], cw['cwnd_bytes'], label=f"trial {row['trial']}")
                        made = True
                except Exception as e:
                    print(f"[warn] skipping {cw_path}: {e}")
        if made:
            plt.xlabel("Time (s)")
            plt.ylabel("CWND (bytes)")
            plt.title(label + " — CWND")
            plt.legend()
            plt.tight_layout()
            plt.savefig(out_dir / f"{label}_cwnd.png")
        plt.close()

def main():
    ap = argparse.ArgumentParser(description="Aggregate results.csv and generate scenario-level plots.")
    ap.add_argument("--results", default="results.csv", help="Path to per-run results CSV (default: results.csv)")
    ap.add_argument("--logs-dir", default="logs", help="Directory containing per-run CSVs like <run_id>_throughput.csv")
    ap.add_argument("--out-dir", default="plots", help="Directory to write scenario-level PNGs")
    args = ap.parse_args()

    results_csv = Path(args.results)
    logs_dir = Path(args.logs_dir)
    out_dir = Path(args.out_dir)

    # aggregate numeric metrics
    agg = aggregate_results(results_csv, results_csv.parent / "results_agg.csv")
    print(f"[ok] wrote {results_csv.parent / 'results_agg.csv'} ({len(agg)} rows)")

    # scenario-level overlay plots
    plot_overlay(results_csv, logs_dir, out_dir)
    print(f"[ok] wrote scenario plots to {out_dir}")

if __name__ == "__main__":
    main()