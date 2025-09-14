import socket, time, argparse, csv, os


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True, help="server IP (Wi-Fi or Ethernet)")
    ap.add_argument("--port", type=int, default=5001)    
    ap.add_argument("--label", default="wifi", help="run label: wifi or eth") 
    ap.add_argument("--payload", type=int, default=0, help="extra bytes to append")
    ap.add_argument("--interval", type=int, default=100)
    ap.add_argument("--count", type=int, default=10)

    return ap.parse_args()

# this estimates clock offset
def sync(s, seq=20):

    print("------------------- SYNC PHASE -------------------")
    offsets = []

    for i in range(seq):

        # t0: client time before send
        t0 = time.time_ns()
        msg = f"SYNC,{i},t0={t0}"
        s.sendall((msg + "\n").encode())

        # read one full reply line
        reply = s.recv(1024).decode().strip()

        # t2: client time right after recive
        t2 = time.time_ns()
        # expect "SYNC_ACK,{i},t1={t1}"
        parts = reply.split(",")

        # t1: server time when recieved
        t1 = int(parts[2].split("t1=", 1)[1])

        roundtrip = t2 - t0
        offsets.append(t1 - (t0 + roundtrip // 2))

        # just to control pacing 
        time.sleep(0.005)

    offsets.sort()
    median = offsets[len(offsets) // 2]

    print(f"------------------- SYNC DONE offset={median} -------------------")

    return median



def run():
    args = parse_args()
    HOST = args.host
    PORT = args.port
    COUNT = args.count
    INTERVAL = args.interval
    PAYLOAD = args.payload
    PADDING= "A" * PAYLOAD if PAYLOAD > 0 else ""
    LABEL = args.label


    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print(f"client connected. host:{HOST} port:{PORT}")

        # SYNC HERE
        offset = sync(s)

        # initialize log
        os.makedirs("logs", exist_ok=True)
        LOG = f"logs/client_{LABEL}_p{PAYLOAD}_i{INTERVAL}_c{COUNT}.csv"
        f = open(LOG, "w", newline="")
        w = csv.writer(f)
        w.writerow(f["seq","time_sent","time_received","delay(offset={offset})","payload_bytes"])

        next_send = time.time()
        for seq in range(COUNT):  # 0 to COUNT-1
            now = time.time()

            # to avoid loop running faster than its supposed to
            if now < next_send:
                time.sleep(next_send - now)

            t0 = time.time_ns()

            msg = f"BOOP,{seq},time_sent={t0},{PADDING}"
            
            # SEND
            s.sendall((msg + "\n").encode())
            # print(f"[CLIENT] sent: {msg}")
            payload_bytes = len(msg.encode())
            
            # RECIEVE
            reply = s.recv(1024).decode().strip()
            # print(f"[CLIENT] recv: {reply}")

            # parse time_receieved from reply and compute OWD = time_recieved - (time_sent + time_desync)
            parts = reply.split(",", 2)
            seq = int(parts[1])
            t1 = float(parts[2].split("t1=", 1)[1])
            OWD = (t1 - offset) - t0

            # append a CSV row here for analysis
            w.writerow([seq, f"{t0}", f"{t1}", f"{OWD}", f"{payload_bytes}"])
            # print(f"[CLIENT] seq={seq} OWD={OWD:.3f} ns")

            next_send += INTERVAL/ 1000.0

        print("[CLIENT] done")
        f.close()

if __name__ == "__main__":
    run()