## Set Up:
- Omen as client (can run on wifi and eth)
- Macbook as server (can only run on wifi)


## Input
- run_id
- scenario
- link_setup
- tcp_flavor
- background
- bidir
- trial


## Output
- run_id,
- scenario,
- link_setup,
- tcp_flavor,
- background,
- bidir,
- trial,
- mean_throughput_mbps,
- p90_throughput_mbps,
- p95_throughput_mbps,
- mean_rtt_ms,
- p90_rtt_ms,
- p95_rtt_ms,
- retrans_total,
- median_cwnd_bytes,
- p95_cwnd_bytes


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
- Reno → Classic, loss-based: reduce window when a packet is lost (under-utilizing bandwidth).
- CUBIC → Default in Linux: uses a cubic growth function, more aggressive than Reno (higher throughput but more delay).
- Vegas → Delay-based: tries to detect congestion early from RTT increases(lower throughput but lower RTT).
- BBR → Rate-based: models bottleneck bandwidth + RTT, doesn’t wait for loss (higher throughput but more delay).