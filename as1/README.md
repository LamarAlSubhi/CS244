# Assignment 1: Custom One-Way Delay (OWD) Measurement Using Python

## Files Included
- PDF with scripts (client.py and server.py) and analysis
- Presentation

## Things to look out for
- Presentation 8 slides straight to the point, methodology, topology, parameters, wireless, wired, observations and questions, 6 mins
- PDF with scripts and analysis
- Flavor of research
- How i overcame problem NAT issue, reposition server, problem solving
- Troubleshooting
- Why are peaks happening, expected answer, i searched and this is

## How to Run Scripts:

### client.py
- required arguments: --host
- optional arguemnts: 
    - --port: port used
    - --label: Wifi or eth
    - --payload: an estimate of the message size you want 
    - --interval: how often to send messages in milliseconds 
    - --count: total number of messages to send
- example: python3 server.py --host 192.168.8.30 --port 5001 --label wifi --payload 64 --interval 100 --count 50

### server.py
- required arguments: --host 
- optional arguemnts: --port 
- example: python3 server.py --host 192.168.8.30 --port 5001 
