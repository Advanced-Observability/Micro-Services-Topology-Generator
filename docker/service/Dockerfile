# Dockerfile for service without CLT

# Runner
FROM alpine:3.19 as runner

# Install requried packages
RUN apk add iproute2 iproute2-tc iptables --no-cache

# Copy Go service and config
COPY ./service /usr/local/bin/
COPY ./config.yml /etc/

# Copy key and certificate
COPY server.key server.key
COPY server.crt server.crt

CMD ["echo", "start"]
