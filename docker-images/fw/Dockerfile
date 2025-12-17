# Dockerfile for firewall

FROM alpine:3.19

# Install required packages
RUN apk update
RUN apk add iproute2 iproute2-tc iptables --no-cache

CMD ["echo", "start"]
