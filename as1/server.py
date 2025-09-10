import socket, time, datetime, argparse

# I will need to use 2 different connection types to compare their delays
# "both wired and wireless interfaces (e.g., eth0 vs wlan0)"
def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True, help="server IP (Wi-Fi or Ethernet)")
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

                # client should send BOOP,{seq},time_sent={time_sent},{padding}
                parts = line.split(",", 3)

                seq = parts[1]
                time_recieved = time.time_ns()  # server receive time
                reply = f"ACK,{seq},time_received={time_recieved:.9f}"
                conn.sendall((reply+"\n").encode())


        # WITH BUFFER
        # with conn:
        #     r = conn.makefile("r", buffering=1, encoding="utf-8", newline="\n")
        #     w = conn.makefile("w", buffering=1, encoding="utf-8", newline="\n")

        #     for line in r:
        #         line = line.strip()
        #         if not line:
        #             continue

        #         # SYNC HERE?

        #         # client should send BOOP,{seq},time_sent={time_sent}
        #         parts = line.split(",", 2)
        #         #ignore BOOP
        #         seq = parts[1]
        #         time_recieved = time.time()  # server receive timestamp

        #         # Reply with ACK carrying t1 so the client can compute OWD
        #         w.write(f"ACK,{seq},time_received={time_recieved:.9f}\n")
        #         w.flush()

if __name__ == "__main__":
    run()