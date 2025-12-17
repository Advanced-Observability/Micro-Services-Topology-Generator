#!/bin/sh

id=$(sysctl net.ipv6.ioam6_id | awk '{print $3}')

for sInterface in /proc/sys/net/ipv6/conf/*; do sysctl -q -w $sInterface.ioam6_enabled=1; sysctl -q -w $sInterface.ioam6_id=$id; done

exit 0
