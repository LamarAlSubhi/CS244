import pandas as pd

IN = "results.csv"
OUT = "results_agg.csv"

df = pd.read_csv(IN)

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
agg[['scenario','link_setup','tcp_flavor','background','bidir','runs_count'] + num_cols].to_csv(OUT, index=False)
print(f"Wrote {OUT}")