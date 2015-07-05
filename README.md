mullvad_bootstrap
=================

Bootstrap a VPN connection from a Mullvad test account


Installation
------------

```
$ sudo su -
[sudo] password for user:
% pip install -r requirements.txt
% python setup.py install
```

Usage
-----

```
% mullvad -h
usage: mullvad [-h] sub-command ...

Manage your Mullvad VPN connection.

positional arguments:
  sub-command
    bootstrap  Bootstrap a VPN connection from a new Mullvad test account.
    protect    Block all traffic not going through the VPN tunnel.

optional arguments:
  -h, --help   show this help message and exit
%
```

```
% mullvad bootstrap -h
usage: mullvad bootstrap [-h] [-e TLD]

optional arguments:
  -h, --help            show this help message and exit
  -e TLD, --exit-country TLD
                        select an exit country [default: se]
%
```

```
% mullvad protect -h
usage: mullvad protect [-h] [-t DEV]

optional arguments:
  -h, --help            show this help message and exit
  -t DEV, --tunnel-device DEV
                        The virtual network device of the tunnel [default:
                        tun0]
%
```


In Action
---------

```
$ sudo su -
[sudo] password for user:
% mullvad bootstrap

Mullvad provides an awesome service!!1
Support them by adding a monthly subscription to your account.
Help keep the service alive!

Enter captcha: mtun
[*] Downloading config...
[*] Unzipping file '/tmp/tmpxxsmdA/mullvadconfig.zip'
[*] Extracting '^dev (\w+)$' from '/tmp/tmpxxsmdA/257556565089/mullvad_linux.conf'
[*] Moving files from '/tmp/tmpxxsmdA/257556565089' to '/etc/openvpn/'
[*] Removing '/tmp/tmpxxsmdA'
[*] Getting connection info...
[*] Restarting VPN service...
[*] Detecting tunnel device....
[*] Waiting for routes to be established
[*] Removing default route from interface eth0
Kernel IP routing table
Destination     Gateway         Genmask         Flags Metric Ref    Use Iface
0.0.0.0         10.114.0.1      128.0.0.0       UG    0      0        0 tun0
10.114.0.0      0.0.0.0         255.255.0.0     U     0      0        0 tun0
128.0.0.0       10.114.0.1      128.0.0.0       UG    0      0        0 tun0
169.254.0.0     0.0.0.0         255.255.0.0     U     1000   0        0 eth0
192.168.1.0     0.0.0.0         255.255.255.0   U     0      0        0 eth0
193.138.219.226 192.168.1.1     255.255.255.255 UGH   0      0        0 eth0

[*] Pinging 4.2.2.2...
PING 4.2.2.2 (4.2.2.2) 56(84) bytes of data.
64 bytes from 4.2.2.2: icmp_seq=1 ttl=52 time=74.7 ms
64 bytes from 4.2.2.2: icmp_seq=2 ttl=52 time=74.3 ms
64 bytes from 4.2.2.2: icmp_seq=3 ttl=52 time=74.4 ms
64 bytes from 4.2.2.2: icmp_seq=4 ttl=52 time=74.6 ms

--- 4.2.2.2 ping statistics ---
4 packets transmitted, 4 received, 0% packet loss, time 3004ms
rtt min/avg/max/mdev = 74.372/74.567/74.764/0.311 ms

[*] Checking external IP...
    [*] Getting connection info...
Original connection:
 - ISP: Simply Transit Ltd in Europe/United Kingdom
 - IP: 85.234.144.42 (85-234-144-42.static.as29550.net)
Current connection:
 - ISP: 31173 Services Ab in Europe/Sweden
 - IP: 193.138.219.228 (se3x.mullvad.net)

Bootstrapped a VPN connection from new Mullvad account 257556565089.
%
```

```
% mullvad protect

Mullvad provides an awesome service!!1
Support them by adding a monthly subscription to your account.
Help keep the service alive!

[*] Backing up firewall configuration to '/tmp/tmpplpX32/iptables.cfg.bak'
[*] Blocking relatable traffic...
    [*] Resetting config
    [*] Allowing traffic over loopback interface
    [*] Allowing traffic over local networks
        [*] Skipping inactive interface eth0
        [*] Allowing traffic over eth0 for 192.168.1.0/24
    [*] Allowing traffic over VPN interface
    [*] Allowing traffic to VPN gateway
        [*] Resolving IP of VPN gateway...........
    [*] Dropping all other traffic
Chain INPUT (policy DROP 0 packets, 0 bytes)
 pkts bytes target     prot opt in     out     source               destination
    0     0 ACCEPT     udp  --  eth0   any     se3.mullvad.net      anywhere             udp spt:1300
   63  4139 ACCEPT     all  --  tun0   any     anywhere             anywhere
    6   423 ACCEPT     all  --  eth0   any     192.168.1.0/24       anywhere
   62  6372 ACCEPT     all  --  lo     any     anywhere             anywhere

Chain FORWARD (policy DROP 0 packets, 0 bytes)
 pkts bytes target     prot opt in     out     source               destination

Chain OUTPUT (policy DROP 0 packets, 0 bytes)
 pkts bytes target     prot opt in     out     source               destination
    0     0 ACCEPT     udp  --  any    eth0    anywhere             se3.mullvad.net      udp dpt:1300
   73  4247 ACCEPT     all  --  any    tun0    anywhere             anywhere
    0     0 ACCEPT     all  --  any    eth0    anywhere             192.168.1.0/24
   62  6372 ACCEPT     all  --  any    lo      anywhere             anywhere
[*] Enter 'vxls' to terminate protection
Security code:
```

```
Security code: vxls
[*] Restoring firewall configuration from '/tmp/tmpplpX32/iptables.cfg.bak'
    [*] Removing '/tmp/tmpplpX32'
%
```
