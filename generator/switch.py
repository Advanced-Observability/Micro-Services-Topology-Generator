"""
Represent a switch in MSTG.
"""

import utils
import network
import entities
import constants


class Switch(entities.Entity):
    """Represent a switch in the architecture."""

    def __init__(self, name, config):
        super().__init__(name, config, None)
        self.network: network.Network | None = None

    def __str__(self):
        return f"Switch: {self.name} - {super().__str__()}"

    def pretty(self) -> str:
        return f"Switch: {self.name}\n\t- {super().pretty()}"

    def get_vlan_id(self, name: str) -> int | None:
        """Get VLAN ID of entity `name`."""

        if "connections" not in self.config or self.config["connections"] is None:
            return None

        for conn in self.config["connections"]:
            if conn["path"] == name and "vlan" in conn:
                return conn["vlan"]

        return None

    def export_compose(self, file) -> None:
        """Export the switch in the given Docker Compose `file`."""

        commands = []
        commands.append(constants.OVS_ENABLE_SERVICE)
        commands.append(constants.OVS_ADD_BRIDGE.format(self.name))
        commands.append(constants.LINUX_SET_LINK_UP.format(self.name))
        commands.append(constants.LAUNCH_BACKGROUND_PROCESS)

        # write template
        mappings = {
            "name": self.name,
            "dockerImage": "mstg_switch",
            "commands": utils.combine_commands(commands, separator="&&")
        }
        file.write(constants.SWITCH_TEMPLATE.substitute(mappings))

    def export_k8s(self):
        raise RuntimeError("Switches cannot be used with Kubernetes")
