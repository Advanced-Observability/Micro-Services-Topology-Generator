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
        super().__init__(arch)
        self.filename = filename

    def write_docker_networks(self, file) -> None:
        '''Write all docker networks into the given `file` as in a docker compose file.'''
        for network in self.arch.networks:
            network.export_compose(file)
            file.write("\n")

    def write_routers(self, file) -> None:
        '''Write all the routers into the given `file` as in a docker compose file.'''
        for entity in self.arch.entities:
            if isinstance(entity, router.Router):
                entity.export_compose(file)
                file.write("\n")

    def write_services(self, file) -> None:
        '''Write all the services into the given `file` as in a docker compose file.'''
        for entity in self.arch.entities:
            if isinstance(entity, services.Service):
                entity.export_compose(file)
                file.write("\n")

    def write_firewalls(self, file) -> None:
        '''Write all the firewalls into the given `file`.'''
        for entity in self.arch.entities:
            if isinstance(entity, firewall.Firewall):
                entity.export_compose(file)
                file.write("\n")

    def write_switches(self, file) -> None:
        '''Write all the switches into the given `file`.'''
        for entity in self.arch.entities:
            if isinstance(entity, switch.Switch):
                entity.export_compose(file)
                file.write("\n")

    def write_docker_compose(self) -> None:
        '''Write the given architecture in a file as a docker compose configuration.'''
        with open(self.filename, 'w', encoding="utf-8") as f:

            utils.print_info("Writing networks...")

            # write all the docker networks
            if utils.is_using_jaeger() or self.arch.count_l3_networks() > 0:
                f.write("networks:\n")

            if utils.topology_is_ipv4() and utils.is_using_jaeger():
                f.write(constants.TELEMETRY_IPV4_NETWORK)
            elif utils.is_using_jaeger():
                f.write(constants.TELEMETRY_IPV6_NETWORK)

            self.write_docker_networks(f)

            # write all the entities
            utils.print_info("Writing all the services...")
            f.write("services:\n")

            # write jaeger if used
            if utils.is_using_jaeger():
                f.write(constants.JAEGER_SERVICE)
                if utils.topology_is_ipv4():
                    f.write(constants.COMPOSE_JAEGER_IPV4)
                else:
                    f.write(constants.COMPOSE_JAEGER_IPV6)

            # write ioam collector if clt
            if utils.is_using_clt():
                f.write(constants.IOAM_COLLECTOR_SERVICE)

            # write other entities
            f.write("\n")
            utils.print_info("Writing routers...")
            self.write_routers(f)
            utils.print_info("Writing services...")
            self.write_services(f)
            utils.print_info("Writing firewalls...")
            self.write_firewalls(f)
            utils.print_info("Writing switches...")
            self.write_switches(f)

    def export(self):
        # empty commands file
        with open(constants.COMMANDS_FILE, "w", encoding="utf-8") as f:
            f.write("#!/bin/bash\n\n")

        self.write_docker_compose()
