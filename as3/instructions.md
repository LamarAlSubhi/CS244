# Assignment 3: Queueing in the Linux Network Stack: Delay vs. Throughput Tradeoffs

In this assignment, you will study the effect of packet queue sizes on network delay and throughput by modifying buffer parameters in the Linux network stack. Queues are a fundamental part of any networking system, enabling asynchronous communication between modules and improving link utilization. However, misconfigured queues — especially oversized ones — can introduce bufferbloat, leading to significant increases in end-to-end delay.

The goal is to understand where queuing happens in the Linux stack (e.g., in the qdisc layer or driver queues) and how transmission queue size affects the performance of TCP/UDP traffic across wired and wireless interfaces.

## Preparing Queueing Experiments
In Linux, queueing disciplines (qdiscs) and buffer settings can be manipulated using
tools such as:
- tc (traffic control)
- sysctl (for kernel parameters)
- /proc/net/ and /sys/class/net/ interfaces

To configure the transmission queue length:
- ifconfig eth0 txqueuelen 100
- ip link set dev eth0 txqueuelen 100
You can also manipulate advanced queuing disciplines (e.g., fq, pfifo_fast, netem) using
tc:
- tc qdisc add dev eth0 root fq
- tc qdisc change dev eth0 root pfifo limit 100

Use tools such as iperf3, ping, traceroute, and ss to monitor the traffic. 

You may also inspect buffer occupancy using /proc/net/netstat and interface stats via
- /sys/class/net/<iface>/statistics/

## Getting Started
Before you begin experimentation, you are encouraged to review Linux queueing documentation and existing research on bufferbloat. 

Specifically, consider how:
- Small queues may result in early packet drops and throughput degradation.
- Large queues reduce packet loss but introduce high latency.
- TCP’s congestion control interacts with queue length to shape flow behavior.

You will examine how changing the transmission queue size affects delay, throughput, and overall link performance over both wired and wireless interfaces.

## Assignment
You are required to analyze both TCP throughput and delay in Linux by systematically modifying queue sizes and observing the resulting behavior.

#### Tasks:
##### 1. Throughput Analysis
- Use iPerf to generate TCP (or optionally UDP) traffic over wired and wireless interfaces.
- Modify the transmission queue size and plot TCP throughput under each setting.
- Discuss how queue size impacts link utilization.
##### 2. Delay Analysis
- Measure and plot end-to-end delay (e.g., using ping, or timestamps in packet traces).
- Analyze how increasing or decreasing queue size affects packet latency.
- Highlight cases where queueing leads to bufferbloat.
##### 3. Optimal Queue Configuration
- Identify the optimal queue size that minimizes delay while maintaining sufficient throughput.
- Define a reasonable delay threshold for acceptable application performance (e.g., <100 ms). Make sure to understand the application delay requirements!
- Justify your choice using plotted data and observations.

Repeat the experiment using different traffic types (e.g., short bursts vs. bulk transfers) or congestion control algorithms for deeper analysis.

## Deliverables
Submit to the instructor via email:
- All scripts, configuration files, or tools used in the tests
- Output data (logs, statistics, CSVs)
- A README file documenting your experiment setup, system environment, queueing configurations, and summary of findings

A short presentation (5–8 slides) that:
- Describes your methodology
- Presents your plots (throughput, delay vs. queue size)
- Summarizes conclusions about optimal queue sizing