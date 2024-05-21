# Micro-Services Topology Generator (MSTG)

This tool automates the generation of containerized microservices topologies.

From a single user-provided configuration `yml` file, it generates the intermediary files for [Docker Compose](https://docs.docker.com/compose/) or [Kubernetes](https://kubernetes.io/).

The microservices, all instances of the same program, will sequentially send requests to the services they are connected to before responding to their own requests.

Routers can be added between the services to simulate a real network environment.

See [`generator/README.md`](./generator/README.md) for details on the generator of configuration files.

### 🌐 Architecture of MSTG:

![architecture](./MSTG.png)

## 🚀 Getting Started

### Specify the architecture

When invoking `make` commands, the architecture configuration file can by specified as follows:
```bash
CONFIG=<file> make
```

Alternatively, if no argument are given, `make` will look for a file named `config.yml`.

See [`CONFIGURATION.md`](/CONFIGURATION.md) for how to write the architecture file and [`configuration_examples`](./configuration_examples) for examples.

### Build the Docker images

Then, you need to build the Docker images with the following command:
```bash
make images
```

The Docker images for the CLT version can be build with:
```bash
make images_clt
```

### Generate the topology

You have 2 possibilities when it comes to the output of the generator:

- You can generate a **Docker Compose** file which can be used to deploy the topology on a *single machine*.
- You can generate the configuration files for **Kubernetes** which can be used to deploy the topology on *one or more machines*.

#### Docker Compose

Now, you can generate the architecture with IPv4 or IPv6 with the following commands:
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

##### Start the architecture

You can start the architecture with:
```bash
make start
```

##### Make requests to the services

You can make requests to the services using the following commands and replacing `<port>` with the port of the service to which you want to send a request:
```bash
curl "http://127.0.0.1:<port>/" # IPv4 + HTTP
curl -6 "http://[::1]:<port>/" # IPV6 + HTTP
curl --insecure "https://127.0.0.1:<port>/" # IPv4 + HTTPS
curl --insecure -6 "https://[::1]:<port>/" # IPv6 + HTTPS
```

Choose the command based on which version of IP and HTTP you chose to generate the architecture.

When using HTTPS, you need to add `--insecure` because the services use a self-signed certificate.

##### Check the traces

If you decided to enable Jaeger, you can see the traces by opening the URL [http://localhost:16686/](http://localhost:16686/) in your Web browser of choice.

##### Stop the architecture

You can stop the architecture with:
```bash
make stop
```

#### Kubernetes

See [K8S.md](./K8S.md) for explanations regarding the deployment to Kubernetes.

## 🔍 Cross-Layer Telemetry (CLT)

This tool can be used to demonstrate the capabilities of [Cross-Layer-Telemetry](https://github.com/Advanced-Observability/cross-layer-telemetry).

Telemetry data will be generated with [OpenTelemetry](https://opentelemetry.io/) and displayed with [Jaeger](https://www.jaegertracing.io/).
Furthermore, telemetry data related to the routers will be generated with [IOAM](https://datatracker.ietf.org/doc/rfc9197/) and gathered with OpenTelemetry data in Jaeger by using the [IOAM collector for Jaeger](https://github.com/Advanced-Observability/ioam-collector-go-jaeger).

## 📋 Requirements

In order to use these tools, you need the following:
- [Docker](https://docs.docker.com/get-docker/).
- [Docker compose](https://docs.docker.com/compose/) v2 for local deployment.
- A Kubernetes cluster and the [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) tool for multi-host deployment. See [K8S.md](./K8S.md) for more info.
- [Go](https://go.dev/) >= 1.21
- [Python](https://www.python.org/) >= 3.10.
    - Libraries can be installed with `pip3 install -r requirements.txt`
- The following command-line tools: `grep`, `tr`, `awk`, and [GNU Make](https://www.gnu.org/software/make/).
- If you want to use CLT, you need a [kernel 5.17](https://github.com/torvalds/linux/releases/tag/v5.17) which is [patched](https://github.com/Advanced-Observability/cross-layer-telemetry) for CLT.
