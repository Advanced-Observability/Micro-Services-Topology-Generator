# Docker Compose templates

Templates to generate a Docker Compose configuration file.

## Files

The files in the folder are the following ones.

### Shared for IPv4 and IPv6

- [external-template.yaml](./external-template.yaml) is a template for a service using a provided Docker image;
- [firewall-template.yaml](./firewall-template.yaml) is a template for a firewall;
- [service-template.yaml](./service-template.yaml) is a template for a generic microservice;
- [router-template.yaml](./router-template.yaml) is a template for a router;
- [jaeger-service.yaml](./jaeger-service.yaml) is a template for Jaeger.

### IPv4

- [network-template-ipv4.yaml](./network-template-ipv4.yaml) is a template for a docker network with IPv4;
- [telemetry-network-ipv4.yaml](./telemetry-network-ipv4.yaml) is a template for a telemtry network with IPv4.

### IPv6

- [ioam-collector-ipv6.yaml](./ioam-collector-ipv6.yaml) contains the service for the IOAM collector with IPv6;
- [network-template-ipv6.yaml](./network-template-ipv6.yaml) is a template for a docker network with IPv6;
- [telemetry-network-ipv6.yaml](./telemetry-network-ipv6.yaml) is a template for a telemetry network with IPv6.
