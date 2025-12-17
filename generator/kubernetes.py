"""
Interactions with a Kubernetes cluster.
"""

import ipaddress
import subprocess

import utils
import constants


class Kubernetes:
    """Represent a Kubernetes cluster."""

    # node port min, max and next
    node_port_min = constants.K8S_DEFAULT_NODE_PORT_MIN
    node_port_max = constants.K8S_DEFAULT_NODE_PORT_MAX
    node_port_next = node_port_min

    def __init__(self) -> None:
        # number of nodes in cluster
        self.nb_nodes = Kubernetes.get_nb_nodes()
        # range of IP for services
        self.service_ip_range = Kubernetes.get_service_ip_range()
        # range of ip for pods
        self.pods_ip_range = Kubernetes.get_pod_ip_range()
        # ip subnet for services
        self.services_net = (
            ipaddress.IPv4Network(self.service_ip_range)
            if utils.topology_is_ipv4()
            else ipaddress.IPv6Network(self.service_ip_range)
        )
        # ip subnet for pods
        self.pods_net = (
            ipaddress.IPv4Network(self.pods_ip_range)
            if utils.topology_is_ipv4()
            else ipaddress.IPv6Network(self.pods_ip_range)
        )
        # iterator for IPs of pods
        self.pods_ips = iter(self.pods_net.hosts())

    def __str__(self) -> str:
        return self.string(" - ")

    def pretty(self) -> str:
        return "Kubernetes:\n\t- " + self.string("\n\t- ")

    def string(self, separator) -> str:
        """String representation of Kubernetes class."""
        return (
            f"Number of nodes: {self.nb_nodes}"
            f"{separator}Service IP range: {self.service_ip_range}"
            f"{separator}Pods IP range: {self.pods_ip_range}"
            f"{separator}Service network: {self.services_net}"
            f"{separator}Pod network: {self.pods_net}"
        )

    @staticmethod
    def next_node_port() -> int:
        """Return next node port usable."""
        if Kubernetes.node_port_next > Kubernetes.node_port_max:
            raise RuntimeError("Reached upper bound of node port")

        p = Kubernetes.node_port_next
        Kubernetes.node_port_next += 1
        return p

    @staticmethod
    def check_kubectl() -> bool:
        """Check if `kubectl` is available and its configuration."""
        check_exec = subprocess.run(
            constants.K8S_KUBECTL_CHECK_EXEC,
            shell=True,
            stdout=subprocess.PIPE,
            check=False,
        )
        if check_exec.returncode != 0:
            raise RuntimeError("kubectl is required")

        check_config = subprocess.run(
            constants.K8S_KUBECTL_GET_CONFIG,
            shell=True,
            stdout=subprocess.PIPE,
            check=False,
        )
        if check_config.returncode != 0:
            raise RuntimeError("Error when checking kubectl config")

        check_cluster = subprocess.run(
            constants.K8S_KUBECTL_GET_CLUSTER_INFO,
            shell=True,
            stdout=subprocess.PIPE,
            check=False,
        )
        if check_cluster.returncode != 0:
            raise RuntimeError("Error when checking the cluster")

        nb_nodes = Kubernetes.get_nb_nodes()
        if nb_nodes <= 0:
            raise RuntimeError("Requires at least 1 node in the cluster")

        return True

    @staticmethod
    def check_meshnet_cni() -> bool:
        """Check if Meshnet-CNI is properly running on the cluster."""
        check_meshnet = subprocess.run(
            constants.K8S_CHECK_MESHNET, shell=True, stdout=subprocess.PIPE, check=False
        )
        if check_meshnet.returncode != 0:
            raise RuntimeError("Unable to check status of Meshnet-CNI")

        decoded = check_meshnet.stdout.decode("utf-8").strip()
        lines = decoded.split("\n")
        if len(lines) < 2:  # line[0] is header of `kubectl`
            raise RuntimeError("Unexpected length for check_meshnet_cni")

        values = lines[1].split(" ")

        nb_nodes = Kubernetes.get_nb_nodes()
        for i in values:
            if int(i) != nb_nodes:
                raise RuntimeError(
                    "Meshnet CNI does not seem to run properly on the cluster"
                )

        return True

    @staticmethod
    def get_service_ip_range() -> str:
        """Return the range of IP addresses for services."""

        res = subprocess.run(
            constants.K8S_GET_SERVICE_IP_RANGE_CMD,
            shell=True,
            stdout=subprocess.PIPE,
            check=False,
        )
        if res.returncode != 0:
            raise RuntimeError("Unable to get the range of IP addresses for services")

        return res.stdout.decode("utf-8").strip()

    @staticmethod
    def get_pod_ip_range() -> str:
        """Return the range of IP addresses for pods."""

        res = subprocess.run(
            constants.K8S_GET_PODS_IP_RANGE_CMD,
            shell=True,
            stdout=subprocess.PIPE,
            check=False,
        )
        if res.returncode != 0:
            raise RuntimeError("Unable to get the range of IP addresses for pods")

        return res.stdout.decode("utf-8").strip()

    @staticmethod
    def get_nb_nodes() -> int:
        """Return the number of nodes in the Kubernetes clsuster."""

        check_nodes = subprocess.run(
            constants.K8S_KUBECTL_GET_NODES_COUNT,
            shell=True,
            stdout=subprocess.PIPE,
            check=False,
        )
        if check_nodes.returncode != 0:
            raise RuntimeError("Error when checking the nodes in the cluster")

        # -1 to remove header
        return int(check_nodes.stdout.decode("utf-8")) - 1
