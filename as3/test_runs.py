"""
runs all experiment rows in runs.csv
- applies qdisc (pfifo) and txqueuelen
- applies NIC ring sizes (ethtool -G) when supported
- binds iperf3 client to the run's interface IP
- runs iperf3 (JSON), parallel ping, and CWND snapshots (ss -ti)
- captures pre/post qdisc + NIC counter snapshots

how to use:
  # receiver (mac):
  iperf3 -s

  # sender (linux omen):
  sudo python3 test_runs.py
"""
import csv
import os
import shlex
import subprocess
import re
import time
from pathlib import Path
import threading
import argparse


# ---------- PARAMS  ----------
SERVER_IP   = "10.240.175.138" # my mac

BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "as3" / "logs"
WIRED_CSV = str(BASE_DIR / "wired.csv")
WIRELESS_CSV = str(BASE_DIR / "wireless.csv")

print(f"[INFO] LOGS_DIR = {LOGS_DIR}")
LOGS_DIR.mkdir(parents=True, exist_ok=True)

WIRED_IFACE    = "enp0s3"   # VirtualBox e1000
WIRELESS_IFACE = "wlo1"   # OMEN host Wi-Fi

# ---------- helpers  ----------
def run(cmd: str) -> subprocess.CompletedProcess:
    """Run a shell command and capture stdout/stderr (no exception on non-zero exit).
    Returns: subprocess.CompletedProcess with .stdout/.stderr/.returncode.
    """
    return subprocess.run(shlex.split(cmd), text=True, capture_output=True, check=False)

def iface_ipv4(iface: str):
    """returns the first IPv4 address assigned """
    out = run(f"ip -4 addr show dev {iface}").stdout
    m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", out)
    return m.group(1) if m else None

def set_txqueuelen(iface: str, qlen: int) -> None:
    _ = run(f"ip link set dev {iface} txqueuelen {qlen}")

def set_qdisc_pfifo(iface: str, limit_pkts: int) -> None:
    _ = run(f"tc qdisc replace dev {iface} root pfifo limit {limit_pkts}")

def apply_queue_with_logs(iface: str, txqlen: int, out_dir: Path) -> None:
    """
    snapshots before, apply txqueuelen + qdisc, snapshot after
    creates:
      - queue_before.txt   (ip -s link show + tc -s qdisc show)
      - queue_apply.txt    (stdout/stderr from the two set commands)
      - queue_after.txt    (ip -s link show + tc -s qdisc show)
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    # BEFORE
    bef_ip  = run(f"ip -s link show dev {iface}")
    bef_tc  = run(f"tc -s qdisc show dev {iface}")
    (out_dir / "queue_before.txt").write_text(
        "=== ip -s link (before) ===\n" + bef_ip.stdout + bef_ip.stderr +
        "\n=== tc -s qdisc (before) ===\n" + bef_tc.stdout + bef_tc.stderr
    )

    # APPLY
    a1 = run(f"ip link set dev {iface} txqueuelen {txqlen}")
    a2 = run(f"tc qdisc replace dev {iface} root pfifo limit {txqlen}")
    if a2.returncode != 0:
        # fallback if pfifo unsupported and record why
        a2_fb = run(f"tc qdisc replace dev {iface} root pfifo_fast")
        (out_dir / "queue_apply.txt").write_text(
            "=== ip link set txqueuelen ===\n" + a1.stdout + a1.stderr +
            "\n=== tc qdisc pfifo (failed) ===\n" + a2.stdout + a2.stderr +
            "\n=== tc qdisc pfifo_fast (fallback) ===\n" + a2_fb.stdout + a2_fb.stderr
        )
    else:
        (out_dir / "queue_apply.txt").write_text(
            "=== ip link set txqueuelen ===\n" + a1.stdout + a1.stderr +
            "\n=== tc qdisc pfifo ===\n" + a2.stdout + a2.stderr
        )

    # AFTER
    aft_ip  = run(f"ip -s link show dev {iface}")
    aft_tc  = run(f"tc -s qdisc show dev {iface}")
    (out_dir / "queue_after.txt").write_text(
        "=== ip -s link (after) ===\n" + aft_ip.stdout + aft_ip.stderr +
        "\n=== tc -s qdisc (after) ===\n" + aft_tc.stdout + aft_tc.stderr
    )


def apply_rings_with_logs(iface: str, tx: int, rx: int, out_dir: Path) -> None:
    """   
    snapshots before, apply NIC TX/RX ring sizes, snapshot after
    creates:
      - rings_before.txt   (ethtool -g output before change)
      - rings_set.txt      (stdout/stderr from ethtool -G command)
      - rings_after.txt    (ethtool -g output after change)
    """
    before = run(f"ethtool -g {iface}")
    (out_dir / "rings_before.txt").write_text(before.stdout + before.stderr)
    setres = run(f"ethtool -G {iface} tx {tx} rx {rx}")
    (out_dir / "rings_set.txt").write_text(setres.stdout + setres.stderr)
    after = run(f"ethtool -g {iface}")
    (out_dir / "rings_after.txt").write_text(after.stdout + after.stderr)


# --------------- loggers  ---------------

def snapshot_qdisc(iface: str) -> None:
    """print 'tc -s qdisc show dev <iface>' output for quick testing"""
    res = run(f"tc -s qdisc show dev {iface}")
    print(f"\n=== QDISC SNAPSHOT for {iface} ===")
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr:
        print(f"[stderr]\n{res.stderr.strip()}")

def snapshot_nic_stats(iface: str) -> None:
    """print NIC /sys statistics for quick testing"""
    base = Path(f"/sys/class/net/{iface}/statistics")
    if not base.exists():
        print(f"[warn] stats path not found for {iface}")
        return

    print(f"\n=== NIC STATS SNAPSHOT for {iface} ===")
    for name in sorted(base.iterdir()):
        try:
            val = name.read_text().strip()
        except Exception as e:
            val = f"ERR ({e})"
        print(f"{name.name}: {val}")


# --------------- samplers  ---------------
def start_rtt(server: str, out_file: str) -> subprocess.Popen:
    """
        starts pings in background for 60 secs to measure rtt
    """
    cmd = f"ping -D -i 0.2 -w 60 {server}"
    with open(out_file, "w") as f:
        return subprocess.Popen(shlex.split(cmd), stdout=f, stderr=subprocess.STDOUT)

def start_iperf(server: str, bind_ip: str, out_file: str, port: int = 5201) -> subprocess.Popen:
    """
        starts iperf3 client in background for 60 secs
    """
    cmd = f"iperf3 -J -c {server} -t 60 -B {bind_ip} -p {port}"
    with open(out_file, "w") as f:
        return subprocess.Popen(shlex.split(cmd), stdout=f, stderr=subprocess.STDOUT)

def sample_cwnd(dst_ip: str, out_file: str, fg_port: int = 5201) -> None:
    """
        samples congestion window info every sec for 60 secs
    """
    cmd = ["ss", "-tin", "-f", "inet", "dst", dst_ip,
           "and", f"( dport = :{fg_port} or sport = :{fg_port} )"]
    end_time = time.time() + 60
    with open(out_file, "w") as f:
        while time.time() < end_time:
            ts = int(time.time())
            f.write(f"ts={ts}\n")
            try:
                subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT,
                               text=True, check=False)
            except Exception as e:
                f.write(f"(error: {e})\n")
            f.write("\n")
            f.flush()
            time.sleep(1)



def run_wired():
    """
    runs all of the rows in wired.csv, makes changes to ring sizes
    """
    with open(WIRED_CSV, newline="") as fcsv:
        rdr = csv.DictReader(fcsv)
        for row in rdr:
            # STEP1: read row info and initialize folder
            runid   = row["runid"].strip()
            iface   = WIRED_IFACE
            case    = row["case"].strip()
            txqlen  = int(row["txqueuelen"])
            tx_ring = int(row["tx_ring"])
            rx_ring = int(row["rx_ring"])


            outdir = LOGS_DIR / f"{runid}-{iface}-{case}"
            outdir.mkdir(parents=True, exist_ok=True)

            # STEP2: record initial context
            (outdir / "row.csv").write_text(",".join(row.keys()) + "\n" + ",".join(row.values()) + "\n")
            (outdir / "uname.txt").write_text(run("uname -a").stdout)
            drv = run(f"ethtool -i {iface}")
            (outdir / "driver.txt").write_text(drv.stdout + drv.stderr)

            # STEP3: apply queueing
            apply_queue_with_logs(iface, txqlen, outdir)

            # STEP4: apply rings
            apply_rings_with_logs(iface, tx_ring, rx_ring, outdir)

            # STEP5: bind to iface IP
            bind_ip = iface_ipv4(iface)
            if not bind_ip:
                (outdir / "ERROR.txt").write_text(f"no IPv4 on {iface}")
                print(f"[skip] {runid}-{iface}-{case}: no IPv4 on {iface}")
                continue

            # STEP6: launch collectors
            iperf_p = start_iperf(SERVER_IP, bind_ip, outdir / "iperf.json")
            ping_p  = start_rtt(SERVER_IP, outdir / "ping.txt")

            t_cwnd = threading.Thread(
                target=sample_cwnd,
                args=(SERVER_IP, outdir / "ss_cwnd.txt"),
                kwargs={"fg_port": 5201},
                daemon=True,
            )
            t_cwnd.start()

            iperf_p.wait()
            ping_p.wait()
            if t_cwnd.is_alive():
                t_cwnd.join(timeout=2)

            (outdir / "DONE").write_text(time.strftime("%Y-%m-%d %H:%M:%S"))
            print(f"run {runid}-{iface}-{case} complete")



def run_wireless():
    """
    runs all of the rows in wireless.csv, NO RINGS
    """
    with open(WIRELESS_CSV, newline="") as fcsv:
        rdr = csv.DictReader(fcsv)
        for row in rdr:
            # STEP1: read row info and initialize folder
            runid   = row["runid"].strip()
            iface   = WIRELESS_IFACE
            case    = row["case"].strip()
            txqlen  = int(row["txqueuelen"])
            # NO RINGS SUPPORTED


            outdir = LOGS_DIR / f"{runid}-{iface}-{case}"
            outdir.mkdir(parents=True, exist_ok=True)

            # STEP2: record initial context
            (outdir / "row.csv").write_text(",".join(row.keys()) + "\n" + ",".join(row.values()) + "\n")
            (outdir / "uname.txt").write_text(run("uname -a").stdout)

            #redundant tbh but whatevs 
            drv = run(f"ethtool -i {iface}")
            (outdir / "driver.txt").write_text(drv.stdout + drv.stderr)

            # STEP3: apply queueing
            apply_queue_with_logs(iface, txqlen, outdir)

            # skip rings

            # STEP4: bind to iface IP
            bind_ip = iface_ipv4(iface)
            if not bind_ip:
                (outdir / "ERROR.txt").write_text(f"no IPv4 on {iface}")
                print(f"[skip] {runid}-{iface}-{case}: no IPv4 on {iface}")
                continue

            # STEP5: launch collectors
            iperf_p = start_iperf(SERVER_IP, bind_ip, outdir / "iperf.json")
            ping_p  = start_rtt(SERVER_IP, outdir / "ping.txt")

            t_cwnd = threading.Thread(
                target=sample_cwnd,
                args=(SERVER_IP, outdir / "ss_cwnd.txt"),
                kwargs={"fg_port": 5201},
                daemon=True,
            )
            t_cwnd.start()

            iperf_p.wait()
            ping_p.wait()
            if t_cwnd.is_alive():
                t_cwnd.join(timeout=2)

            (outdir / "DONE").write_text(time.strftime("%Y-%m-%d %H:%M:%S"))
            print(f"run {runid}-{iface}-{case} complete")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["wired", "wireless"], required=True)
    args = parser.parse_args()

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    if args.mode == "wired":
        run_wired()
    else:
        run_wireless()

if __name__ == "__main__":
    main()