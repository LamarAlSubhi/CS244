import csv
from pathlib import Path
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent
SUM      = BASE_DIR / "plots" / "summary.csv"
OUTDIR   = BASE_DIR / "plots"

def load_rows():
    if not SUM.exists():
        raise SystemExit(f"[error] summary not found: {SUM}")
    rows = []
    with SUM.open() as f:
        for r in csv.DictReader(f):
            rows.append(r)
    if not rows:
        raise SystemExit("[error] summary is empty")
    return rows

def scatter_x_y(rows, xkey, ykey, filt=None, title="", out="plot.png"):
    data = rows if filt is None else [r for r in rows if filt(r)]
    xs, ys, labs = [], [], []
    for r in data:
        try:
            x = float(r[xkey])
            y = float(r[ykey])
        except (ValueError, TypeError, KeyError):
            continue
        xs.append(x); ys.append(y); labs.append(r.get("run",""))

    plt.figure(figsize=(6,4))
    plt.scatter(xs, ys, s=30)
    for x, y, l in zip(xs, ys, labs):
        if l:
            plt.annotate(l, (x, y), fontsize=7, alpha=0.6)
    plt.xlabel(xkey.replace("_", " "))
    plt.ylabel(ykey.replace("_", " "))
    plt.title(title)
    plt.grid(True, alpha=0.3)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTDIR / out
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"wrote {out_path}")

def main():
    rows = load_rows()
    # wired only
    scatter_x_y(rows, "tx_ring", "avg_tput_gbps",
                filt=lambda r: "enp0s3" in r["run"] and r["tx_ring"],
                title="Wired: Avg throughput vs TX ring",
                out="tput_vs_txring_wired.png")

    # wired: throughput vs txqueuelen
    scatter_x_y(rows, "txqueuelen", "avg_tput_gbps",
                filt=lambda r: "enp0s3" in r["run"],
                title="wired: avg throughput vs txqueuelen (pfifo limit)",
                out="tput_vs_txqlen_wired.png")

    # wireless: throughput vs txqueuelen
    scatter_x_y(rows, "txqueuelen", "avg_tput_gbps",
                filt=lambda r: "wlo1" in r["run"],
                title="wireless: avg throughput vs txqueuelen",
                out="tput_vs_txqlen_wireless.png")

    # wired: p95 RTT vs throughput
    scatter_x_y(rows, "avg_tput_gbps", "p95_rtt_ms",
                filt=lambda r: "enp0s3" in r["run"],
                title="wired: p95 rtt vs throughput",
                out="p95rtt_vs_tput_wired.png")
    
    # wireless: p95 RTT vs throughput
    scatter_x_y(rows, "avg_tput_gbps", "p95_rtt_ms",
                filt=lambda r: "wlo1" in r["run"],
                title="wireless: p95 rtt vs throughput",
                out="p95rtt_vs_tput_wireless.png")

if __name__ == "__main__":
    main()