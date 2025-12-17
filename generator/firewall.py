"""
Represent a firewall in MSTG.
"""

import os
from typing import Any
from string import Template

import utils
import network
import entities
import constants
import kubernetes


class FirewallRule():
    """Represent a firewall rule."""

    def __init__(self, source="", sport="", dest="", dport="", proto="", action="", extension="", custom=""):
        self.source = source
        self.sport = sport
        self.destination = dest
        self.dport = dport
        self.proto = proto
        self.action = action
        self.extension = extension
        self.custom = custom

    def __str__(self) -> str:
        return f"source: {self.source} - "\
                f"sport: {self.sport} - "\
                f"destination: {self.destination} - "\
                f"dport: {self.dport} - "\
                f"proto: {self.proto} - "\
                f"action: {self.action} - "\
                f"extension: {self.extension} - "\
                f"custom: {self.custom}"

    def pretty(self) -> str:
        """Pretty print the rule."""
        return self.__str__()

    def export_rule(self) -> str:
        """Export a rule as a iptables command."""

        if self.custom != "":
            return self.custom

        if utils.topology_is_ipv4():
            cmd = "iptables -A FORWARD "
        else:
            cmd = "ip6tables -A FORWARD "

        if self.proto != "":
            cmd+=f"-p {self.proto} "
        if self.source != "":
            cmd+=f"-s {self.source} "
        if self.sport not in ("", "*"):
            cmd+=f"--sport {self.sport} "
        if self.destination != "":
            cmd+=f"-d {self.destination} "
        if self.dport not in ("", "*"):
            cmd+=f"--dport {self.dport} "
        if self.extension != "":
            cmd+=f"{self.extension} "
        if self.action != "":
            cmd+=f"-j {self.action.upper()} "

        return cmd

def parse_rule(rule: Any):
    """Parse rule from YML."""

    fw_rule = FirewallRule()
    if "source" in rule and rule["source"] is not None:
        fw_rule.source = rule["source"]

    if "sport" in rule and rule["sport"] is not None:
        fw_rule.sport = rule["sport"]

    if "destination" in rule and rule["destination"] is not None:
        fw_rule.destination = rule["destination"]

    if "dport" in rule and rule["dport"] is not None:
        fw_rule.dport = rule["dport"]

    if "protocol" in rule and rule["protocol"] is not None:
        fw_rule.proto = rule["protocol"]

    if "action" in rule and rule["action"] is not None:
        fw_rule.action = rule["action"]

    if "extension" in rule and rule["extension"] is not None:
        fw_rule.extension = rule["extension"]

    if "custom" in rule and rule["custom"] is not None:
        fw_rule.custom = rule["custom"]

    return fw_rule

class Firewall(entities.Entity):
    """Represent a firewall in the architecture."""

    def __init__(self, name, config):
        super().__init__(name, None)
        self.rules : list[FirewallRule] = []
        self.config = config
        self.default = ""
        self.configure_firewall()

    def __str__(self):
        return f"Firewall: {self.name} - rules: {self.rules} - {super().__str__()}"

    def pretty(self):
        """Indented string describing the object."""

        rules = "\n\t\t- " + "\n\t\t- ".join(self.rules)

        return f"Firewall: {self.name}"\
                f"\n\t- rules: {rules}"\
                f"\n\t- {super().pretty()}"

    def configure_firewall(self) -> None:
        """Set internal representation of firewall."""

        self.default = self.config["default"].lower()
        if self.default not in ("accept", "drop"):
            raise RuntimeError(f"Firewall {self.name} default action {self.default} is not valid")

        if "rules" in self.config and self.config["rules"] is not None:
            for rule in self.config["rules"]:
                self.add_rule(parse_rule(rule))

    def add_rule(self, rule: FirewallRule) -> None:
        """Add a rule to the firewall."""
        self.rules.append(rule)

    def export_commands(self, compose: bool) -> str:
        """Generate all commands required to configure the firewall."""
        if utils.output_is_k8s():
            self.commands.append(constants.DROP_ICMP_REDIRECT)

        if utils.topology_is_ipv4():
            self.commands.append(constants.IPTABLES_DEFAULT_ROUTE.format(self.default.upper()))
        else:
            self.commands.append(constants.IP6TABLES_DEFAULT_ROUTE.format(self.default.upper()))

        for rule in self.rules:
            self.commands.append(rule.export_rule())

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
        """Export the firewall in the given docker compose file."""

        mappings = {
            "name": self.name,
            "dockerImage": "mstg_fw",
            "commands": self.export_commands(True)
        }
        file.write(constants.FIREWALL_TEMPLATE.substitute(mappings))

        # depends on
        if len(self.depends_on) > 0:
            file.write("    depends_on:\n")
            for dependency in self.depends_on:
                file.write(f"      - {dependency}\n")

        # write networks
        self.export_compose_networks(file)

        # write extra hosts to prevent conflict in dns
        if len(self.extra_hosts) > 0:
            file.write("    extra_hosts:\n")
            for host in self.extra_hosts:
                file.write(f"      - \"{host[0]}:{host[1]}\"\n")

    def export_k8s(self) -> None:
        """Export the firewall to Kubernetes configuration files."""

        port = kubernetes.Kubernetes.next_node_port()
        self.export_k8s_pod(port)
        self.export_k8s_service(port)

    def export_k8s_pod(self, port: int):
        """Export the firewall to a Kubernetes pod using the given `port`."""

        # pod configuration
        pod_config = {
            "name": f"{self.name}-pod",
            "serviceName": f"{self.name}-svc",
            "shortName": self.name,
            "image": "mstg_fw",
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

            # write extra hosts
            if len(self.extra_hosts) > 0:
                f.write("  hostAliases:")
                for host in self.extra_hosts:
                    f.write(f"""
    - ip: \"{host[1]}\"
      hostnames:
      - \"{host[0]}\"""")

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
