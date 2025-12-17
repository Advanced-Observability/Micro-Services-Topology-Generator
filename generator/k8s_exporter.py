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
import architecture


class K8SExporter(exporter.Exporter):
    """Export architecture to Kubernetes configuration files."""

    def __init__(self, arch: architecture.Architecure) -> None:
        """
        Export the architecture to Kubernetes configuration file.

        :param arch: Architecture to export.
        """
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
                os.remove(os.path.join(constants.K8S_EXPORT_FOLDER, f))
        else:
            os.makedirs(constants.K8S_EXPORT_FOLDER)

        utils.print_info("Generating configuration for Meshnet...")
        self.generate_meshnet_config()

        utils.print_info("Exporting routers...")
        self.export_entities_type(router.Router)
        utils.print_info("Exporting services...")
        self.export_entities_type(services.Service)
        utils.print_info("Exporting firewalls...")
        self.export_entities_type(firewall.Firewall)

        if utils.is_using_jaeger():
            utils.print_info("Exporting Jaeger...")
            self.export_jaeger()

        if utils.is_using_clt():
            utils.print_info("Exporting IOAM collector...")
            self.export_ioam_collector()

    def export_entities_type(self, type) -> None:
        """Export entities with the given `type`."""
        for entity in self.arch.entities:
            if isinstance(entity, type):
                utils.print_info(f"Exporting entity {entity.name}...")
                entity.export_k8s()

    def export_jaeger(self) -> None:
        """Export Jaeger into Kubernetes pod and service."""
        utils.print_info("Exporting Jaeger to Kubernetes format...")

        # pod
        path = os.path.join(constants.K8S_EXPORT_FOLDER, "jaeger_pod.yaml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(constants.K8S_JAEGER_POD)

        # service
        mapping = {"nodePort": kubernetes.Kubernetes.next_node_port()}
        service = constants.K8S_JAEGER_SERVICE.substitute(mapping)
        path = os.path.join(constants.K8S_EXPORT_FOLDER, "jaeger_service.yaml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(service)

    def export_ioam_collector(self):
        """Exporting IOAM collector into Kubernetes pod and service."""
        utils.print_info("Exporting IOAM collector to Kubernetes format...")

        # pod
        path = os.path.join(constants.K8S_EXPORT_FOLDER, "ioam_collector_pod.yaml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(constants.K8S_COLLECTOR_POD)

        # service
        mapping = {"nodePort": kubernetes.Kubernetes.next_node_port()}
        service = constants.K8S_COLLECTOR_SERVICE.substitute(mapping)
        path = os.path.join(constants.K8S_EXPORT_FOLDER, "ioam_collector_service.yaml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(service)

    def generate_meshnet_config(self):
        """Generate meshnet configuration for the entire architecture."""

        for e in self.arch.entities:
            # create config for each interface
            interfaces = []
            for net in e.attached_networks:
                local_ip = net.get_entity_ip(e.name)
                peer_name = net.get_other_host(e.name).entity.name
                peer_ip = net.get_entity_ip(peer_name)
                local_id = e.attached_networks.index(net)

                peer = self.arch.find_entity(peer_name)
                if peer is None:
                    raise RuntimeError(f"Unable to get peer {peer_name}")

                peer_net_id = peer.get_network_pos(net.name)
                if peer_net_id is None:
                    raise RuntimeError(f"Unable to get network ID for peer")

                prefix = str(net.network.prefixlen)

                # local_id + 1 and peer_net_id + 1 because eth0 is always configured by default
                # (kindnet, Calico, etc.) CNI
                config = {
                    "id": net.network_id + 1,
                    "peer_name": f"{peer_name}-pod",
                    "local_eth": f"eth{local_id + 1}",
                    "local_ip": f"{local_ip}/{prefix}",
                    "peer_eth": f"eth{peer_net_id + 1}",
                    "peer_ip": f"{peer_ip}/{prefix}"
                }
                interfaces.append(constants.TEMPLATE_MESHNET_INTERFACE.substitute(config))

            # write meshnet config for entity into file
            path = os.path.join(constants.K8S_EXPORT_FOLDER, f"{e.name}_meshnet.yaml")
            with open(path, "w", encoding="utf-8") as f:
                f.write(constants.TEMPLATE_MESHNET_CONFIG.substitute({"pod_name": f'{e.name}-pod'}))
                for iface in interfaces:
                    f.write(iface)
