"""
Constants used in MSTG.
"""

import os
from pathlib import Path
from string import Template
from tokenize import EXACT_TOKEN_TYPES


def read_file(path: str) -> str:
    """Read file at given `path`."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# --------------------------------------------------------------------------------------------------

VERSION = "0.0.10"

DEFAULT_CONFIG_FILE = "./config.yaml"

COMMANDS_FILE = "./commands.sh"

# ------------------------------------ IOAM TRACE TYPE CONFIGURATION -------------------------------

# hop limit + node id
IOAM_BIT0 = True
# ingress and egress id
IOAM_BIT1 = False
# timestamp
IOAM_BIT2 = False
# timestamp fraction
IOAM_BIT3 = False
# namespace specific
IOAM_BIT5 = False
# queue depth
IOAM_BIT6 = False
# hop limit + node id wide
IOAM_BIT8 = False
# ingress and egress id wide
IOAM_BIT9 = False
# namespace specific wide
IOAM_BIT10 = False
# opaque state
IOAM_BIT22 = False

# --------------------------------------- ENV. VARIABLES -------------------------------------------

DEBUG_VAR_ENV = "DEBUG"
HTTP_VER_ENV = "HTTP_VER"
K8S_OUT_ENV = "K8S_OUT_ENV"
CLT_ENABLE_ENV = "CLT_ENABLE"
IP_VERSION_ENV = "IP_VERSION"
IOAM_ENABLE_ENV = "IOAM_OUT_ENV"
JAEGER_ENABLE_ENV = "JAEGER_ENABLE"
COMPOSE_OUT_ENV = "COMPOSE_OUT_ENV"
OUTPUT_FORMAT_ENV = "OUTPUT_FORMAT_ENV"

# --------------------------------------- TEMPLATES -----------------------------------------------

# -- network --

NETWORK_NAME = "network_{}_{}"
SWITCH_NET_NAME = "network_switch_{}"

# -- commands --

DOCKER_CMD = "docker exec {} sh -c '{}'"
DOCKER_CMD_BACKGROUND = "docker exec -d {} sh -c '{}'"
KUBECTL_CMD = "kubectl exec {} -- bash -c '{}'"
CMD_INLINE_SYSCTL = """for sInterface in /proc/sys/net/ipv6/conf/*; do name=$(basename $sInterface); sysctl -q -w net.ipv6.conf.$name.ioam6_enabled=1; sysctl -q -w net.ipv6.conf.$name.ioam6_id={}; done"""

# -- compose --

TEMPLATE_COMPOSE_FOLDER = os.path.join(Path(__file__).parent, "templates/compose")
ROUTER_TEMPLATE = Template(
    read_file(os.path.join(TEMPLATE_COMPOSE_FOLDER, "router-template.yaml"))
)
SERVICE_TEMPLATE = Template(
    read_file(os.path.join(TEMPLATE_COMPOSE_FOLDER, "service-template.yaml"))
)
EXTERNAL_TEMPLATE = Template(
    read_file(os.path.join(TEMPLATE_COMPOSE_FOLDER, "external-template.yaml"))
)
FIREWALL_TEMPLATE = Template(
    read_file(os.path.join(TEMPLATE_COMPOSE_FOLDER, "firewall-template.yaml"))
)
SWITCH_TEMPLATE = Template(
    read_file(os.path.join(TEMPLATE_COMPOSE_FOLDER, "switch-template.yaml"))
)
JAEGER_SERVICE = read_file(os.path.join(TEMPLATE_COMPOSE_FOLDER, "jaeger-service.yaml"))
IOAM_COLLECTOR_SERVICE = read_file(
    os.path.join(TEMPLATE_COMPOSE_FOLDER, "ioam-collector-ipv6.yaml")
)

# ipv4
NETWORK_IPV4_TEMPLATE = Template(
    read_file(os.path.join(TEMPLATE_COMPOSE_FOLDER, "network-template-ipv4.yaml"))
)
TELEMETRY_IPV4_NETWORK = read_file(
    os.path.join(TEMPLATE_COMPOSE_FOLDER, "telemetry-network-ipv4.yaml")
)

# ipv6
NETWORK_IPV6_TEMPLATE = Template(
    read_file(os.path.join(TEMPLATE_COMPOSE_FOLDER, "network-template-ipv6.yaml"))
)
TELEMETRY_IPV6_NETWORK = read_file(
    os.path.join(TEMPLATE_COMPOSE_FOLDER, "telemetry-network-ipv6.yaml")
)

# -- kubernetes --

TEMPLATE_FOLDER_K8S = os.path.join(Path(__file__).parent, "templates/kubernetes")
TEMPLATE_K8S_POD = Template(
    read_file(os.path.join(TEMPLATE_FOLDER_K8S, "k8s-pod.yaml"))
)
TEMPLATE_K8S_SERVICE = Template(
    read_file(os.path.join(TEMPLATE_FOLDER_K8S, "k8s-service.yaml"))
)
K8S_JAEGER_POD = read_file(os.path.join(TEMPLATE_FOLDER_K8S, "k8s-jaeger-pod.yaml"))
K8S_JAEGER_SERVICE = Template(
    read_file(os.path.join(TEMPLATE_FOLDER_K8S, "k8s-jaeger-service.yaml"))
)
K8S_COLLECTOR_POD = read_file(
    os.path.join(TEMPLATE_FOLDER_K8S, "k8s-ioam-collector-pod.yaml")
)
K8S_COLLECTOR_SERVICE = Template(
    read_file(os.path.join(TEMPLATE_FOLDER_K8S, "k8s-ioam-collector-service.yaml"))
)
TEMPLATE_MESHNET_CONFIG = Template(
    read_file(os.path.join(TEMPLATE_FOLDER_K8S, "k8s-meshnet-config.yaml"))
)
TEMPLATE_MESHNET_INTERFACE = Template(
    read_file(os.path.join(TEMPLATE_FOLDER_K8S, "k8s-meshnet-interface.yaml"))
)

# --------------------------------------- SYSCTL ---------------------------------------------------

# IOAM/CLT in docker compose
COMPOSE_SYSCTL_DEFAULTS = """
      - net.ipv6.ioam6_id=${ioam_id}
      - net.ipv6.conf.all.ioam6_id=${ioam_id}
      - net.ipv6.conf.default.ioam6_id=${ioam_id}
      - net.ipv6.conf.all.ioam6_enabled=1
      - net.ipv6.conf.default.ioam6_enabled=1
"""

# IOAM/CLT in k8s
K8S_SYSCTL_DEFAULTS = """
      - name: net.ipv6.ioam6_id
        value: "${ioam_id}"
      - name: net.ipv6.conf.all.ioam6_id
        value: "${ioam_id}"
      - name: net.ipv6.conf.default.ioam6_id
        value: "${ioam_id}"
      - name: net.ipv6.conf.all.ioam6_enabled
        value: "1"
      - name: net.ipv6.conf.default.ioam6_enabled
        value: "1"
"""

# --------------------------------------- IP ROUTE COMMANDS FOR IPv6 -------------------------------

IP6_ROUTE_DIRECT_IOAM = (
    "ip -6 r a {} encap ioam6 trace prealloc type {} ns 123 size {} dev {}"
)
IP6_ROUTE_PATH_IOAM = (
    "ip -6 r a {} encap ioam6 trace prealloc type {} ns 123 size {} via {}"
)
IP6_ROUTE_PATH_VANILLA = "ip -6 r a {} via {}"

# --------------------------------------- IP ROUTE COMMANDS FOR IPv4 -------------------------------

# never IOAM because IOAM works only for ipv6
IP4_ROUTE_PATH_VANILLA = "ip r a {} via {}"

# --------------------------------------- COMMANDS -------------------------------------------------

DROP_ICMP_REDIRECT = (
    "iptables -A OUTPUT -p icmp --icmp-type 5 -j DROP && "
    "iptables -A INPUT -p icmp --icmp-type 5 -j DROP"
)
IPTABLES_DEFAULT_ROUTE = "iptables -P FORWARD {}"
IP6TABLES_DEFAULT_ROUTE = "ip6tables -P FORWARD {}"

ADD_IOAM_NAMESPACE = "ip ioam namespace add 123"

DELETE_DEFAULT_IPV6_ROUTE = "ip -6 r d default"
DELETE_DEFAULT_IPV4_ROUTE = "ip r d default"

LAUNCH_SERVICE = "/usr/local/bin/service /etc/config.yaml"
LAUNCH_INTERFACE_SCRIPT = "sh set_interfaces.sh"
LAUNCH_IOAM_AGENT = "/ioam-agent -i eth0"
LAUNCH_BACKGROUND_PROCESS = "tail -f /dev/null"

OVS_CHECK_CMD = "lsmod | awk '{print $1}' | grep -i openvswitch"
OVS_ENABLE_SERVICE = "service openvswitch-switch start"
OVS_ADD_BRIDGE = "ovs-vsctl add-br {}"
OVS_ADD_PORT = "ovs-vsctl add-port {} {}"
OVS_ADD_PORT_VLAN = "ovs-vsctl add-port {} {} tag={}"

LINUX_CREATE_VETH = "ip link add {} type veth peer name {}"
LINUX_MOVE_VETH_TO_NS = "ip link set {} netns $pid"
LINUX_SET_LINK_UP = "ip link set {} up"
LINUX_SET_IP_ADDRESS = "ip addr add {} dev {}"

DOCKER_GET_PID = Template("""docker inspect -f '{{.State.Pid}}' ${name}""")

# --------------------------------------- FOR PARSING THE CONFIG -----------------------------------

# Types of entities supported by the generator
KNOWN_TYPES = ["service", "router", "external", "firewall", "switch"]
INTERMEDIARY_TYPES = ["router", "firewall", "switch"]
END_HOST_TYPES = ["service", "external"]

# Fields shared by all types
MANDATORY_COMMON_FIELDS = ["type"]

# Fields for services
SERVICE_FIELDS = ["port", "endpoints"]
SERVICE_ENDPOINT_FIELDS = ["entrypoint", "respsize"]

# Fields for external container
EXTERNAL_FIELDS = ["image", "ports", "connections"]

# Fields for firewall
FIREWALL_FIELDS = ["default", "neighbors", "rules"]
FIREWALL_RULES_FIELDS = [
    "source",
    "sport",
    "destination",
    "dport",
    "protocol",
    "action",
    "extension",
    "custom",
]

# Fields for switch
SWITCH_FIELDS = ["neighbors"]

# Fields for router
ROUTER_FIELDS = ["neighbors"]

# Ports used by telemetry
TELEMETRY_PORTS = [1686, 14268, 4317, 4318, 7123]

# Fields for connections
CONNECTION_SERVICE_MANDATORY_FIELDS = ["path", "url"]
CONNECTION_EXTERNAL_MANDATORY_FIELDS = ["path"]
CONNECTION_ROUTER_MANDATORY_FIELDS = []
CONNECTION_FIREWALL_MANDATORY_FIELDS = []
CONNECTION_SW_MANDATORY_FIELDS = []
CONNECTION_IMPAIRMENTS = [
    "mtu",
    "buffer_size",
    "rate",
    "delay",
    "jitter",
    "loss",
    "corrupt",
    "duplicate",
    "reorder",
    "timers",
]
CONNECTION_OPTIONAL_FIELDS = ["hop", "vlan"]
CONNECTION_OPTIONAL_FIELDS.extend(CONNECTION_IMPAIRMENTS)

# -- options and timers --

# commands to modify the properties of the connections
MTU_OPTION = "ip link set dev {} mtu {}"
BUFFER_SIZE_OPTION = "ip link set dev {} txqueuelen {}"
IMPAIRMENT_OPTION = "tc qdisc add dev {} root netem"
MODIFY_IMPAIRMENT = "sleep {} && {}"
MODIFY_IMPAIRMENT_DELETE_TC = "sleep {} && tc qdisc del dev {} root && {}"

# regex to match iproute2 `tc` specifications
TC_PERCENTAGE_REGEX = r"\A([0-9]{1,2}|100)%\Z"
TC_TIME_REGEX = r"\A[0-9]+(s|ms|us)\Z"
TC_RATE_REGEX = r"\A[0-9]+(bit|kbit|mbit|gbit|tbit|bps|kbps|mbps|gbps|tbps)\Z"

# timers
TIMER_EXPECTED_FIELDS = ["option", "start", "newValue"]
TIMER_OPTIONAL_FIELDS = ["duration"]
TIMER_TIME_REGEX = r"\A(?=.)(([0-9]*)(\.([0-9]+))?)\Z"

# --------------------------------------- HTTPS ----------------------------------------------------

PATH_CERTIFICATE = "/server.crt"
PATH_KEY_FILE = "/server.key"

# --------------------------------------- COMPOSE --------------------------------------------------

COMPOSE_IPV4_NET_SPEC = Template("""
      ${net_name}:
        ipv4_address: ${ip}
        mac_address: ${mac}
        interface_name: ${ifname}
""")

COMPOSE_IPV6_NET_SPEC = Template("""
      ${net_name}:
        ipv6_address: ${ip}
        mac_address: ${mac}
        interface_name: ${ifname}
""")

COMPOSE_JAEGER_IPV4 = """        ipv4_address: 0.0.4.2"""
COMPOSE_JAEGER_IPV6 = """        ipv6_address: ::1:0:0:0:2"""

# --------------------------------------- KUBERNETES -----------------------------------------------

K8S_DEFAULT_NODE_PORT_MIN = 30000
K8S_DEFAULT_NODE_PORT_MAX = 32767
K8S_EXPORT_FOLDER = "./k8s_configs"  # do NOT put a '/' at the end

K8S_GET_SERVICE_IP_RANGE_CMD = (
    "kubectl cluster-info dump | grep -m 1 service-cluster-ip-range | "
    "tr -d '[:space:]' | grep -o '=.*' | cut -c 2- | rev | cut -c 3- | rev"
)
K8S_GET_PODS_IP_RANGE_CMD = (
    "kubectl cluster-info dump | grep -m 1 cluster-cidr | "
    "tr -d '[:space:]' | grep -o '=.*' | cut -c 2- | rev | cut -c 3- | rev"
)
K8S_CHECK_MESHNET = "kubectl get daemonset -n meshnet | awk '{print $2,$3,$4,$5}'"
K8S_KUBECTL_CHECK_EXEC = "which kubectl"
K8S_KUBECTL_GET_CONFIG = "kubectl config view"
K8S_KUBECTL_GET_CLUSTER_INFO = "kubectl cluster-info"
K8S_KUBECTL_GET_NODES_COUNT = "kubectl get nodes | wc -l"

K8S_JAEGER_HOSTNAME = "jaeger-pod.jaeger-svc.default.svc.cluster.local"
K8S_COLLECTOR_HOSTNAME = (
    "ioam-collector-pod.ioam-collector-svc.default.svc.cluster.local:7123"
)

K8S_POD_PORT = """
        - containerPort: ${port}
          hostPort: ${port}
          protocol: TCP
"""

K8S_POD_CMD = """
      args:
        - sh
        - -c
        - {}
"""

K8S_SERVICE_PORT = """
    - name: "${port}"
      port: ${port}
      targetPort: ${port}
      nodePort: ${nodePort}
"""

# --------------------------------------- ASCII ART ------------------------------------------------

ASCII_ART = r"""
  __  __  _____ _______ _____
 |  \/  |/ ____|__   __/ ____|
 | \  / | (___    | | | |  __
 | |\/| |\___ \   | | | | |_ |
 | |  | |____) |  | | | |__| |
 |_|  |_|_____/   |_|  \_____|
"""
