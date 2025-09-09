import socket, time, datetime, argparse

# I will need to use 2 different connection types to compare their delays
# "both wired and wireless interfaces (e.g., eth0 vs wlan0)"


# socket object expects this pair of arguments, it determines interface
HOST = "temp"
PORT =  0000

#AF_INET is
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))    
s.listen(1)


conn, addr = s.accept()