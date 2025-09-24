# Assignment 2: Network Performance Using Different TCP Congestion Control Algorithms Basics

In this assignment, you will explore and compare the behavior of different TCP
congestion control algorithms over wired and wireless interfaces. Your goal is to
observe how each algorithm adapts to various network conditions in terms of
throughput, delay, and congestion window size.

You will use the iPerf tool to generate traffic while varying the TCP algorithm in use.
Four TCP flavors will be considered: TCP BBR, TCP CUBIC, TCP Reno, and TCP
Vegas. These are implemented in the Linux kernel (4.9+), and must be enabled
explicitly before testing.

This is an individual assignment and has to be done without the assistance of others.
You should present your work to the class and expect a technical discussion.

## Preparing TCP Congestion Control Setup:
- Linux provides support for multiple congestion control algorithms, which you can list
using:
    - sysctl net.ipv4.tcp_available_congestion_control
- To switch between algorithms:
    - sysctl -w net.ipv4.tcp_congestion_control=bbr
- You are encouraged to use Linux tools (e.g., iperf3, tc, and netstat) and monitor the behavior of each TCP flavor under both wired (eth0) and wireless (wlan0) interfaces. Ensure that you enable each TCP flavor individually during each test run.
- If needed, refer to:
    - iPerf: https://iperf.fr
    - TCP congestion control overview: Linux TCP Docs

## Getting Started
Before starting, review available documentation on TCP congestion control, including
the role of RTT estimation, delivery rate, and loss recovery. Explore how each TCP
flavor differs in its control loop (e.g., Reno is loss-based, Vegas is delay-based, BBR is
rate-based).

You are expected to test each TCP flavor over:
    - Wired and wireless connections
    - Varying background traffic or link conditions
    - Different geographical iPerf server locations
You may use monitoring tools such as netstat, ss, tcptrace, or logging in iPerf3 for visualization.

Your goal is to investigate the effect of different TCP congestion control strategies under
diverse network conditions.

## You must complete the following tasks:
1. Throughput Comparison:
    - Use iPerf to generate traffic using each TCP flavor (BBR, CUBIC, Reno, Vegas).
    - Record and plot TCP throughput over time on both wired and wireless interfaces.
    - Explain the observed differences based on the nature of each algorithm.
2. Delay Analysis:
    - Measure and plot end-to-end delay (e.g., using owping, ping, or iPerf delay stats).
    - Compare the delay performance of each TCP algorithm under wired and wireless conditions.
    - Discuss how delay control (especially in TCP Vegas and BBR) affects performance.
3. Congestion Window Observation:
    - Plot the evolution of the congestion window (CWND) for each TCP flavor.
    - Try to infer CWND behavior using ss -ti or kernel tracing utilities.
    - Provide one consolidated figure comparing all CWND traces.
4. Best Performing TCP Flavor:
    - From your data, identify the optimal TCP flavor in terms of throughput, delay, and stability.
    - Provide justification supported by plots and statistics.

## Deliverables
You are expected to demonstrate the network behavior and performance metrics as
follows:
- Submit by email to the instructor:
    - All scripts or configuration files used to run your experiments in a readme.txt file
    - Output files (logs, CSVs, plots)
    - A README file describing your testing setup, interface configurations, and algorithm workflow
- A 5–8 slide presentation that:
    - Summarizes methodology
    - Shows comparative plots and performance insights
    - Presents key takeaways and limitations