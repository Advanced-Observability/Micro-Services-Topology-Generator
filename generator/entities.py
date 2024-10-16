"""
Entities generated by the generator.
"""

import os

import kubernetes
from utils import *

class DockerNetwork:
    """Represent a Docker network"""

    # used to generate the ip subnets
    # start at 1 because the first network will be used for telemetry.
    networkCounter = 1

    def __init__(self, begin: str, end: str):
        self.begin = begin
        self.end = end
        self.name = DockerNetwork.generate_name(begin, end)

        self.networkID = DockerNetwork.networkCounter + 1
        DockerNetwork.networkCounter+=1

        if output_is_k8s() and topology_is_ipv4():
            self.network = convert_network_id_to_k8s_ipv4(self.networkID)
        elif output_is_k8s() and topology_is_ipv6():
            self.network = convert_network_id_to_k8s_ipv6(self.networkID)
        elif output_is_compose() and topology_is_ipv4():
            self.network = convert_network_id_to_ip4_network(self.networkID)
        elif output_is_compose() and topology_is_ipv6():
            self.network = convert_network_id_to_ip6_network(self.networkID)

        self.subnet = self.network.with_prefixlen
        hosts = iter(self.network.hosts())
        self.gateway = next(hosts) if output_is_compose() else None
        self.beginIP = next(hosts)
        self.endIP = next(hosts)

    def __str__(self) -> str:
        return f"Docker network {self.name} - Subnet: {self.subnet} - Gateway: {self.gateway} - Begin: {self.begin} (IP: {self.beginIP}) - End: {self.end} (IP: {self.endIP}) - ID: {self.networkID}"

    def pretty(self) -> str:
        """Indented string describing the object"""
        return f"Docker network {self.name}\n\t- Subnet: {self.subnet}\n\t- Gateway: {self.gateway}\n\t- Begin: {self.begin} (IP: {self.beginIP})\n\t- End: {self.end} (IP: {self.endIP})\n\t- ID: {self.networkID}"

    def export_compose(self, file) -> None:
        """Export the Docker network in the given docker compose file."""
        mappings = dict(name=self.name, subnet=self.subnet, gateway=self.gateway)
        if topology_is_ipv4():
            file.write(NETWORK_IPV4_TEMPLATE.substitute(mappings))
        else:
            file.write(NETWORK_IPV6_TEMPLATE.substitute(mappings))

    @staticmethod
    def generate_name(begin : str, end : str) -> str:
        """Generate name for Docker network shared by `begin` and `end`."""
        return NETWORK_NAME.format(begin, end)

class Entity:
    """Represent every entity in the architecture."""

    # used to assign a unique IOAM id to every entity
    ioamCounter = 0

    def __init__(self, name : str, kubernetesIP):
        self.name = name
        self.ioamID = Entity.ioamCounter + 1
        Entity.ioamCounter+=1
        self.kubernetesIP = kubernetesIP

        # docker networks to which the entity is attached
        self.attachedNetworks = []
        # list of names of entities on which the current one depends
        # used by docker compose to start the containers in the appropriate order
        self.depends_on = set()
        # ip route commands to configure the networking of the entity
        self.ipRouteCommands = set()
        # additional commands to configure the entity
        self.additionalCommands = []

    def __str__(self) -> str:
        return f"Entity: {self.name} - ioamID: {self.ioamID} - kubernetes IP: {self.kubernetesIP} - networks: {self.attachedNetworks} - depends-on: {self.depends_on} - iproute configuration: {self.iproute_to_str(False)} - additional commands: {self.commands_to_str(False)}"

    def pretty(self) -> str:
        """Indented string describing the object"""
        return f"Entity: {self.name}\n\t\t- ioamID: {self.ioamID}\n\t\t- kubernetes IP: {self.kubernetesIP}\n\t\t- networks: {self.attachedNetworks}\n\t\t- depends-on: {self.depends_on}\n\t\t- iproute configuration:\n{self.iproute_to_str(True)}\n\t\t- additional commands:{self.commands_to_str(True)}"

    def iproute_to_str(self, pretty: bool = False) -> str:
        """Convert ip route commands to str."""
        commandsStr = ""
        for cmd in self.ipRouteCommands:
            if pretty:
                commandsStr+=("\t\t\t- " + str(cmd) + "\n")
            else:
                commandsStr+=("," + str(cmd))
        return commandsStr

    def commands_to_str(self, pretty: bool = False) -> str:
        """Convert commands to str."""
        commandsStr = ""
        for cmd in self.additionalCommands:
            if pretty:
                commandsStr+=("\n\t\t\t- " + str(cmd))
            else:
                commandsStr+=("," + str(cmd))
        return commandsStr

    def get_network_pos(self, name : str) -> int | None:
        """
        Get id of attached network with given `name`.
        If not found, return None.
        """

        for net in self.attachedNetworks:
            if net["name"] == name:
                return self.attachedNetworks.index(net)

        return None

class Service(Entity):
    """Represent a microservice in the architecture."""

    def __init__(self, name : str, entity):
        super().__init__(name, None)

        self.port = entity["port"]

        # Port exposed by default
        if "expose" in entity:
            self.expose = entity["expose"]
        else:
            self.expose = True

        # end-to-end connections
        self.e2eConnections = []
        # hosts to which the entity is connected to in end-to-end connections
        self.extraHosts = set()

    def __str__(self) -> str:
        return f"Service: {self.name} - port: {self.port} - e2e connections: {self.e2e_to_str()} - {super().__str__()}"

    def pretty(self) -> str:
        return f"Service: {self.name}\n\t- port: {self.port}\n\t- e2e connections: {self.e2e_to_str()}\n\t- extra hosts: {self.extraHosts}\n\t- {super().pretty()}"

    def e2e_to_str(self) -> str:
        """Convert end-to-end connections to string."""
        e2e = ""
        for e2econn in self.e2eConnections:
                e2e+=(e2econn+",")
        return e2e

    def export_compose(self, file) -> None:
        """Export the service in the given docker compose file."""

        # generate one line combining all extra commands
        additionalCommands = ""
        for cmd in self.ipRouteCommands:
            additionalCommands+=(f"({cmd}) & ")
        for cmd in self.additionalCommands:
            additionalCommands+=(f"({cmd}) & ")
        if is_using_ioam_only() or is_using_clt():
            additionalCommands+=(f"(sh set_interfaces.sh) & ")

        image = "mstg_service" if not is_using_clt() else "mstg_service_clt"

        # write template
        mappings = dict(
            name=self.name, ioamID=self.ioamID,
            additionalCommands=additionalCommands,
            CLT_ENABLE=os.environ[CLT_ENABLE_ENV], IOAM_ONLY=os.environ[IOAM_ENABLE_ENV],
            dockerImage=image, JAEGER_ENABLE=os.environ[JAEGER_ENABLE_ENV],
            HTTP_VER=os.environ[HTTP_VER_ENV], IOAM_ENABLE=os.environ[IOAM_ENABLE_ENV]
        )
        if topology_is_ipv4():
            file.write(SERVICE_IPV4_TEMPLATE.substitute(mappings))
        else:
            file.write(SERVICE_IPV6_TEMPLATE.substitute(mappings))

        if self.expose == True:
            file.write("    ports:\n")
            file.write(f"     - {self.port}:{self.port}\n")

        # if using https => add key + cert
        if topology_is_https():
            file.write(f"      - CERT_FILE={PATH_CERTIFICATE}\n")
            file.write(f"      - KEY_FILE={PATH_KEY_FILE}\n")

        # sysctl configuration
        if is_using_clt() or is_using_ioam_only():
            file.write("    sysctls:")
            file.write(Template(COMPOSE_SYSCTL_DEFAULTS).substitute(dict(ioamID=self.ioamID)))

        # depends_on
        alreadyWrote = False
        if is_using_jaeger() or is_using_clt():
            alreadyWrote = True
            file.write("    depends_on:\n")
        if is_using_jaeger():
            file.write("      - jaeger\n")
        if is_using_clt():
            file.write("      - ioam-collector\n")
        if not alreadyWrote and len(self.depends_on) > 0:
            file.write("    depends_on:\n")
        for dependency in self.depends_on:
            file.write(f"      - {dependency}\n")

        # write networks
        wroteHeader = False
        if is_using_jaeger():
            wroteHeader = True
            file.write("    networks:\n")
            file.write("      network_telemetry:\n")
        if len(self.attachedNetworks) > 0 and not wroteHeader:
            file.write("    networks:\n")
        for net in self.attachedNetworks:
            file.write("      " + net["name"]+':\n')
            if topology_is_ipv4():
                file.write("        ipv4_address: " + str(net["ip"])+'\n')
            else:
                file.write("        ipv6_address: " + str(net["ip"])+'\n')

        # write extra hosts to prevent conflict in dns
        if len(self.extraHosts) > 0:
            file.write("    extra_hosts:\n")
            for host in self.extraHosts:
                file.write("      - \"{}:{}\"\n".format(host[0], host[1]))

    def export_k8s(self):
        """Export the service to Kubernetes configuration files."""

        self.export_k8s_pod()
        self.export_k8s_service()

    def export_k8s_pod(self):
        """Export the service to a Kubernetes pod."""

        # generate oneline combining all commands
        # need to drop icmp redirect (type 5) to prevent modification of the routing
        onelineCmd = f"({DROP_ICMP_REDIRECT}) & "
        onelineCmd+=f"({ADD_IOAM_NAMESPACE}) & "
        for cmd in self.ipRouteCommands:
            # sleep for 10s to be sure that vxlan interfaces had time to be configured properly by meshnet cni
            onelineCmd+=(f"(sleep 20 && {cmd}) & ")
        for cmd in self.additionalCommands:
            onelineCmd+=(f"(sleep 20 && {cmd}) & ")
        if is_using_ioam_only() or is_using_clt():
            onelineCmd+=(f"(sleep 20 && sh set_interfaces.sh) & ")
        onelineCmd+=("(/usr/local/bin/service /etc/config.yml)")
        # add ioam agent is using clt
        if is_using_clt():
            onelineCmd+="& (/ioam-agent -i eth0)"
        cmd=f"""
        - sh
        - -c
        - {onelineCmd}
"""

        image = "mstg_service" if not is_using_clt() else "mstg_service_clt"

        # pod configuration
        podConfig = dict(
            name=f"{self.name}-pod", serviceName=f"{self.name}-svc", shortName=self.name, image=image, cmd=cmd,
            CLT_ENABLE=f"\"{os.environ[CLT_ENABLE_ENV]}\"",
            JAEGER_HOSTNAME=K8S_JAEGER_HOSTNAME, JAEGER_ENABLE=f"\"{os.environ[JAEGER_ENABLE_ENV]}\"",
            COLLECTOR_HOSTNAME=K8S_COLLECTOR_HOSTNAME,
            HTTP_VER=os.environ[HTTP_VER_ENV], CERT_FILE="empty", KEY_FILE="empty",
            IP_VERSION=f"\"{os.environ[IP_VERSION_ENV]}\"", port=self.port
        )

        if topology_is_https():
            podConfig["CERT_FILE"] = PATH_CERTIFICATE
            podConfig["KEY_FILE"] = PATH_KEY_FILE

        pod = TEMPLATE_K8S_POD.substitute(podConfig)

        # output file
        f = open(f"{K8S_EXPORT_FOLDER}/{self.name}_pod.yaml", "w")
        f.write(pod)

        # write sysctls
        if is_using_clt() or is_using_ioam_only():
            f.write(Template(K8S_SYSCTL_DEFAULTS).substitute(dict(ioamID=self.ioamID)))

        # write extra hosts
        if len(self.extraHosts) > 0:
            f.write("  hostAliases:")
            for host in self.extraHosts:
                f.write(f"""
    - ip: \"{host[1]}\"
      hostnames:
      - \"{host[0]}\"""")

        f.close()

    def export_k8s_service(self):
        """Export the service to a Kubernetes service."""

        nodePort = kubernetes.Kubernetes.next_node_port()
        serviceConfig = dict(name=f"{self.name}-svc", podName=f"{self.name}-pod", port=self.port, nodePort=nodePort)
        service = TEMPLATE_K8S_SERVICE.substitute(serviceConfig)
        f = open(f"{K8S_EXPORT_FOLDER}/{self.name}_service.yaml", "w")
        f.write(service)
        f.close()

class Router(Entity):
    """Represent a router in the architecture."""

    def __init__(self, name : str):
        super().__init__(name, None)

    def __str__(self) -> str:
        return f"Router: {self.name} - {super().__str__()}"

    def pretty(self) -> str:
        """Indented string describing the object"""
        return f"Router: {self.name}\n\t- {super().pretty()}"

    def export_compose(self, file) -> None:
        """Export the service in the given docker compose file."""

        # generate one line combining all extra commands
        additionalCommands = ""
        for cmd in self.ipRouteCommands:
            additionalCommands+=(f"({cmd}) & ")
        for cmd in self.additionalCommands:
            additionalCommands+=(f"({cmd}) & ")
        if is_using_ioam_only() or is_using_clt():
            additionalCommands+=(f"(sh set_interfaces.sh) & ")

        image = "mstg_router" if not is_using_clt() else "mstg_router_clt"

        # write template
        mappings = dict(
            name=self.name, ioamID=self.ioamID, additionalCommands=additionalCommands,
            CLT_ENABLE=os.environ[CLT_ENABLE_ENV], IOAM_ONLY=os.environ[IOAM_ENABLE_ENV],
            dockerImage=image
        )
        if topology_is_ipv4():
            file.write(ROUTER_IPV4_TEMPLATE.substitute(mappings))
        else:
            file.write(ROUTER_IPV6_TEMPLATE.substitute(mappings))

        # sysctl configuration
        if is_using_clt() or is_using_ioam_only():
            file.write(Template(COMPOSE_SYSCTL_DEFAULTS).substitute(dict(ioamID=self.ioamID)))

        # depends_on
        if len(self.depends_on) > 0:
            file.write("    depends_on:\n")
            for dependency in self.depends_on:
                file.write(f"      - {dependency}\n")

        # write networks
        file.write("    networks:\n")
        for net in self.attachedNetworks:
            file.write("      " + net["name"]+':\n')
            if topology_is_ipv4():
                file.write("        ipv4_address: " + str(net["ip"])+'\n')
            else:
                file.write("        ipv6_address: " + str(net["ip"])+'\n')

    def export_k8s(self):
        """Export the router to Kubernetes configuration files."""

        port = kubernetes.Kubernetes.next_node_port()
        self.export_k8s_pod(port)
        self.export_k8s_service(port)

    def export_k8s_pod(self, port : int):
        """Export the router to a Kubernetes pod using the given `port`."""

        # generate one line combining all commands
        # need to drop icmp redirect (type 5) to prevent modification of the routing
        onelineCmd = f"({DROP_ICMP_REDIRECT}) & "
        onelineCmd+=f"({ADD_IOAM_NAMESPACE}) & "
        for cmd in self.ipRouteCommands:
            # sleep for 10s to be sure that vxlan interfaces had time to be configured properly by meshnet cni
            onelineCmd+=(f"(sleep 20 && {cmd}) & ")
        for cmd in self.additionalCommands:
            onelineCmd+=(f"(sleep 20 && {cmd}) & ")
        if is_using_ioam_only() or is_using_clt():
            onelineCmd+=(f"(sleep 20 && sh set_interfaces.sh) & ")

        onelineCmd+=("(tail -f /dev/null)")
        cmd=f"""
        - sh
        - -c
        - {onelineCmd}
"""
        image = "mstg_router" if not is_using_clt() else "mstg_router_clt"

        # pod configuration
        podConfig = dict(
            name=f"{self.name}-pod", serviceName=f"{self.name}-svc", shortName=self.name, image=image, cmd=cmd,
            CLT_ENABLE=f"\"{os.environ[CLT_ENABLE_ENV]}\"",
            JAEGER_HOSTNAME=K8S_JAEGER_HOSTNAME, JAEGER_ENABLE=f"\"{os.environ[JAEGER_ENABLE_ENV]}\"",
            COLLECTOR_HOSTNAME=K8S_COLLECTOR_HOSTNAME,
            HTTP_VER=os.environ[HTTP_VER_ENV], CERT_FILE="empty", KEY_FILE="empty",
            IP_VERSION=f"\"{os.environ[IP_VERSION_ENV]}\"", port=port
        )
        pod = TEMPLATE_K8S_POD.substitute(podConfig)

        # output file
        f = open(f"{K8S_EXPORT_FOLDER}/{self.name}_pod.yaml", "w")
        f.write(pod)

        # write sysctls
        if is_using_clt() or is_using_ioam_only():
            f.write(Template(K8S_SYSCTL_DEFAULTS).substitute(dict(ioamID=self.ioamID)))

        f.close()

    def export_k8s_service(self, port : int):
        """Export the router to a Kubernetes service using the given `port`."""

        serviceConfig = dict(name=f"{self.name}-svc", podName=f"{self.name}-pod", port=port, nodePort=port)
        service = TEMPLATE_K8S_SERVICE.substitute(serviceConfig)
        f = open(f"{K8S_EXPORT_FOLDER}/{self.name}_service.yaml", "w")
        f.write(service)
        f.close()
