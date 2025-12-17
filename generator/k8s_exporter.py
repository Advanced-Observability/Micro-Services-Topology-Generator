"""
Export the architecture to the configuration files
for Kubernetes.
"""

import os

import utils
import router
import services
import exporter
import firewall
import constants
import kubernetes


class K8SExporter(exporter.Exporter):
    """Export architecture to Kubernetes configuration files."""

    def __init__(self, arch) -> None:
        super().__init__(arch)

    def export(self):
        """Export the architecture to Kubernetes configuration files."""
        # empty commands file
        with open(constants.COMMANDS_FILE, "w", encoding="utf-8") as f:
            f.write("#!/bin/bash\n\n")

        # remove existing files to prevent port collisions
        if os.path.exists(constants.K8S_EXPORT_FOLDER):
            files = os.listdir(constants.K8S_EXPORT_FOLDER)
            files = [f for f in files if f.endswith(".yaml")]
            for f in files:
                os.remove(f"{constants.K8S_EXPORT_FOLDER}/{f}")
        else:
            os.makedirs(constants.K8S_EXPORT_FOLDER)

        self.generate_meshnet_config()

        self.export_routers()
        self.export_services()
        self.export_firewalls()

        if utils.is_using_jaeger():
            self.export_jaeger()

        if utils.is_using_clt():
            self.export_clt()

    def export_routers(self) -> None:
        '''Export all the routers into Kubernetes configuration files.'''
        for entity in self.arch.entities:
            if isinstance(entity, router.Router):
                utils.print_info(f"Exporting router {entity.name} to Kubernetes format...")
                entity.export_k8s()

    def export_services(self) -> None:
        '''Export all the services into Kubernetes configuration files.'''
        for entity in self.arch.entities:
            if isinstance(entity, services.Service):
                utils.print_info(f"Exporting service {entity.name} to Kubernetes format...")
                entity.export_k8s()

    def export_firewalls(self) -> None:
        """Export all the firewalls into Kubernetes configuratio files."""
        for entity in self.arch.entities:
            if isinstance(entity, firewall.Firewall):
                utils.print_info(f"Exporting firewall {entity.name} to Kubernetes format")
                entity.export_k8s()

    def export_jaeger(self) -> None:
        """Export Jaeger into Kubernetes pod and service."""
        utils.print_info("Exporting Jaeger to Kubernetes format...")

        # pod
        with open(f"{constants.K8S_EXPORT_FOLDER}/jaeger_pod.yaml", "w", encoding="utf-8") as f:
            f.write(constants.K8S_JAEGER_POD)

        # service
        mapping = {"nodePort": kubernetes.Kubernetes.next_node_port()}
        service = constants.K8S_JAEGER_SERVICE.substitute(mapping)
        with open(f"{constants.K8S_EXPORT_FOLDER}/jaeger_service.yaml", "w", encoding="utf-8") as f:
            f.write(service)

    def export_clt(self):
        """Exporting IOAM collector into Kubernetes pod and service."""
        utils.print_info("Exporting IOAM collector to Kubernetes format...")

        # pod
        with open(f"{constants.K8S_EXPORT_FOLDER}/ioam_collector_pod.yaml", "w", encoding="utf-8")\
                as f:
            f.write(constants.K8S_COLLECTOR_POD)

        # service
        mapping = {"nodePort": kubernetes.Kubernetes.next_node_port()}
        service = constants.K8S_COLLECTOR_SERVICE.substitute(mapping)
        with open(f"{constants.K8S_EXPORT_FOLDER}/ioam_collector_service.yaml", "w",
                  encoding="utf-8") as f:
            f.write(service)

    def generate_meshnet_config(self):
        """Generate meshnet configuration for the entire architecture."""

        for e in self.arch.entities:
            config = {"pod_name": f'{e.name}-pod'}
            meshnet_config = constants.TEMPLATE_MESHNET_CONFIG.substitute(config)

            # create config for each interface
            interfaces = []
            for net in e.attached_networks:
                network, net_id = self.arch.find_network(net['name'])
                peer_name = network.begin if network.begin != e.name else network.end
                local_ip = network.begin_ip if network.begin == e.name else network.end_ip
                peer_ip = network.begin_ip if network.begin == peer_name else network.end_ip
                local_id = e.attached_networks.index(net)

                peer = self.arch.find_entity(peer_name)
                if peer is None:
                    raise RuntimeError(f"Unable to get peer {peer_name} in generate_meshnet_config")

                peer_net_id = peer.get_network_pos(net['name'])
                if peer_net_id is None:
                    raise RuntimeError(f"Unable to get id of network {network} for peer "
                                       f"{peer_name}")

                prefix = str(network.network.prefixlen)

                # local_id + 1 and peer_net_id + 1 because eth0 is always configured by default
                # (kindnet, Calico, etc.) CNI
                config = {
                    "id": net_id + 1,
                    "peer_name": f"{peer_name}-pod",
                    "local_eth": f"eth{local_id + 1}",
                    "local_ip": f"{local_ip}/{prefix}",
                    "peer_eth": f"eth{peer_net_id + 1}",
                    "peer_ip": f"{peer_ip}/{prefix}"
                }
                interface = constants.TEMPLATE_MESHNET_INTERFACE.substitute(config)
                interfaces.append(interface)

            # write meshnet config for entity into file
            with open(f"{constants.K8S_EXPORT_FOLDER}/{e.name}_meshnet.yaml", "w",
                      encoding="utf-8") as f:
                f.write(meshnet_config)
                for intf in interfaces:
                    f.write(intf)
