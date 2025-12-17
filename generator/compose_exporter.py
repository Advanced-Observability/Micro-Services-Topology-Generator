"""
Export the architecture to the configuration file for Docker Compose.
"""

import utils
import router
import switch
import exporter
import services
import firewall
import constants
import architecture


class ComposeExporter(exporter.Exporter):
    """Export architecture to a Docker Compose configuration."""

    def __init__(self, arch: architecture.Architecure, filename: str) -> None:
        """
        Export the architecture in the given file.

        :param arch: Architecture to export.
        :param filename: Filename in which to write the architecture.
        """
        super().__init__(arch)
        self.filename = filename

    def write_entity_type(self, file, type) -> None:
        '''Write entities with the given `type` inside the given docker compose `file`.'''

        for entity in self.arch.entities:
            if isinstance(entity, type):
                entity.export_compose(file)
                file.write("\n")

    def write_networks(self, file) -> None:
        '''Write all the networks.'''
        utils.print_info("Writing networks...")
        if utils.is_using_jaeger() or self.arch.count_l3_networks() > 0:
            file.write("networks:\n")

        if utils.topology_is_ipv4() and utils.is_using_jaeger():
            file.write(constants.TELEMETRY_IPV4_NETWORK)
        elif utils.is_using_jaeger():
            file.write(constants.TELEMETRY_IPV6_NETWORK)

        for network in self.arch.networks:
            network.export_compose(file)
            file.write("\n")

    def write_containers(self, file) -> None:
        '''Write the containers.'''
        utils.print_info("Writing all the containers...")
        file.write("services:\n")

        # write jaeger if used
        if utils.is_using_jaeger():
            file.write(constants.JAEGER_SERVICE)
            if utils.topology_is_ipv4():
                file.write(constants.COMPOSE_JAEGER_IPV4)
            else:
                file.write(constants.COMPOSE_JAEGER_IPV6)

        # write ioam collector if clt
        if utils.is_using_clt():
            file.write(constants.IOAM_COLLECTOR_SERVICE)

        # write other entities
        file.write("\n")
        utils.print_info("Writing switches...")
        self.write_entity_type(file, switch.Switch)
        utils.print_info("Writing routers...")
        self.write_entity_type(file, router.Router)
        utils.print_info("Writing firewalls...")
        self.write_entity_type(file, firewall.Firewall)
        utils.print_info("Writing services...")
        self.write_entity_type(file, services.Service)

    def export(self):
        # empty commands file
        with open(constants.COMMANDS_FILE, "w", encoding="utf-8") as f:
            f.write("#!/bin/bash\n\n")

        with open(self.filename, 'w', encoding="utf-8") as f:
            # need to export networks first because will add interfaces inside containers
            # if interfaces are not added first, ip route command will fail in other entities
            self.write_networks(f)
            self.write_containers(f)
