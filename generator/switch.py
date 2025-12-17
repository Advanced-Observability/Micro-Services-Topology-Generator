"""
Represent a switch in MSTG.
"""

import network
import entities
import constants


class Switch(entities.Entity):
    """Represent a switch in the architecture."""

    def __init__(self, name, config):
        super().__init__(name, None)
        self.config = config
        self.network : network.Network | None = None

    def __str__(self):
        return f"Switch: {self.name} - {super().__str__()}"

    def pretty(self):
        return f"Switch: {self.name}"\
                f"\n\t- {super().pretty()}"

    def export_compose(self, file) -> None:
        """Export the switch in the given Docker Compose file."""

        # write template
        mappings = {
            "name": self.name,
            "dockerImage": "mstg_switch",
            "commands": self.export_commands()
        }
        file.write(constants.SWITCH_TEMPLATE.substitute(mappings))

        # no docker networks for a switch

    def export_commands(self) -> str:
        """Export commands to configure the switch to a string."""
        # commands to run inside container at startup
        self.commands.append(constants.OVS_ENABLE_SERVICE)
        self.commands.append(constants.OVS_ADD_BRIDGE.format(self.name))
        self.commands.append(constants.LAUNCH_BACKGROUND_PROCESS)

        prefix = f"/{self.network.network.prefixlen}"

        with open(constants.COMMANDS_FILE, "a", encoding="utf-8") as f:

            for e in self.e2e_conns:
                local_iface_name = f"{e}"
                switch_iface_name = f"{e}_{self.name}"

                # create veth pair
                f.write(constants.LINUX_CREATE_VETH.format(local_iface_name, switch_iface_name) + '\n')

                # move veth into container (not switch)
                f.write(f"pid=$({constants.DOCKER_GET_PID.substitute({"name": e})})\n")
                f.write(constants.LINUX_MOVE_VETH_TO_NS.format(local_iface_name, "$pid")+"\n")

                # set veth up inside container
                f.write(constants.TEMPLATE_CMD.format(e, constants.LINUX_SET_LINK_UP.format(local_iface_name))+"\n")

                # set ip of veth in containers (not switch)
                iface = self.network.get_network_interface(e)
                if iface is None:
                    raise RuntimeError(f"Interface of {e} cannot be found.")
                ip = f"{iface.ip}{prefix}"
                f.write(constants.TEMPLATE_CMD.format(e, constants.LINUX_SET_IP_ADDRESS.format(ip, local_iface_name))+"\n")

                # move other veth to sw namespace
                f.write(f"pid=$({constants.DOCKER_GET_PID.substitute({"name": self.name})})\n")
                f.write(constants.LINUX_MOVE_VETH_TO_NS.format(switch_iface_name, "$pid")+"\n")

                # set veth up inside switch
                f.write(constants.TEMPLATE_CMD.format(self.name, constants.LINUX_SET_LINK_UP.format(switch_iface_name))+"\n")

                # add interface to bridge
                for conn in self.config["connections"]:
                    if conn["path"] == e and "vlan" in conn:
                        f.write(constants.TEMPLATE_CMD.format(
                            self.name, constants.OVS_ADD_PORT_VLAN.format(self.name, switch_iface_name, conn["vlan"])
                        )+"\n")
                    elif conn["path"] == e:
                        f.write(constants.TEMPLATE_CMD.format(
                            self.name, constants.OVS_ADD_PORT.format(self.name, switch_iface_name)
                        )+"\n")

            # bridge interface up
            f.write(constants.TEMPLATE_CMD.format(self.name, constants.LINUX_SET_LINK_UP.format(switch_iface_name))+"\n")

        return self.cmds_combined(separator="&&")[:-2]

    def export_k8s(self):
        pass
