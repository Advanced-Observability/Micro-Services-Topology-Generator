# Usage

## Specify the architecture

When invoking `make` commands, the architecture configuration file can be specified as follows:
```bash
CONFIG=<file> make
```

Alternatively, if no argument is given, `make` will look for a file named `config.yml`.

See [configuration.md](./configuration.md) for how to write the architecture file and [configuration_examples](./configuration_examples) directory for examples.

## Build the Docker images

Then, you need to build the Docker images with the following command:
```bash
make images
```

The Docker images for the version using CLT can be built with:
```bash
make images_clt
```

## Generation

You have 2 possibilities when it comes to the output of the generator:

- You can generate a **Docker Compose file**, which can be used to deploy the topology on a *single machine*;
- You can generate the configuration files for **Kubernetes**, which can be used to deploy the topology on *one or more machines*.

### Docker Compose

You can generate the architecture with IPv4 or IPv6 with the following commands:
```bash
make ipv4
make ipv6
```

If you want to enable Jaeger to see the traces, you can use one of the following commands depending on whether you want the topology to use IPv4 or IPv6:
```bash
make ipv4_jaeger
make ipv6_jaeger
```

If you want to generate the architecture with CLT, which always uses IPv6 and Jaeger, you can use the command:
```bash
make clt
```

You can add `_https` at the end of each of the previous command (e.g. `make ipv4_https`) to use HTTPS instead of HTTP.

You can start the architecture with:
```bash
make start
```

You can make requests to the services using the following commands and replacing `<port>` with the port of the service to which you want to send a request:
```bash
curl "http://127.0.0.1:<port>/" # IPv4 + HTTP
curl -6 "http://[::1]:<port>/" # IPV6 + HTTP
curl --insecure "https://127.0.0.1:<port>/" # IPv4 + HTTPS
curl --insecure -6 "https://[::1]:<port>/" # IPv6 + HTTPS
```

Choose the command based on which version of IP and HTTP you chose to generate the architecture.

When using HTTPS, you need to add `--insecure` because the services use a self-signed certificate.

If you decided to enable Jaeger, you can see the traces by opening the URL [http://localhost:16686/](http://localhost:16686/) in your Web browser of choice.

You can stop the architecture with:
```bash
make stop
```

### Kubernetes

See [K8S.md](./K8S.md) for explanations regarding the deployment to Kubernetes.
