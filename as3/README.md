# my notes

## plan:
1. Identify driver and kernel limits
2. Locate older kernel that allows ring tuning
3. Run experiments with both queues adjustable
4. Analyze + conclude

## research:
- OS and NIC (network card) coordinate to send packets by communicating using a shared memory area
- they use a circular buffer also called the ring buffer
- each spot in that buffer contains the metadata of one packet
- so this ring is the shared queue between software and hardware 
- it’s where the kernel and NIC hand off work to eachother asynchronously

### we have 2 rings
- TX ring: holds the packets that are waiting to be sent on the wire
- RX ring: holds memory slots for incoming packets

### what does the journey look like
- transmitting: application buffer -> socket buffer -> kernel queue -> TX ring ->  NIC hardware -> physical wire
- recieving: physical wire -> NIC hardware -> RX ring -> kernel queue -> socket buffer -> application buffer

### what does it mean
- if kernel queue is short, but the ring is long: the packets will pile up inside the NIC => hidden delay
- if ring is too short: NIC runs out of packets to send => throughput drops

## plots:
- throughput
- CWND RTT
- loss
- queue backlog
- TX/RX errors/drops


## issues running into: 
- My omen's driver, r8169 (Realtek), never implemented set_ring, so it doesn’t matter which kernel I use
- by reinstalling windows i somehow broke my current networkmanager on linux mashallah 3alaya: a stale EFI mount in /etc/fstab forced emergency mode; then a half-installed kernel (6.14.0-33) left /lib/modules empty, so GPU and NIC drivers couldn’t load. Booting the previous kernel (6.14.0-29) and fixing fstab resolved it.


## set up:
- installed virtual box and ra
- set adapter type as: Intel PRO/1000 MT Desktop (82540EM)

