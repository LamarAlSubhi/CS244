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

## Runs
1. Baseline (16 runs):
    - No background traffic.
	- Both link setups: WiFi–WiFi and Ethernet–WiFi.
	- All four TCP congestion control algorithms (BBR, CUBIC, Reno, Vegas).
	- Two trials (A and B) for each.
    - This gives me a clean reference for how each algorithm behaves under stable vs variable links.

2.	Light Background (16 runs):
	- Same coverage as Baseline (WiFi–WiFi + Ethernet–WiFi, four algorithms, two trials).
	- Adds a small amount of background traffic (light contention).
    - This shows how algorithms degrade when the channel is moderately busy.

3.	Heavy Background (16 runs):
	- Again, full coverage of both link setups and all four algorithms, with two trials.
	- Uses a heavy, sustained background load to stress the link.
    - This reveals which algorithms are most robust when the channel is near saturation.

4.	Bonus Bidirectional Heavy (8 runs):
	- Only for BBR and CUBIC (the most contrasting algorithms).
	- Tested under heavy background traffic, but with bidirectional data transfer enabled (both client and server send simultaneously).
	- Done for both WiFi–WiFi and Ethernet–WiFi, with two trials each.
    - This highlights Wi-Fi’s half-duplex nature and how up/down contention interacts with congestion control.

## TCP Flavors:
- Reno → Classic, loss-based: reduce window when a packet is lost.
- CUBIC → Default in Linux: uses a cubic growth function, more aggressive than Reno.
- Vegas → Delay-based: tries to detect congestion early from RTT increases.
- BBR → Rate-based: models bottleneck bandwidth + RTT, doesn’t wait for loss.