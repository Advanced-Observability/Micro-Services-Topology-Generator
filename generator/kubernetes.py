'''
Represents and allows to interact with a Kubernetes cluster.
'''

import subprocess, ipaddress

import utils
from constants import *

class Kubernetes():
    """Represent a Kubernetes cluster."""

    # node port min, max and next
    nodePortMin = K8S_DEFAULT_NODE_PORT_MIN
    nodePortMax = K8S_DEFAULT_NODE_PORT_MAX
    nodePortNext = nodePortMin

    def __init__(self) -> None:
        # number of nodes in cluster
        self.nbNodes = Kubernetes.get_nb_nodes()
        # range of IP for services
        self.serviceIpRange = Kubernetes.get_service_ip_range()
        # range of ip for pods
        self.podsIpRange = Kubernetes.get_pod_ip_range()
        # ip subnet for services
        self.servicesNetwork = ipaddress.IPv4Network(self.serviceIpRange) if utils.topology_is_ipv4() else ipaddress.IPv6Network(self.serviceIpRange)
        # ip subnet for pods
        self.podsNetwork = ipaddress.IPv4Network(self.podsIpRange) if utils.topology_is_ipv4() else ipaddress.IPv6Network(self.podsIpRange)
        # iterator for IPs of pods
        self.podIPs = iter(self.podsNetwork.hosts())
    
    def __str__(self) -> str:
        return f"Number of nodes: {self.nbNodes} - Service IP range: {self.serviceIpRange} - Pods IP range: {self.podsIpRange} - Service network: {self.servicesNetwork} - Pod network: {self.podsNetwork}"

    def pretty(self) -> str:
        """Pretty print the Kubernetes class."""
        return f"Kubernetes:\n\tNumber of nodes: {self.nbNodes}\n\tService IP range: {self.serviceIpRange}\n\tPods IP range: {self.podsIpRange}\n\tService network: {self.servicesNetwork}\n\tPod network: {self.podsNetwork}"

    @staticmethod
    def next_node_port() -> int:
        """Return next node port usable."""
        if Kubernetes.nodePortNext > Kubernetes.nodePortMax:
            raise RuntimeError("Reached upper bound of node port")
        p = Kubernetes.nodePortNext
        Kubernetes.nodePortNext+=1

        return p

    @staticmethod
    def check_kubectl() -> bool:
        """Check if `kubectl` is available and its configuration."""
        checkExecutable = subprocess.run(K8S_KUBECTL_CHECK_EXEC, shell=True, stdout=subprocess.PIPE)
        if checkExecutable.returncode != 0:
            raise RuntimeError("kubectl is required")
        
        checkConfig = subprocess.run(K8S_KUBECTL_GET_CONFIG, shell=True, stdout=subprocess.PIPE)
        if checkConfig.returncode != 0:
            raise RuntimeError("Error when checking kubectl config")
        
        checkCluster = subprocess.run(K8S_KUBECTL_GET_CLUSTER_INFO, shell=True, stdout=subprocess.PIPE)
        if checkCluster.returncode != 0:
            raise RuntimeError("Error when checking the cluster")

        nbNodes = Kubernetes.get_nb_nodes()
        if nbNodes <= 0:
            raise RuntimeError("Requires at least 1 node in the cluster")
        
        return True
    
    @staticmethod
    def check_meshnet_cni() -> bool:
        """Check if Meshnet-CNI is properly running on the cluster."""
        checkMeshnet = subprocess.run(K8S_CHECK_MESHNET, shell=True, stdout=subprocess.PIPE)
        if checkMeshnet.returncode != 0:
            raise RuntimeError("Unable to check status of Meshnet-CNI")

        decoded = checkMeshnet.stdout.decode("utf-8")
        decoded = decoded.strip()
        lines = decoded.split('\n')
        if len(lines) < 2: # line[0] is header of `kubectl`
            raise RuntimeError("Unexpected length for check_meshnet_cni")

        values = lines[1].split(' ')
        
        nbNodes = Kubernetes.get_nb_nodes()
        for i in values:
            if int(i) != nbNodes:
                raise RuntimeError("Meshnet CNI does not seem to run properly on the cluster")

        return True

    @staticmethod
    def get_service_ip_range() -> str:
        """Return the range of IP addresses for services."""

        res = subprocess.run(K8S_GET_SERVICE_IP_RANGE_CMD, shell=True, stdout=subprocess.PIPE)
        if res.returncode != 0:
            raise RuntimeError("Unable to get the range of IP addresses for services")
        
        return res.stdout.decode('utf-8').strip()

    @staticmethod
    def get_pod_ip_range() -> str:
        """Return the range of IP addresses for pods."""

        res = subprocess.run(K8S_GET_PODS_IP_RANGE_CMD, shell=True, stdout=subprocess.PIPE)
        if res.returncode != 0:
            raise RuntimeError("Unable to get the range of IP addresses for pods")
        
        return res.stdout.decode('utf-8').strip()
    
    @staticmethod
    def get_nb_nodes() -> int:
        """Return the number of nodes in the Kubernetes clsuster."""
        
        checkNodes = subprocess.run(K8S_KUBECTL_GET_NODES_COUNT, shell=True, stdout=subprocess.PIPE)
        if checkNodes.returncode != 0:
            raise RuntimeError("Error when checking the nodes in the cluster")
        
        # -1 to remove header
        return int(checkNodes.stdout.decode('utf-8')) - 1
