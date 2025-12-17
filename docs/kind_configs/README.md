# [Kind](https://kind.sigs.k8s.io/)

Kubernetes distribution that allows to run Kubernetes in Docker (Kubernetes-IN-Docker).

Please refer to the [quick start guide](https://kind.sigs.k8s.io/docs/user/quick-start/#installation) for the installation procedure.

## Files

The following files contain the configurations to deploy a Kubernetes cluster using Kind:
- [cluster-ipv4.yaml](./cluster-ipv4.yaml): Cluster with 1 control node and 2 worker nodes with IPv4;
- [cluster-ipv6.yaml](./cluster-ipv6.yaml): Cluster with 1 control node and 2 worker nodes with IPv6.

You can use one of the files to create your cluster with the following command:
```shell
kind create cluster --name meshnet --config <cluster-ipv4.yaml|cluster-ipv6.yaml>
```

You might have to update your path to have access to kind after the installation.

## Networking

It uses [Kindnet](https://github.com/aojea/kindnet), which is a simple CNI plugin for networking.

[Website](https://www.tkng.io/cni/kindnet/) with explanations about the inner-workings.
