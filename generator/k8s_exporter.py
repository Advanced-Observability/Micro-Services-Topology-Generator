'''
Export the architecture to the configuration files
for Kubernetes.
'''

import entities, os, kubernetes
from exporter import *
from utils import *
from constants import *

class K8SExporter(Exporter):
    """Export architecture to Kubernetes configuration files."""

    def __init__(self, arch) -> None:
        super().__init__(arch)

    def export(self):
        """Export the architecture to Kubernetes configuration files."""

        if os.path.exists(K8S_EXPORT_FOLDER):
            # remove existing files to prevent port collisions
            files = os.listdir(K8S_EXPORT_FOLDER)
            files = [f for f in files if f.endswith(".yaml")]
            for f in files:
                os.remove(f"{K8S_EXPORT_FOLDER}/{f}")
        else:
            os.makedirs(K8S_EXPORT_FOLDER)

        self.generate_meshnet_config()

        self.export_routers()
        self.export_services()

        if is_using_jaeger():
            self.export_jaeger()

        if is_using_clt():
            self.export_clt()

    def export_routers(self) -> None:
        '''Export all the routers into Kubernetes configuration files.'''
        for entity in self.arch.entities:
            if isinstance(entity, entities.Router):
                print_info(f"Exporting router {entity.name} to Kubernetes format...")
                entity.export_k8s()

    def export_services(self) -> None:
        '''Export all the services into Kubernetes configuration files.'''
        for entity in self.arch.entities:
            if isinstance(entity, entities.Service):
                print_info(f"Exporting service {entity.name} to Kubernetes format...")
                entity.export_k8s()

    def export_jaeger(self) -> None:
        """Export Jaeger into Kubernetes pod and service."""
        print_info("Exporting Jaeger to Kubernetes format...")

        # pod
        f = open(f"{K8S_EXPORT_FOLDER}/jaeger_pod.yaml", "w")
        f.write(K8S_JAEGER_POD)
        f.close()

        # service
        mapping = dict(nodePort=kubernetes.Kubernetes.next_node_port())
        service = K8S_JAEGER_SERVICE.substitute(mapping)
        f = open(f"{K8S_EXPORT_FOLDER}/jaeger_service.yaml", "w")
        f.write(service)
        f.close()

    def export_clt(self):
        """Exporting IOAM collector into Kubernetes pod and service."""
        print_info("Exporting IOAM collector to Kubernetes format...")

        # pod
        f = open(f"{K8S_EXPORT_FOLDER}/ioam_collector_pod.yaml", "w")
        f.write(K8S_COLLECTOR_POD)
        f.close()

        # service
        mapping = dict(nodePort=kubernetes.Kubernetes.next_node_port())
        service = K8S_COLLECTOR_SERVICE.substitute(mapping)
        f = open(f"{K8S_EXPORT_FOLDER}/ioam_collector_service.yaml", "w")
        f.write(service)
        f.close()

    def generate_meshnet_config(self):
        """Generate meshnet configuration for the entire architecture."""

        for e in self.arch.entities:
            config = dict(pod_name=f"{e.name}-pod")
            meshnetConfig = TEMPLATE_MESHNET_CONFIG.substitute(config)

            # create config for each interface
            interfaces = []
            for net in e.attachedNetworks:
                network, id = self.arch.find_network(net['name'])
                peerName = network.begin if network.begin != e.name else network.end
                localIP = network.beginIP if network.begin == e.name else network.endIP
                peerIP = network.beginIP if network.begin == peerName else network.endIP
                localID = e.attachedNetworks.index(net)

                peer = self.arch.find_entity(peerName)
                if peer is None:
                    raise RuntimeError(f"Unable to get peer {peerName} in generate_meshnet_config")

                peerNetID = peer.get_network_pos(net['name'])
                if peerNetID is None:
                    raise RuntimeError(f"Unable to get id of network {network} for peer {peerName}")

                prefix = str(network.network.prefixlen)

                # localID + 1 and peerNetID + 1 because eth0 is always configured by default (kindnet, Calico, etc.) CNI
                config = dict(
                    id=id+1, peer_name=f"{peerName}-pod", local_eth=f"eth{localID+1}", peer_eth=f"eth{peerNetID+1}",
                    local_ip=f"{localIP}/{prefix}", peer_ip=f"{peerIP}/{prefix}"
                )
                interface = TEMPLATE_MESHNET_INTERFACE.substitute(config)
                interfaces.append(interface)

            # write meshnet config for entity into file
            f = open(f"{K8S_EXPORT_FOLDER}/{e.name}_meshnet.yaml", "w")
            f.write(meshnetConfig)
            for intf in interfaces:
                f.write(intf)
            f.close()
