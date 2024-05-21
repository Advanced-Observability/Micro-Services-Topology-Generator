# Dockerfiles

This folder contains the Dockerfiles that will be used to create the containers representing the various elements of the architecture.

## [IOAM collector](./ioam-collector/)

Docker container containing the [ioam-collector-go-jaeger](https://github.com/Advanced-Observability/ioam-collector-go-jaeger), which is responsible for converting IOAM data into OpenTelemetry traces.

## [Router](./router/)

Represents a router in the topology.

## [Service](./service/)

Represents a service in the topology.
