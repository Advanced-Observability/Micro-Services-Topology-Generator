"""
Represent a network inside MSTG.
"""

import ipaddress
from enum import Enum

import utils
import switch
import constants


class NetworkType(Enum):
    """Represent the different network types."""

    L2_NET = 2
    """Layer 2 Ethernet network."""

    L3_NET = 3
    """Layer 3 IP network."""


class NetworkInterface:
    """Represent a network interface."""

    def __init__(
        self,
        entity,
        next_hop,
        ip: ipaddress.IPv4Address | ipaddress.IPv6Address | None,
        mac: str,
        vlan: int | None,
    ):
        """
        Create a network interface.

        :param entity: The entity (entity.Entity) using this interface.
        :param next_hop: The entity (entity.Entity) of the next hop.
        :param ip: The IP address of the interface.
        :param mac: The MAC address of the interface.
        """
        self.entity = entity
        self.next_hop = next_hop
        self.ip = ip
        self.mac = mac
        self.vlan = vlan

    def __str__(self):
        return f"EntityName = {self.entity.name} - next hop = {self.next_hop.name if self.next_hop is not None else 'None'} - ip = {self.ip} - mac = {self.mac} - vlan = {self.vlan}"


class Network:
    """Represent a network."""

    # used to generate the ip subnets
    # start at 2 because the first network will be used for telemetry.
    network_counter = 2

    def __init__(self, type: NetworkType):
        """
        Create a network with the given type.

        :param type: The type of network.
        """
        self.type = type
        self.name = ""
        self.network_id = Network.network_counter
        Network.network_counter += 1
        self.network = self.create_network()
        self.hosts = iter(self.network.hosts())
        self.gateway = next(self.hosts) if utils.output_is_compose() else None
        self.subnet = self.network.with_prefixlen
        self.interfaces: list[NetworkInterface] = []

    def set_l3_network(self, begin, end) -> None:
        """
        Configure network as a layer 3 network.

        :param begin: The entity (entity.Entity) on one side of the network.
        :param end: The entity (entity.Entity) on the other side of the network.
        """
        self.name = Network.generate_l3_net_name(begin.name, end.name)

        macs = utils.convert_net_id_to_mac_addresses(self.network_id)

        self.interfaces.append(
            NetworkInterface(begin, end, next(self.hosts), macs[0], None)
        )
        self.interfaces.append(
            NetworkInterface(end, None, next(self.hosts), macs[1], None)
        )

    def set_l2_network(self, name: str) -> None:
        """Configure network as a L2 network."""
        self.name = Network.generate_l2_net_name(name)

    def add_network_interface(
        self, entity, next_hop, ethernet=False, vlan=None
    ) -> None:
        """
        Add a network interface for the given entity on the network.

        :param entity: The entity (entity.Entity) using the interface.
        :param next_hop: The entity (entity.Entity) of the next hop.
        :param ethernet: Interface without IP address.
        """
        if not ethernet:
            self.interfaces.append(
                NetworkInterface(entity, next_hop, next(self.hosts), "", vlan)
            )
        else:
            self.interfaces.append(NetworkInterface(entity, next_hop, None, "", vlan))

    def get_shared_interface(self, begin: str, end: str) -> NetworkInterface | None:
        """
        Return the network interface to reach `end` from ` begin` on this network.
        """

        return next(
            (
                iface
                for iface in self.interfaces
                if iface.entity.name == begin
                and iface.next_hop is not None
                and iface.next_hop.name == end
            ),
            None,
        )

    def check_shared_network(self, begin: str, end: str) -> bool:
        """
        Check whether the network has interfaces for both `begin` and `end`.
        """

        found_begin = False
        found_end = False

        for iface in self.interfaces:
            if iface.entity.name == begin:
                found_begin = True
            if iface.entity.name == end:
                found_end = True

        return found_begin and found_end

    def get_entity_ip(self, name: str):
        """Get IP of interface of entity with the given `name`."""
        return next(
            (intf.ip for intf in self.interfaces if intf.entity.name == name), None
        )

    def get_entity_mac(self, name: str) -> str:
        """Get MAC address of interface of entity with the given `name`."""
        return next(
            (intf.mac for intf in self.interfaces if intf.entity.name == name), ""
        )

    def get_entity_vlan(self, name: str) -> int | None:
        """Get VLAN of interface of entity `name`."""
        return next(
            (intf.vlan for intf in self.interfaces if intf.entity.name == name), None
        )

    def get_other_host(self, name: str):
        """
        If the network is L3, get the other host on the network.
        L3 network will always only have 2 interfaces.
        """

        if self.type != NetworkType.L3_NET:
            raise RuntimeError("This method can be used only with L3 network")

        if len(self.interfaces) != 2:
            raise RuntimeError("Unexpected network status")

        for iface in self.interfaces:
            if iface.entity.name != name:
                return iface

        return None

    def string(self, separator, pretty=False) -> str:
        """Convert network to string with the given `separator`."""
        if pretty:
            interfaces = f"{separator}\t- " + f"{separator}\t- ".join(
                f"{intf}" for intf in self.interfaces
            )
        else:
            interfaces = " | ".join(f"{intf}" for intf in self.interfaces)

        rep = (
            f"Network: {self.name}"
            f"{separator}- Type: {self.type}"
            f"{separator}- ID: {self.network_id}"
            f"{separator}- Subnet: {self.subnet}"
            f"{separator}- Gateway: {self.gateway}"
            f"{separator}- Interfaces: {interfaces}"
        )

        return rep

    def __str__(self) -> str:
        return self.string(" ")

    def pretty(self) -> str:
        """Pretty string of the network."""
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

        if self.type == NetworkType.L3_NET:
            self.export_compose_l3(file)
            return

        # do not export L2 network because a docker network == l3 network
        # only need to generate the commands
        if self.type == NetworkType.L2_NET:
            self.export_compose_l2()
            return

    def export_compose_l2(self) -> None:
        """Generate the commands to create the L2 network."""

        commands = []

        for iface in self.interfaces:
            if iface.entity is None or iface.next_hop is None:
                continue

            local = iface.entity.name
            local_switch = isinstance(iface.entity, switch.Switch)
            remote = iface.next_hop.name
            remote_switch = isinstance(iface.next_hop, switch.Switch)

            local_iface_name = f"{local}_{remote}"
            remote_iface_name = f"{remote}_{local}"

            commands.append(
                constants.LINUX_CREATE_VETH.format(local_iface_name, remote_iface_name)
            )

            # move one end into container and set up
            commands.append(
                f"pid=$({constants.DOCKER_GET_PID.substitute({'name': local})})"
            )
            commands.append(
                constants.LINUX_MOVE_VETH_TO_NS.format(local_iface_name, "$pid")
            )
            commands.append(
                utils.generate_command(
                    constants.LINUX_SET_LINK_UP.format(local_iface_name), local, False
                )
            )
            # set ip in container if any
            if iface.ip is not None:
                ip = f"{iface.ip}/{self.network.prefixlen}"
                commands.append(
                    utils.generate_command(
                        constants.LINUX_SET_IP_ADDRESS.format(ip, local_iface_name),
                        local,
                        False,
                    )
                )
            # add port in ovs if it's a switch
            if local_switch and self.get_entity_vlan(remote) is not None:
                commands.append(
                    utils.generate_command(
                        constants.OVS_ADD_PORT_VLAN.format(
                            local, local_iface_name, self.get_entity_vlan(remote)
                        ),
                        local,
                        False,
                    )
                )
            elif local_switch:
                commands.append(
                    utils.generate_command(
                        constants.OVS_ADD_PORT.format(local, local_iface_name),
                        local,
                        False,
                    )
                )

            # move other end into other container and set up
            commands.append(
                f"pid=$({constants.DOCKER_GET_PID.substitute({'name': remote})})"
            )
            commands.append(
                constants.LINUX_MOVE_VETH_TO_NS.format(remote_iface_name, "$pid")
            )
            commands.append(
                utils.generate_command(
                    constants.LINUX_SET_LINK_UP.format(remote_iface_name), remote, False
                )
            )
            # set ip in other container if any
            remote_ip = self.get_entity_ip(remote)
            if remote_ip is not None:
                ip = f"{remote_ip}/{self.network.prefixlen}"
                commands.append(
                    utils.generate_command(
                        constants.LINUX_SET_IP_ADDRESS.format(ip, remote_iface_name),
                        remote,
                        False,
                    )
                )
            # add port in ovs if it's a switch
            if remote_switch and self.get_entity_vlan(local) is not None:
                commands.append(
                    utils.generate_command(
                        constants.OVS_ADD_PORT_VLAN.format(
                            remote, remote_iface_name, self.get_entity_vlan(local)
                        ),
                        remote,
                        False,
                    )
                )
            elif remote_switch:
                commands.append(
                    utils.generate_command(
                        constants.OVS_ADD_PORT.format(remote, remote_iface_name),
                        remote,
                        False,
                    )
                )

            # TODO ovs add vlan

        # write every command to file
        with open(constants.COMMANDS_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n# configuring {self.name}\n\n")
            for cmd in commands:
                f.write(f"{cmd}\n")

    def export_compose_l3(self, file) -> None:
        """Export the L3 network in the given Docker compose `file`."""

        mappings = {"name": self.name, "subnet": self.subnet, "gateway": self.gateway}
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
