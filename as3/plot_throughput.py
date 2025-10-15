import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
PLOTS_DIR = BASE_DIR / "plots"
WIRED_KEY = "enp0s3"
WIRELESS_KEY = "wlo1"

# ---------- helpers ----------
def load_iperf(iperf_path: Path):
    try:
        data = json.loads(iperf_path.read_text())
    except Exception:
        return [], []
    ts, gbps = [], []
    for iv in data.get("intervals", []):
        s = iv.get("sum") or iv["streams"][0]
        mid = 0.5 * (float(s["start"]) + float(s["end"]))
        ts.append(mid)
        gbps.append(float(s["bits_per_second"]) / 1e9)
    if not ts:
        return [], []
    t0 = ts[0]
    ts = [t - t0 for t in ts]
    return np.array(ts), np.array(gbps)

def discover_runs():
    runs = []
    for p in sorted(LOGS_DIR.iterdir()):
        if p.is_dir() and (p / "iperf.json").exists():
            runs.append((p, p.name))
    return runs

def plot_throughput(runs, out_path: Path, title):
    plt.figure(figsize=(8,5))
    for p, label in runs:
        t, y = load_iperf(p / "iperf.json")
        if len(t) == 0: 
            continue
        style = "-" if WIRED_KEY in label else "--"
        plt.plot(t, y, style, label=label)
    plt.xlabel("time (s)")
    plt.ylabel("throughput (Gb/s)")
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize="small", ncol=2)
    plt.tight_layout()
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"wrote {out_path}")

# ---------- main ----------
def main():
    runs = discover_runs()
    wired = [(p,l) for (p,l) in runs if WIRED_KEY in l]
    wireless = [(p,l) for (p,l) in runs if WIRELESS_KEY in l]

    plot_throughput(runs, PLOTS_DIR / "throughput_all.png", "throughput of all runs")
    plot_throughput(wired, PLOTS_DIR / "throughput_wired.png", "throughput (wired)")
    plot_throughput(wireless, PLOTS_DIR / "throughput_wireless.png", "throughput (wireless)")

if __name__ == "__main__":
    main()