# Service

These Dockerfiles represent a microservice in the generated architecture.

2 versions are available:
- [Dockerfile](./Dockerfile) for the service with CLT
- [Dockerfile_clt](./Dockerfile_clt) for the service without CLT

## Reduce size for service with CLT

By using the command `docker build -t service_clt -f Dockerfile_clt .`, the image will be approximately 105MB.

The size of the image can be reduced down to approximately 95MB by using [Docker Squash](https://github.com/goldmann/docker-squash).

If you have Python >= 3.6, you can do the following:
```bash
pip3 install docker-squash # you might need to update your PATH, check the logs
docker build -t service_clt -f Dockerfile_clt .
docker-squash service_clt -t service_clt
```

## [IOAM agent](./ioam-agent.cpp)

The IOAM agent is responsible for intercepting the IOAM data contained in the IPv6 extension headers.
Then, it sends them to the [ioam-collector-go-jaeger](https://github.com/Advanced-Observability/ioam-collector-go-jaeger) using gRPC.

## HTTPS

The self-signed certificate [server.crt](./server.crt) and key [server.key](./server.key) are used for HTTPS communication.
