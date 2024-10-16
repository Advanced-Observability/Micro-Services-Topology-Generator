# Build IOAM collector
FROM golang:1.22-alpine AS build

RUN apk add protobuf protobuf-dev
RUN go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
RUN go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

WORKDIR /apps

# Build IOAM API for gRPC
RUN wget https://raw.githubusercontent.com/Advanced-Observability/ioam-api/clt/ioam_api.proto
RUN protoc --go_out=. --go-grpc_out=. ioam_api.proto

# Build IOAM collector
COPY ioam-collector.go ioam-collector.go
RUN go mod init ioam-collector
RUN go mod tidy
RUN CGO_ENABLED=0 go build ioam-collector.go

# --------------------------------------------------------------

# Run IOAM collector
FROM alpine:latest

COPY --from=build /apps/ioam-collector /

ENTRYPOINT ["/ioam-collector"]
