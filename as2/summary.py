import os
import re
import pandas as pd
import matplotlib.pyplot as plt

IN_CSV = "results_agg.csv"
OUT_DIR = "plots"

def sanitize(name: str) -> str:
    s = re.sub(r'[^A-Za-z0-9._+-]+', '_', str(name).strip())
    s = re.sub(r'_{2,}', '_', s).strip('_')
    return s or "all"

def ensure_numeric(df: pd.DataFrame, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

def bar_plot(df, metric, background, link_setup):
    subset = df[(df["background"] == background) & (df["link_setup"] == link_setup)]
    if subset.empty:
        return None
    # consistent flavor order if present
    order = ["BBR", "CUBIC", "Reno", "Vegas"]
    present = [f for f in order if f in subset["tcp_flavor"].unique().tolist()]
    subset = subset.set_index("tcp_flavor").loc[present].reset_index() if present else subset

    fig = plt.figure()
    plt.bar(subset["tcp_flavor"], subset[metric])
    plt.xlabel("TCP flavor")
    plt.ylabel(metric.replace('_', ' '))
    plt.title(f"{metric.replace('_',' ')} – {background} – {link_setup}")
    plt.tight_layout()
    fname = f"{metric}_{sanitize(background)}_{sanitize(link_setup)}.png"
    out_path = os.path.join(OUT_DIR, fname)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path

def scatter_tradeoff(df):
    # Scatter: x = mean_rtt_ms, y = mean_throughput_mbps
    if df.empty:
        return None

    markers = {}
    for ls in df["link_setup"].dropna().unique().tolist():
        markers[ls] = 'o' if len(markers)==0 else ('s' if len(markers)==1 else '^')

    fig = plt.figure()
    for _, row in df.iterrows():
        ls = row.get("link_setup", "unknown")
        marker = markers.get(ls, 'o')
        plt.scatter(row["mean_rtt_ms"], row["mean_throughput_mbps"], marker=marker)
    plt.xlabel("mean RTT (ms)")
    plt.ylabel("mean throughput (Mbps)")
    plt.title("Throughput vs RTT (aggregated per group)")

    handles = []
    labels = []
    for ls, m in markers.items():
        handles.append(plt.Line2D([0],[0], linestyle='', marker=m))
        labels.append(ls)
    if handles:
        plt.legend(handles, labels, title="link_setup", loc="best")
    plt.tight_layout()
    out_path = os.path.join(OUT_DIR, "throughput_vs_rtt_scatter.png")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path

def main():
    if not os.path.exists(IN_CSV):
        raise SystemExit(f"Missing {IN_CSV} in the current directory.")
    os.makedirs(OUT_DIR, exist_ok=True)

    df = pd.read_csv(IN_CSV)
    num_cols = [
        "mean_throughput_mbps","p90_throughput_mbps","p95_throughput_mbps",
        "mean_rtt_ms","p90_rtt_ms","p95_rtt_ms",
        "loss_percent","median_cwnd_bytes","p95_cwnd_bytes"
    ]
    ensure_numeric(df, num_cols)

    required = ["scenario","link_setup","tcp_flavor","background","bidir"]
    for c in required:
        if c not in df.columns:
            raise SystemExit(f"Missing required column: {c}")

    outputs = []

    backgrounds = sorted(df["background"].dropna().unique().tolist(), key=lambda x: str(x))
    link_setups = sorted(df["link_setup"].dropna().unique().tolist(), key=lambda x: str(x))

    metrics = ["mean_throughput_mbps","mean_rtt_ms","loss_percent","median_cwnd_bytes"]
    for bg in backgrounds:
        for ls in link_setups:
            for metric in metrics:
                out = bar_plot(df, metric, bg, ls)
                if out:
                    outputs.append(out)

    out = scatter_tradeoff(df)
    if out:
        outputs.append(out)

    print("Saved plots:")
    for p in outputs:
        print(" -", p)

if __name__ == "__main__":
    main()