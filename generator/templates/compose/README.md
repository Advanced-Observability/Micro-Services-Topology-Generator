# Docker Compose templates

Templates to generate a Docker Compose configuration file.

## Files

The files in the folder are the following ones.

### Shared for IPv4 and IPv6

- [external-template.yml](./external-template.yml) is a template for a service using a provided Docker image;
- [firewall-template.yml](./firewall-template.yml) is a template for a firewall;
- [service-template.yml](./service-template.yml) is a template for a generic microservice;
- [router-template.yml](./router-template.yml) is a template for a router;
- [jaeger-service.yml](./jaeger-service.yml) is a template for Jaeger.

### IPv4

- [network-template-ipv4.yml](./network-template-ipv4.yml) is a template for a docker network with IPv4;
- [telemetry-network-ipv4.yml](./telemetry-network-ipv4.yml) is a template for a telemtry network with IPv4.

### IPv6

- [ioam-collector-ipv6.yml](./ioam-collector-ipv6.yml) contains the service for the IOAM collector with IPv6;
- [network-template-ipv6.yml](./network-template-ipv6.yml) is a template for a docker network with IPv6;
- [telemetry-network-ipv6.yml](./telemetry-network-ipv6.yml) is a template for a telemetry network with IPv6.
