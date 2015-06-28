mullvad_bootstrap
=================

Bootstrap a VPN connection from a Mullvad test account

Usage
-----

```
$ sudo su -
[sudo] password for user: 
# cd /path/to/mullvad_bootstrap
# PYTHONPATH=. python bin/mullvad
Enter captcha: foob
Downloading config...
Unzipping file /tmp/tmpe4Uz9l/mullvadconfig.zip
Moving files from '/tmp/tmpe4Uz9l/377836838570' to '/etc/openvpn/'
Starting VPN service...
Waiting for routes to be established.....
Removing default route from interface wlan0
Kernel IP routing table
Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
0.0.0.0         10.114.0.1      128.0.0.0       UG    0      0        0 tun0
10.114.0.0      0.0.0.0         255.255.0.0     U     0      0        0 tun0
128.0.0.0       10.114.0.1      128.0.0.0       UG    0      0        0 tun0
169.254.0.0     0.0.0.0         255.255.0.0     U     1000   0        0 eth0
192.168.1.0     0.0.0.0         255.255.255.0   U     0      0        0 eth0
193.138.219.226 192.168.1.1     255.255.255.255 UGH   0      0        0 eth0

Pinging 4.2.2.2...
PING 4.2.2.2 (4.2.2.2) 56(84) bytes of data.
64 bytes from 4.2.2.2: icmp_seq=1 ttl=52 time=74.7 ms
64 bytes from 4.2.2.2: icmp_seq=2 ttl=52 time=74.3 ms
64 bytes from 4.2.2.2: icmp_seq=3 ttl=52 time=74.4 ms
64 bytes from 4.2.2.2: icmp_seq=4 ttl=52 time=74.6 ms

--- 4.2.2.2 ping statistics ---
4 packets transmitted, 4 received, 0% packet loss, time 3004ms
rtt min/avg/max/mdev = 74.372/74.567/74.764/0.311 ms

Checking external IP...
 - ISP: 31173 Services Ab in Europe/Sweden
 - IP: 193.138.219.228 (se3x.mullvad.net)
Successfully bootstrapped a Mullvad VPN account
#
```
