import socket, time, datetime, argparse

# I will need to use 2 different connection types to compare their delays
# "both wired and wireless interfaces (e.g., eth0 vs wlan0)"
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True, help="server IP")
    ap.add_argument("--port", type=int, default=5001)   
    return ap.parse_args()


def run():
    args = parse_args()
    HOST = args.host
    PORT = args.port

    # AF_INET: address family for IPv4, SOCK_STREAM: TCP
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:

        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(1)
        print(f"[SERVER] bound host:{HOST} port:{PORT}")

        conn, addr = s.accept()
        print("[SERVER] connection accepted from:", addr)
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        # since TCP is a data stream, we gotta listen for whole line
        buffer = ""
        while True:
            data = conn.recv(1024)
            if not data:
                break  # connection closed
            buffer += data.decode()

            # process all complete lines
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                # client should send BOOP,{seq},t0={t0},{padding}
                # or SYNC,{round},t0={t0}
                parts = line.split(",", 2)
                t1 = time.time_ns()  # server receive time
                seq = parts[1]

                if parts[0] == "SYNC":
                    reply = f"SYNC_ACK,{seq},t1={t1}"
                    
                else:
                    
                    reply = f"ACK,{seq},t1={t1}"
                conn.sendall((reply+"\n").encode())
                print(reply)


if __name__ == "__main__":
    run()