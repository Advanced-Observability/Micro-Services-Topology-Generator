#!/bin/sh


# configuring network_switch_s1

ip link add frontend_s1 type veth peer name s1_frontend
pid=$(docker inspect -f '{{.State.Pid}}' frontend)
ip link set frontend_s1 netns $pid
docker exec frontend sh -c 'ip link set frontend_s1 up'
docker exec frontend sh -c 'ip addr add ::26:0:0:0:2/64 dev frontend_s1'
pid=$(docker inspect -f '{{.State.Pid}}' s1)
ip link set s1_frontend netns $pid
docker exec s1 sh -c 'ip link set s1_frontend up'
docker exec s1 sh -c 'ovs-vsctl add-port s1 s1_frontend tag=10'
ip link add s1_db type veth peer name db_s1
pid=$(docker inspect -f '{{.State.Pid}}' s1)
ip link set s1_db netns $pid
docker exec s1 sh -c 'ip link set s1_db up'
docker exec s1 sh -c 'ovs-vsctl add-port s1 s1_db tag=10'
pid=$(docker inspect -f '{{.State.Pid}}' db)
ip link set db_s1 netns $pid
docker exec db sh -c 'ip link set db_s1 up'
docker exec db sh -c 'ip addr add ::26:0:0:0:3/64 dev db_s1'

# configuring frontend #
docker exec frontend sh -c 'sh set_interfaces.sh'
docker exec frontend sh -c 'ip -6 r a 0:0:0:26::/64 encap ioam6 trace prealloc type 0x800000 ns 123 size 12 via ::26:0:0:0:3'
docker exec frontend sh -c 'ip r d default'
docker exec frontend sh -c 'ip -6 r d default'
docker exec frontend sh -c 'ip ioam namespace add 123'
docker exec frontend sh -c '/ioam-agent -i eth0'

# configuring db #
docker exec db sh -c 'ip -6 r d default'
docker exec db sh -c 'sh set_interfaces.sh'
docker exec db sh -c 'ip ioam namespace add 123'
docker exec db sh -c '/ioam-agent -i eth0'
docker exec db sh -c 'ip r d default'
docker exec db sh -c 'ip -6 r a 0:0:0:26::/64 via ::26:0:0:0:2'
