'''
Export the architecture to the configuration files
for Docker Compose.
'''

from entities import *
from architecture import Architecure
from exporter import *
from utils import *

class ComposeExporter(Exporter):
    """Export architecture to a Docker Compose configuration."""

    def __init__(self, arch : Architecure, filename : str) -> None:
        super().__init__(arch)
        self.filename = filename

    def write_docker_networks(self, file) -> None:
        '''Write all docker networks into the given `file` as in a docker compose file.'''
        for network in self.arch.dockerNetworks:
            network.export_compose(file)
            file.write("\n")

    def write_routers(self, file) -> None:
        '''Write all the routers into the given `file` as in a docker compose file.'''
        for entity in self.arch.entities:
            if isinstance(entity, Router):
                entity.export_compose(file)
                file.write("\n")

    def write_services(self, file) -> None:
        '''Write all the services into the given `file` as in a docker compose file.'''
        for entity in self.arch.entities:
            if isinstance(entity, Service):
                entity.export_compose(file)
                file.write("\n")

    def write_docker_compose(self) -> None:
        '''Write the given architecture in a file as a docker compose configuration.'''
        f = open(self.filename, 'w')
        
        # write all the docker networks
        if is_using_jaeger() or len(self.arch.dockerNetworks) > 0:
            f.write("networks:\n")
        
        if topology_is_ipv4() and is_using_jaeger():
            f.write(TELEMETRY_IPV4_NETWORK)
        elif is_using_jaeger():
            f.write(TELEMETRY_IPV6_NETWORK)
        
        self.write_docker_networks(f)

        # write all the services
        f.write("services:\n")
        if topology_is_ipv4() and is_using_jaeger():
            f.write(JAEGER_IPV4_SERVICE)
        elif is_using_jaeger():
            f.write(JAEGER_IPV6_SERVICE)
        
        if is_using_clt():
            f.write(IOAM_COLLECTOR_SERVICE)
        
        f.write("\n")
        self.write_routers(f)
        self.write_services(f)

        f.close()

    def export(self):
        self.write_docker_compose()
