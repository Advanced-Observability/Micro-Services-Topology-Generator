# Dockerfile for service without CLT

# Runner
FROM alpine:3.19

# Install requried packages
RUN apk add iproute2 iproute2-tc iptables --no-cache

# Copy Go service and config
COPY ./service /usr/local/bin/
COPY ./config.yml /etc/

# Copy key and certificate
COPY server.key server.key
COPY server.crt server.crt

# Copy script to set interfaces
COPY set_interfaces.sh set_interfaces.sh

CMD ["echo", "start"]
