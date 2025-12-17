# Dockerfile for service without CLT
FROM golang:1.24-alpine AS builder

WORKDIR /app
COPY ./dummy-service/* .
RUN go mod init dummy-service
RUN go mod tidy
RUN CGO_ENABLED=0 go build -tags netgo -o /usr/local/bin/service

# Runner
FROM alpine:3.19

# Install requried packages
RUN apk add iproute2 iproute2-tc iptables tcpdump --no-cache

# Copy Go service and config
COPY --from=builder /usr/local/bin/service /usr/local/bin/
COPY ./config.yaml /etc/

# Copy key and certificate
COPY ./server.key server.key
COPY ./server.crt server.crt

# Copy script to set interfaces
COPY ./set_interfaces.sh set_interfaces.sh

CMD ["/usr/local/bin/service", "/etc/config.yaml"]
