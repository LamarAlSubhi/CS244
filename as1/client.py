import socket, time, datetime, argparse, csv


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True, help="server IP (Wi-Fi or Ethernet)")
    ap.add_argument("--port", type=int, default=5001)    
    ap.add_argument("--label", default="wifi", help="run label: wifi or eth") 
    ap.add_argument("--payload", type=int, default=0, help="extra bytes to append")
    ap.add_argument("--interval", type=int, default=100)
    ap.add_argument("--count", type=int, default=10)

    return ap.parse_args()


def run():
    args = parse_args()
    HOST = args.host
    PORT = args.port
    COUNT = args.count
    INTERVAL = args.interval
    PAYLOAD = args.payload
    PADDING= "A" * PAYLOAD if PAYLOAD > 0 else ""
    LABEL = args.label
    LOG = f"logs/client_{LABEL}_p{PAYLOAD}_i{INTERVAL}_c{COUNT}.csv"

    f = open(LOG, "w", newline="")
    w = csv.writer(f)

    w.writerow(["seq","time_sent","time_received","OWD","payload_bytes"])

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print(f"client connected. host:{HOST} port:{PORT}")

        # SYNC HERE
        # 

        next_send = time.time()
        for seq in range(COUNT):  # 0 to COUNT-1
            now = time.time()

            # to avoid loop running faster than its supposed to
            if now < next_send:
                time.sleep(next_send - now)

            time_sent = time.time_ns()

            msg = f"BOOP,{seq},time_sent={time_sent:.9f},{PADDING}"

            
            # SEND
            s.sendall((msg + "\n").encode())
            print(f"[CLIENT] sent: {msg}")
            payload_bytes = len(msg.encode())
            
            # RECIEVE
            reply = s.recv(1024).decode().strip()
            print(f"[CLIENT] recv: {reply}")

            # TODO: parse time_receieved from reply and compute OWD = time_recieved - (time_sent + time_desync)
            parts = reply.split(",")
            seq = int(parts[1])
            time_recieved = float(parts[2].split("=", 1)[1])
            OWD = time_recieved - (time_sent)
            # TODO: append a CSV row here for analysis
            w.writerow([seq, f"{time_sent:.9f}", f"{time_recieved:.9f}", f"{OWD:.3f}", f"{payload_bytes}"])
            print(f"[CLIENT] seq={seq} OWD={OWD:.3f} ns")

            next_send += INTERVAL/ 1000.0

        print("[CLIENT] done")
        f.close()

if __name__ == "__main__":
    run()