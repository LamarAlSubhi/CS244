# Expect
- some flavors to be really good and more traditional ones should be slower
- fairness issue clear

# Steps for me:

## Set Up:
- Omen as client (can run on wifi and eth)
- Macbook as server (can only run on wifi)


## Make a data schema before I collect anything
- timestamp 
- hostnames 
- interface
- SSID/channel 
- TCP flavor
- server location 
- background load 
- test duration
- mean throughput
- p50/p90/p99 throughput
- mean RTT 
- p95 RTT 
- loss %
- CWND samples (serialized)
- notes

## Metrics:
- Throughput over time: iPerf3 interval logs
- Delay/Jitter: ping/owping during the iPerf run and/or iPerf latency stats
- CWND (and pacing/RTT): ss -ti snapshots at fixed intervals, maybe add kernel tracing later for bonus insight

## Plots:
- (A) Throughput over time: 4 sub-traces overlaid per interface (one figure for Ethernet, one for Wi-Fi)
- (B) Delay over time: same structure as (A)
- (C) CWND comparison: one consolidated figure with all flavors (pick representative runs or show median-of-three)

