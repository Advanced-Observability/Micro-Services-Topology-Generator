# Dockerfile for router without CLT

FROM alpine:latest

# Install requried packages
RUN apk update
RUN apk add iproute2 iproute2-tc iptables --no-cache

# Copy script to set interfaces
COPY set_interfaces.sh set_interfaces.sh

CMD ["echo", "start"]
