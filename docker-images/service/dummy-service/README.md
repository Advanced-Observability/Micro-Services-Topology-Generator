# Service

This folder contains the code for a service in the generated architecture.

It will contact other services in sequence as specified in the [`config.yaml`](./../config.yaml) file before answering to a request.
See [`CONFIGURATION.md`](./../CONFIGURATION.md) for how to specify the architecture in a `yml` file.

## Compilation

You can compile the service with the following command:
```bash
go mod download
CGO_ENABLED=0 go build -tags netgo -o service
```

## Environment variables

The service relies on the following environment variables to configure itself:
- `SERVICE_NAME`: name of the service in order to match itself with the configuration
- `IP_VERSION`: whether to use IPv4 or IPv6
- `HTTP_VERSION`: whether to use HTTP or HTTPS
- `JAEGER_ENABLE`: enable Jaeger or not
- `JAEGER_HOSTNAME`: hostname to reach the instance of Jaeger.
- `CLT_ENABLE`: enable CLT or not
- `IOAM_COLLECTOR`: hostname of the IOAM collector.
- `CERT_FILE` and `KEY_FILE`: path towards the certificate and the key when using HTTPS.

## Files

The code of the service is split across the following files:
- [main.go](./main.go)
- [server_side.go](./server_side.go): code for listening to incoming HTTP(S) requests
- [client_side.go](./client_side.go): code for sending HTTP(s) requests
- [types.go](./types.go): data types used throughout the code
- [otel.go](./otel.go): code to setup the OpenTelemetry SDK.
- [clt_agent.go](./clt_agent.go): code to interact with netlink when using CLT.
- [utils.go](./utils.go): utilities
