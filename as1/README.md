## Assignment 1: Custom One-Way Delay (OWD) Measurement Using Python

# Requirements
1. Time Sync Setup:
    - Simulate time synchronization between client and server.
    - Assume near-perfect sync or apply a simple NTP-like model (e.g., roundtrip-based estimation).

2. Client Program:
    - Sends timestamped packets at regular intervals (e.g., every 100ms).
    - Logs sent timestamps and sequence numbers.

3. Server Program:
    - Receives packets, timestamps them upon arrival.
    - Logs received time and sequence number.
4. OWD Computation:
    - OWD = (Server Receive Time) − (Client Send Time)
    - Implement client-side and/or server-side processing to calculate delays.
5. Test Scenarios:
    - Use both wired and wireless interfaces (e.g., eth0 vs wlan0).
    - Vary packet size, interval, and background load.
6. Plots and Analysis:
    - Plot delay over time for both interfaces.
    - Plot packet loss (if any).
    - Compare average OWD, variance, and jitter.