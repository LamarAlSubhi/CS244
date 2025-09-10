import socket, time, datetime, argparse

# I will need to use 2 different connection types to compare their delays
# "both wired and wireless interfaces (e.g., eth0 vs wlan0)"


#AF_INET address family
# socket object expects this pair of arguments, it determines interface
HOST = "temp" # wired/wireless interface IP address
PORT =  5000 # any available port

# AF_INET: address family for IPv4, SOCK_STREAM: TCP
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))    
s.listen(1)


conn, addr = s.accept()



#TODO: Function that establishes connection
# TODO: Function that receives
# TODO: Function that sends 
# TODO: Function that calculates time 