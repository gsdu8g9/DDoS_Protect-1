#!/usr/bin/env python

import subprocess as sp
from time import sleep
import signal
import sys
import struct
import socket
import array
import fcntl


def signal_handler(signal, frame):
    sys.exit(0)

COUNT = 0
ADDR = 1


def getIPs():
    p = sp.Popen("netstat -plan | grep :80 | awk '{print $5}' | cut -d : -f1 | sort -nk1 | uniq -c | sort -rnk1", shell=True, stdou                                                           t=sp.PIPE)
    output = p.stdout.readlines()
    return [ x.split() for x in output ]


def isDropped(ip):
    p = sp.Popen("csf -g " + ip[ADDR] + " | grep DROP", shell=True, stdout=sp.PIPE)
    if p.stdout.read():
        return True

    return False


def deny(ip, sec):
    cmd = "csf -td %s %s 'Blocked for %s connections'" % (ip[ADDR], sec, ip[COUNT])
    #sp.Popen("csf -td " + ip[ADDR] + " " + str(sec), shell=True, stdout=sp.PIPE)
    sp.Popen(cmd, shell=True, stdout=sp.PIPE)
    print ip[ADDR] + " has " + ip[COUNT] + " connections....dropping for " + str(sec/60) + " minutes!"


def get_local_IPs():
    struct_size = 40
    if 8*struct.calcsize('P') == 32:
        struct_size -= 8

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    max_possible = 8

    while True:
        bytes = max_possible * struct_size
        names = array.array('B', '\0' * bytes)
        outbytes = struct.unpack('iL', fcntl.ioctl(s.fileno(), 0x8912,
            struct.pack('iL', bytes, names.buffer_info()[0])))[0]
        if outbytes == bytes:
            max_possible *= 2
        else:
            break

    namestr = names.tostring()

    IPtuples = [(namestr[i:i+16].split('\0',1)[0],socket.inet_ntoa(
                    namestr[i+20:i+24])) for i in range(0, outbytes, struct_size)]

    ips = [ x[1] for x in IPtuples ]

    return ips

if __name__ == "__main__":

    signal.signal(signal.SIGINT, signal_handler)
    local_IPs = get_local_IPs()

    while True:

        for ip in getIPs():
            if len(ip) < 2:
                continue

            if ip[ADDR] in local_IPs:
                continue

            if isDropped(ip):
                continue

            cons = int(ip[COUNT])

            # getIPs sorts results based on number of connections, so if we hit an
            # IP with less than 30 connections, all the rest will also be < 30
            if cons < 35:
                break

            elif cons >= 35 and cons < 60:
                deny(ip, 300)

            elif cons >= 60 and cons < 90:
                deny(ip, 600)

            elif cons >= 90:
                deny(ip, 1800)

        sleep(10)
