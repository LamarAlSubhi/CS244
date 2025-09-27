import pandas as pd

IN = "results.csv"
OUT = "results_agg.csv"

df = pd.read_csv(IN)

num_cols = [
    "mean_throughput_mbps","p90_throughput_mbps","p95_throughput_mbps",
    "mean_rtt_ms","p90_rtt_ms","p95_rtt_ms",
    "loss_percent","median_cwnd_bytes","p95_cwnd_bytes"
]

# convert numeric fields safely
for c in num_cols:
    df[c] = pd.to_numeric(df[c], errors="coerce")

key = ["scenario","link_setup","tcp_flavor","background","bidir"]

def agg_fn(g):
    out = {"runs_count": g.shape[0]}
    for c in num_cols:
        # just take the mean across runs (skip NaN)
        out[c] = g[c].mean(skipna=True)
    return pd.Series(out)

agg = df.groupby(key, dropna=False).apply(agg_fn).reset_index()

# reorder columns for clean output
cols = key + ["runs_count"] + num_cols
agg[cols].to_csv(OUT, index=False)

print(f"Wrote {OUT}")