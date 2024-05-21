# Generator of configuration files

## About

This tool allows to generate a docker compose file or the configuration files for Kubernetes based on an architecture defined in a `yml` file.

The generated topology will use: 
- [Jaeger](https://www.jaegertracing.io/)
- IOAM
- [IOAM collector for Jaeger](https://github.com/Advanced-Observability/ioam-collector-go-jaeger) and [Cross-Layer-Telemetry](https://github.com/Advanced-Observability/cross-layer-telemetry) (CLT) both created by [Justin Iurman](https://github.com/IurmanJ).

## Usage

First, you need to install the dependencies with:
```bash
pip3 install -r ../requirements.txt
```

You can generate the configurations files with the following command line:
```bash
python3 generator.py <options>
```

See below for details on `<options>`.

## Options

The following `<options>` are available.

### Mandatory

- `--ip {4,6}`: specify which version of IP you want being used in the architecture.

### Optional

- `--config <path>`: path towards the configuration file. If not specified, it will default to `./config.yml`.
- `--jaeger`: add OpenTelemetry and Jaeger in the generated topology.
- `--clt`: add Cross-Layer-Telemetry in the generated topology.
- `--kubernetes`: generate configuration files for Kubernetes instead of Docker Compose.
- `--https`: use HTTPS instead of HTTP.
- `--debug`: show debug information.

## Structure of configuration file

Read [`../CONFIGURATION.md`](../CONFIGURATION.md) for explanations on how to write a configuration file that can be used by the generator.

Check the folder [`configuration_examples`](../configuration_examples/) for examples of valid configuration files.

## Directory structure

The tool uses the following directories and files:
- `templates/` directory contains the templates used by the generator to create the generated files.
- `architecture.py` represents the architecture as defined in the configuration file.
- `compose_exporter` exports the internal representation into a `docker-compose.yml` file.
- `config_parser.py` is the parser for the configuration files.
- `constants.py` contains constant values used throughout the code.
- `entities.py` represents the entities in the interl representation.
- `exporter.py` is the abstract expoter of the internal representation.
- `generator.py` is the main file for the tool.
- `k8s_exporter.py` exports the internal representation into the configuration files for Kubernetes.
- `kubernetes.py` is the helper file for Kubernetes.
- `utils.py` are utilities for the generator.
