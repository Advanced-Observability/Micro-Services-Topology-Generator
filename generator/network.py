"""
Represent a network inside MSTG.
"""

import ipaddress
from enum import Enum

import utils
import constants

class NetworkType(Enum):
    """Represent the different network types."""

    L3_NET = 1
    """Layer 3 IP network."""

    L2_NET = 2
    """Layer 2 Ethernet network."""

class NetworkInterface():
    """Represent a network interface."""

    def __init__(self, entity, ip: ipaddress.IPv4Address | ipaddress.IPv6Address, mac: str):
        """
        Create a network interface.

        :param entity: The entity (entity.Entity) using this interface.
        :param ip: The IP address of the interface.
        :param mac: The MAC address of the interface.
        """
        self.entity = entity
        self.ip = ip
        self.mac = mac

    def __str__(self):
        return f"EntityName = {self.entity.name} - ip = {self.ip} - mac = {self.mac}"

class Network:
    """Represent a network."""

    # used to generate the ip subnets
    # start at 1 because the first network will be used for telemetry.
    network_counter = 1

    def __init__(self, type: NetworkType):
        """
        Create a network with the given type.

        :param type: The type of network.
        """
        self.type = type
        self.name = ""
        self.network_id = Network.network_counter + 1
        Network.network_counter += 1
        self.network = self.create_network()
        self.hosts = iter(self.network.hosts())
        self.gateway = next(self.hosts) if utils.output_is_compose() else None
        self.subnet = self.network.with_prefixlen
        self.interfaces : list[NetworkInterface] = []

    def set_l3_network(self, begin, end) -> None:
        """
        Configure network as a layer 3 network.

        :param begin: The entity (entity.Entity) on one side of the network.
        :param end: The entity (entity.Entity) on the other side of the network.
        """
        self.name = Network.generate_l3_net_name(begin.name, end.name)

        macs = utils.convert_net_id_to_mac_addresses(self.network_id)

        self.interfaces.append(NetworkInterface(begin, next(self.hosts), macs[0]))
        self.interfaces.append(NetworkInterface(end, next(self.hosts), macs[1]))

    def set_l2_network(self, name: str) -> None:
        """Configure network as a L2 network."""
        self.name = Network.generate_l2_net_name(name)

    def add_network_interface(self, entity) -> None:
        """
        Add a network interface for the given entity on the network.

        :param entity: The entity (entity.Entity) using the interface.
        """
        self.interfaces.append(NetworkInterface(entity, next(self.hosts), ""))

    def get_network_interface(self, name: str) -> NetworkInterface | None:
        """
        Get the network interface used by the entity with the given `name`
        on this network.
        """
        return next((iface for iface in self.interfaces if iface.entity.name == name), None)

    def get_entity_ip(self, name: str):
        """Get IP of interface of entity with the given `name`."""
        return next((intf.ip for intf in self.interfaces if intf.entity.name == name), None)

    def get_entity_mac(self, name: str) -> str:
        """Get MAC address of interface of entity with the given `name`."""
        return next((intf.mac for intf in self.interfaces if intf.entity.name == name), "")

    def string(self, separator, pretty = False) -> str:
        """Convert network to string with the given `separator`."""
        interfaces = ""
        for intf in self.interfaces:
            if pretty:
                interfaces+=f"{separator}\t- {intf}"
            else:
                interfaces+=f"{intf} | "

        rep = f"Network: {self.name}"\
            f"{separator}- Type: {self.type}"\
            f"{separator}- ID: {self.network_id}"\
            f"{separator}- Subnet: {self.subnet}"\
            f"{separator}- Gateway: {self.gateway}"\
            f"{separator}- Interfaces: {interfaces}"

        return rep

    def __str__(self) -> str:
        return self.string(" ")

    def pretty(self) -> str:
        """Pretty print the network."""
        return self.string("\n\t", True)

    def create_network(self) -> ipaddress.IPv4Network | ipaddress.IPv6Network:
        """Create a network depending on the output settings."""
        if utils.output_is_k8s() and utils.topology_is_ipv4():
            return utils.convert_net_id_to_k8s_ipv4(self.network_id)
        if utils.output_is_k8s() and utils.topology_is_ipv6():
            return utils.convert_net_id_to_k8s_ipv6(self.network_id)
        if utils.output_is_compose() and utils.topology_is_ipv4():
            return utils.convert_net_id_to_ip4_net(self.network_id)
        if utils.output_is_compose() and utils.topology_is_ipv6():
            return utils.convert_net_id_to_ip6_net(self.network_id)

        raise RuntimeError("Unexpected network configuration")

    def export_compose(self, file) -> None:
        """Export the Docker network in the given Docker Compose `file`."""

        # do not export L2 network because a docker network == l3 network
        if self.type == NetworkType.L2_NET:
            return

        mappings = {
            "name": self.name,
            "subnet": self.subnet,
            "gateway": self.gateway
        }
        if utils.topology_is_ipv4():
            file.write(constants.NETWORK_IPV4_TEMPLATE.substitute(mappings))
        else:
            file.write(constants.NETWORK_IPV6_TEMPLATE.substitute(mappings))

    @staticmethod
    def generate_l3_net_name(begin: str, end: str) -> str:
        """Generate name for network shared by `begin` and `end`."""
        return constants.NETWORK_NAME.format(begin, end)

    @staticmethod
    def generate_l2_net_name(name: str) -> str:
        """Generate name for network used by a switch named `name`."""
        return constants.SWITCH_NET_NAME.format(name)
