# Requirements

In order to use MSTG, you need the following:
- [Docker](https://docs.docker.com/get-docker/) (>= v28.0.0);
- [Docker compose](https://docs.docker.com/compose/) v2 for local deployment;
- A Kubernetes cluster and the [kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl) tool for multi-host deployment. See [K8S.md](./K8S.md) for more info;
- [Go](https://go.dev/) >= 1.21;
- [Python](https://www.python.org/) >= 3.10. Libraries can be installed with `pip3 install -r requirements.txt`;
- The following command-line tools: `grep`, `tr`, `awk`, and [GNU Make](https://www.gnu.org/software/make/);
- If you want to use CLT, you need a [Linux kernel 5.17](https://github.com/torvalds/linux/releases/tag/v5.17), which is [patched](https://github.com/Advanced-Observability/cross-layer-telemetry) for CLT.
