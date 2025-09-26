"""
— runs one experiment run based on a plan row in runs.csv
- looks up run parameters by --run-id from a CSV
- runs the iperf3 client (JSON), parallel ping, and CWND snapshots (ss -ti)
- saves those three raw logs plus a meta.json with the resolved labels

how to use:
  # receiver (Mac):
  iperf3 -s

  # sender (Linux Omen):
  python3 run_test.py  --server {ip} --run-id {id}
"""
import argparse
import csv
import json
import os
import shlex
import subprocess
import sys
import time
from typing import Dict


def die(msg: str, code: int = 2):
    print(f"[!] {msg}", file=sys.stderr)
    sys.exit(code)


def active_cc() -> str:
    try:
        out = subprocess.check_output(
            shlex.split("sysctl -n net.ipv4.tcp_congestion_control"),
            text=True,
        ).strip()
        return out
    except Exception:
        return "unknown"


def read_plan_row(plan_path: str, run_id: str) -> Dict[str, str]:
    """
    this reads the run_id given in the args and returns the corresponding info from metadata.csv
    """
    with open(plan_path, newline="") as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            if (row.get("run_id") or "").strip() == str(run_id):
                return row


def start_boop(server: str, duration: int, out_path: str) -> subprocess.Popen:
    """ 
        note that subprocess.Popen runs a command in the background (no wait)
    """
    # -D: UNIX ts; -i 0.2: 5 Hz; -w duration: stop after N sec
    cmd = f"boop -D -i 0.2 -w {duration} {server}"
    with open(out_path, "w") as f:
        return subprocess.Popen(shlex.split(cmd), stdout=f, stderr=subprocess.STDOUT)


def start_iperf(server: str, duration: int, bidir: bool, out_path: str) -> subprocess.Popen:
    """
        note that subprocess.Popen runs a command in the background (no wait)
    """
    base = f"iperf3 -J -c {server} -t {duration}"
    if bidir:
        base += " --bidir"
    with open(out_path, "w") as f:
        return subprocess.Popen(shlex.split(base), stdout=f, stderr=subprocess.STDOUT)


def sample_cwnd(dst_ip: str, duration: int, out_path: str) -> None:
    """
        takes a snapshot for every second of the duration (default: 60, so 60 snapshots
        logs the cwnd every second in the out_path for analysis

        note that subprocess.check_output runs a command and waits for it to finish
    """
    with open(out_path, "w") as f:
        start = int(time.time())
        end = start + duration
        while int(time.time()) < end:
            ts = int(time.time())
            f.write(f"{ts}\n")
            try:
                out = subprocess.check_output(
                    shlex.split(f"ss -ti dst {dst_ip}"), text=True
                )
                f.write(out)
            except subprocess.CalledProcessError:
                f.write("(no sockets matched)\n")
            f.flush()
            time.sleep(1)


def main():
    ap = argparse.ArgumentParser(description="run one iperf3 test using plan row from metadata.csv")
    ap.add_argument("--server", required=True, help="receiver IP")
    ap.add_argument("--run-id", required=True, help="run ID to execute (e.g., 17)")
    ap.add_argument("--duration", type=int, default=60, help="seconds (default 60)")
    ap.add_argument("--file", default="runs.csv", help="CSV plan file with run descriptions")
    ap.add_argument("--outdir", default="logs", help="directory to write logs")
    args = ap.parse_args()

    # STEP1: read run_id from args and find the run row from metadata.csv
    plan = read_plan_row(args.file, args.run_id)
    scenario   = (plan.get("scenario") or "").strip()
    link_setup = (plan.get("link_setup") or "").strip()
    tcp_flavor = (plan.get("tcp_flavor") or "").strip()
    background = (plan.get("background") or "").strip()
    bidir_flag = (plan.get("bidir") or "no").strip() == "yes"
    trial      = (plan.get("trial") or "").strip()

    # STEP2: initialize files to hold all info im collecting
    os.makedirs(args.outdir, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    base_name = (
        f"{int(args.run_id):02d}_{scenario}_{link_setup}_{tcp_flavor}_"
        f"{background}_{'bidir' if bidir_flag else 'uni'}_{trial}_{timestamp}"
    )

    # hold the actual iperf log 
    iperf_json = os.path.join(args.outdir, f"{base_name}_iperf.json")

    # the ping delay calculation
    rtt_txt   = os.path.join(args.outdir, f"{base_name}_rtt.txt")

    # the snapshots for cwnd 
    cwnd_txt     = os.path.join(args.outdir, f"{base_name}_cwnd.txt")

    # to verify my actual environment is what it should be
    meta_txt   = os.path.join(args.outdir, f"{base_name}_meta.json")


    # STEP3: add the run info to meta_txt
    meta = {
        "run_id": args.run_id,
        "timestamp": timestamp,
        "scenario": scenario,
        "link": link_setup,
        "tcp_flavor_claimed": tcp_flavor,
        "tcp_flavor_active": active_cc(),
        "background": background,
        "bidir": "yes" if bidir_flag else "no",
        "trial": trial,
        "duration": args.duration,
        "server_ip": args.server,
        "plan_file": os.path.abspath(args.plan),
    }
    with open(meta_txt, "w") as f:
        json.dump(meta, f, indent=2)


    # STEP4: run iperf while sending pings/boops in to calculate rrt while also sampling cwnd

    print(f" Running run #{args.run_id}: {scenario} / {link_setup} / {tcp_flavor} / {background} / bidir={'yes' if bidir_flag else 'no'} / trial={trial}")
    print(f" Active kernel congestion control: {meta['tcp_flavor_active']} (claimed: {tcp_flavor})")

    # start our ping and iperf servers
    boop_p  = start_boop(args.server, args.duration, rtt_txt)
    iperf_p = start_iperf(args.server, args.duration, bidir_flag, iperf_json)

    # iperf can take a sec to establish connection
    time.sleep(1)

    # cwnd sampling that runs in the background
    sample_cwnd(args.server, args.duration, cwnd_txt)

    # wait for iperf
    iperf_rc = iperf_p.wait()

    # make sure the ping stopped
    try:
        boop_p.terminate()
    except Exception:
        pass

    # STEP5: save everything
    
    print(f"iperf3 exit code: {iperf_rc}")
    print("Saved:")
    for p in (iperf_json, rtt_txt, cwnd_txt, meta_txt):
        print(f"    {p}")

if __name__ == "__main__":
    main()
