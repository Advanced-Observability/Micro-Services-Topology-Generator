"""
Represent a router in MSTG.
"""

from string import Template

import os

import utils
import network
import entities
import constants
import kubernetes


class Router(entities.Entity):
    """Represent a router in the architecture."""

    def __init__(self, name: str):
        super().__init__(name, None)

    def __str__(self) -> str:
        return f"Router: {self.name} - {super().__str__()}"

    def pretty(self) -> str:
        """Indented string describing the object"""
        return f"Router: {self.name}\n\t- {super().pretty()}"

    def export_commands(self, compose: bool) -> str:
        """Generate one line combining all commands."""

        if utils.is_using_ioam_only() or utils.is_using_clt():
            self.commands.append(constants.LAUNCH_INTERFACE_SCRIPT)
            self.commands.append(constants.ADD_IOAM_NAMESPACE)

        if utils.output_is_k8s():
            # need to drop icmp redirect (type 5) to prevent modification of the routing
            self.commands.append(constants.DROP_ICMP_REDIRECT)

        self.commands.append(constants.DELETE_DEFAULT_IPV4_ROUTE)
        self.commands.append(constants.DELETE_DEFAULT_IPV6_ROUTE)
        self.commands.append(constants.LAUNCH_BACKGROUND_PROCESS)

        if compose:
            return self.cmds_combined()[:-1]

        return self.cmds_combined(True)[:-1]

    def export_compose_networks(self, file) -> None:
        """Export network settings in Docker compose."""

        if self.count_l3_networks() == 0:
            return

        file.write("    networks:\n")

        for i, net in enumerate(self.attached_networks):
            # do not attach L2 network. Will be configured with veth
            if net.type == network.NetworkType.L2_NET:
                continue

            name = net.name
            ip = net.get_entity_ip(self.name)
            mac = net.get_entity_mac(self.name)
            ifname = utils.get_interface_name(i, self.name)

            mappings = {
                "net_name": name,
                "ip": ip,
                "mac": mac,
                "ifname": ifname
            }

            if utils.topology_is_ipv4():
                file.write(constants.COMPOSE_IPV4_NET_SPEC.substitute(mappings))
            else:
                file.write(constants.COMPOSE_IPV6_NET_SPEC.substitute(mappings))

    def export_compose(self, file) -> None:
        """Export the router in the given docker compose file."""

        # write template
        mappings = {
            "name": self.name,
            "dockerImage": "mstg_router" if not utils.is_using_clt() else "mstg_router_clt",
            "commands": self.export_commands(True),
        }
        file.write(constants.ROUTER_TEMPLATE.substitute(mappings))

        # sysctl configuration
        if utils.is_using_clt() or utils.is_using_ioam_only():
            file.write(Template(constants.COMPOSE_SYSCTL_DEFAULTS).substitute({"ioam_id": self.ioam_id}))

        # depends_on
        if len(self.depends_on) > 0:
            file.write("    depends_on:\n")
            for dependency in self.depends_on:
                file.write(f"      - {dependency}\n")

        # write networks
        self.export_compose_networks(file)

    def export_k8s(self):
        """Export the router to Kubernetes configuration files."""

        port = kubernetes.Kubernetes.next_node_port()
        self.export_k8s_pod(port)
        self.export_k8s_service(port)

    def export_k8s_pod(self, port: int):
        """Export the router to a Kubernetes pod using the given `port`."""

        # pod configuration
        pod_config = {
            "name": f"{self.name}-pod",
            "serviceName": f"{self.name}-svc",
            "shortName": self.name,
            "image": "mstg_router" if not utils.is_using_clt() else "mstg_router_clt",
            "cmd": constants.K8S_POD_CMD.format(self.export_commands(False)),
            "CLT_ENABLE": f"\"{os.environ[constants.CLT_ENABLE_ENV]}\"",
            "JAEGER_HOSTNAME": constants.K8S_JAEGER_HOSTNAME,
            "JAEGER_ENABLE": f"\"{os.environ[constants.JAEGER_ENABLE_ENV]}\"",
            "COLLECTOR_HOSTNAME": constants.K8S_COLLECTOR_HOSTNAME,
            "HTTP_VER": os.environ[constants.HTTP_VER_ENV],
            "CERT_FILE": "empty",
            "KEY_FILE": "empty",
            "IP_VERSION": f"\"{os.environ[constants.IP_VERSION_ENV]}\"",
            "ports": Template(constants.K8S_POD_PORT).substitute({"port": port})
        }
        pod = constants.TEMPLATE_K8S_POD.substitute(pod_config)

        # output file
        with open(os.path.join(constants.K8S_EXPORT_FOLDER, f"{self.name}_pod.yaml"), "w", encoding="utf-8") as f:
            f.write(pod)

            # write sysctls
            if utils.is_using_clt() or utils.is_using_ioam_only():
                f.write(Template(constants.K8S_SYSCTL_DEFAULTS).substitute({"ioam_id": self.ioam_id}))

    def export_k8s_service(self, port: int):
        """Export the router to a Kubernetes service using the given `port`."""

        service_config = {
            "name": f"{self.name}-svc",
            "podName": f"{self.name}-pod",
            "ports": Template(constants.K8S_SERVICE_PORT).substitute({"port": port, "nodePort": port})
        }
        service = constants.TEMPLATE_K8S_SERVICE.substitute(service_config)

        with open(os.path.join(constants.K8S_EXPORT_FOLDER, f"{self.name}_service.yaml"), "w", encoding="utf-8") as f:
            f.write(service)
            f.close()
