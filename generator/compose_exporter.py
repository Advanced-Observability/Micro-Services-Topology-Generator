'''
Export the architecture to the configuration files
for Docker Compose.
'''

import entities
import architecture
import exporter
import utils
import constants


class ComposeExporter(exporter.Exporter):
    """Export architecture to a Docker Compose configuration."""

    def __init__(self, arch: architecture.Architecure, filename: str) -> None:
        super().__init__(arch)
        self.filename = filename

    def write_docker_networks(self, file) -> None:
        '''Write all docker networks into the given `file` as in a docker compose file.'''
        for network in self.arch.docker_networks:
            network.export_compose(file)
            file.write("\n")

    def write_routers(self, file) -> None:
        '''Write all the routers into the given `file` as in a docker compose file.'''
        for entity in self.arch.entities:
            if isinstance(entity, entities.Router):
                entity.export_compose(file)
                file.write("\n")

    def write_services(self, file) -> None:
        '''Write all the services into the given `file` as in a docker compose file.'''
        for entity in self.arch.entities:
            if isinstance(entity, entities.Service):
                entity.export_compose(file)
                file.write("\n")

    def write_docker_compose(self) -> None:
        '''Write the given architecture in a file as a docker compose configuration.'''
        with open(self.filename, 'w', encoding="utf-8") as f:

            # write all the docker networks
            if utils.is_using_jaeger() or len(self.arch.docker_networks) > 0:
                f.write("networks:\n")

            if utils.topology_is_ipv4() and utils.is_using_jaeger():
                f.write(constants.TELEMETRY_IPV4_NETWORK)
            elif utils.is_using_jaeger():
                f.write(constants.TELEMETRY_IPV6_NETWORK)

            self.write_docker_networks(f)

            # write all the services
            f.write("services:\n")
            if utils.topology_is_ipv4() and utils.is_using_jaeger():
                f.write(constants.JAEGER_IPV4_SERVICE)
            elif utils.is_using_jaeger():
                f.write(constants.JAEGER_IPV6_SERVICE)

            if utils.is_using_clt():
                f.write(constants.IOAM_COLLECTOR_SERVICE)

            f.write("\n")
            self.write_routers(f)
            self.write_services(f)

    def export(self):
        self.write_docker_compose()
