"""
Constants used in the generator.
"""

import os
from string import Template
from pathlib import Path

VERSION = "0.0.2"

DEFAULT_CONFIG_FILE="./config.yml"

# ------------------------------------ IOAM TRACE TYPE CONFIGURATION ------------------------------------

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

# --------------------------------------- ENV. VARIABLES -----------------------------------------------

CLT_ENABLE_ENV = "CLT_ENABLE"
IP_VERSION_ENV = "IP_VERSION"
HTTP_VER_ENV = "HTTP_VER"
DEBUG_VAR_ENV = "DEBUG"
JAEGER_ENABLE_ENV = "JAEGER_ENABLE"
OUTPUT_FORMAT_ENV = "OUTPUT_FORMAT_ENV"
K8S_OUT_ENV = "K8S_OUT_ENV"
COMPOSE_OUT_ENV = "COMPOSE_OUT_ENV"
IOAM_ENABLE_ENV = "IOAM_OUT_ENV"

# --------------------------------------- TEMPLATES -----------------------------------------------

# network

NETWORK_NAME = "network_{}_{}"

# compose
TEMPLATE_COMPOSE_FOLDER = os.path.join(Path(__file__).parent, "templates/compose")
IOAM_COLLECTOR_SERVICE = open(os.path.join(TEMPLATE_COMPOSE_FOLDER, "ioam-collector-ipv6.yml")).read()
## ipv4
JAEGER_IPV4_SERVICE = open(os.path.join(TEMPLATE_COMPOSE_FOLDER, "jaeger-service-ipv4.yml")).read()
NETWORK_IPV4_TEMPLATE = Template(open(os.path.join(TEMPLATE_COMPOSE_FOLDER, "network-template-ipv4.yml")).read())
ROUTER_IPV4_TEMPLATE = Template(open(os.path.join(TEMPLATE_COMPOSE_FOLDER, "router-template-ipv4.yml")).read())
SERVICE_IPV4_TEMPLATE = Template(open(os.path.join(TEMPLATE_COMPOSE_FOLDER, "service-template-ipv4.yml")).read())
TELEMETRY_IPV4_NETWORK = open(os.path.join(TEMPLATE_COMPOSE_FOLDER, "telemetry-network-ipv4.yml")).read()
## ipv6
JAEGER_IPV6_SERVICE = open(os.path.join(TEMPLATE_COMPOSE_FOLDER, "jaeger-service-ipv6.yml")).read()
NETWORK_IPV6_TEMPLATE = Template(open(os.path.join(TEMPLATE_COMPOSE_FOLDER, "network-template-ipv6.yml")).read())
ROUTER_IPV6_TEMPLATE = Template(open(os.path.join(TEMPLATE_COMPOSE_FOLDER, "router-template-ipv6.yml")).read())
SERVICE_IPV6_TEMPLATE = Template(open(os.path.join(TEMPLATE_COMPOSE_FOLDER, "service-template-ipv6.yml")).read())
TELEMETRY_IPV6_NETWORK = open(os.path.join(TEMPLATE_COMPOSE_FOLDER, "telemetry-network-ipv6.yml")).read()

# kubernetes

TEMPLATE_FOLDER_K8S = os.path.join(Path(__file__).parent, "templates/kubernetes")
TEMPLATE_K8S_POD = Template(open(os.path.join(TEMPLATE_FOLDER_K8S, "k8s-pod.yml")).read())
TEMPLATE_K8S_SERVICE = Template(open(os.path.join(TEMPLATE_FOLDER_K8S, "k8s-service.yml")).read())
K8S_JAEGER_POD = open(os.path.join(TEMPLATE_FOLDER_K8S, "k8s-jaeger-pod.yml")).read()
K8S_JAEGER_SERVICE = Template(open(os.path.join(TEMPLATE_FOLDER_K8S, "k8s-jaeger-service.yml")).read())
K8S_COLLECTOR_POD = open(os.path.join(TEMPLATE_FOLDER_K8S, "k8s-ioam-collector-pod.yml")).read()
K8S_COLLECTOR_SERVICE = Template(open(os.path.join(TEMPLATE_FOLDER_K8S, "k8s-ioam-collector-service.yml")).read())
TEMPLATE_MESHNET_CONFIG = Template(open(os.path.join(TEMPLATE_FOLDER_K8S, "k8s-meshnet-config.yml")).read())
TEMPLATE_MESHNET_INTERFACE = Template(open(os.path.join(TEMPLATE_FOLDER_K8S, "k8s-meshnet-interface.yml")).read())

# --------------------------------------- SYSCTL -----------------------------------------------

# sysctl configuration for any entity if IOAM/CLT is used
COMPOSE_SYSCTL_DEFAULTS = """
      - net.ipv6.ioam6_id=${ioamID}
      - net.ipv6.conf.all.ioam6_id=${ioamID}
      - net.ipv6.conf.default.ioam6_id=${ioamID}
      - net.ipv6.conf.all.ioam6_enabled=1
      - net.ipv6.conf.default.ioam6_enabled=1
"""

# sysctl configuration for any entity if IOAM/CLT is used
K8S_SYSCTL_DEFAULTS = """
      - name: net.ipv6.ioam6_id
        value: "${ioamID}"
      - name: net.ipv6.conf.all.ioam6_id
        value: "${ioamID}"
      - name: net.ipv6.conf.default.ioam6_id
        value: "${ioamID}"
      - name: net.ipv6.conf.all.ioam6_enabled
        value: "1"
      - name: net.ipv6.conf.default.ioam6_enabled
        value: "1"
"""

K8S_SYSCTL_IOAM_ID = """      - name: net.ipv6.conf.eth${i}.ioam6_id\n        value: \"${ioamID}\"\n"""
K8S_SYSCTL_IOAM_ENABLE = """      - name: net.ipv6.conf.eth${i}.ioam6_enabled\n        value: \"1\"\n"""
CMD_SYSCTL_IOAM_ID ="""sysctl -q -w net.ipv6.conf.eth${i}.ioam6_id=${ioamID}"""
CMD_SYSCTL_IOAM_ENABLE = """sysctl -q -w net.ipv6.conf.eth${i}.ioam6_enabled=1"""

# --------------------------------------- IP ROUTE COMMANDS FOR IPv6 -----------------------------------------------

TEMPLATE_IP6_ROUTE_DIRECT_CONNECTION = "/sbin/ip -6 r a {} encap ioam6 trace prealloc type {} ns 123 size {} dev eth{}"
TEMPLATE_IP6_ROUTE_PATH = "/sbin/ip -6 r a {} encap ioam6 trace prealloc type {} ns 123 size {} via {}"
TEMPLATE_IP6_ROUTE_PATH_NO_IOAM = "/sbin/ip -6 r a {} via {}"

# --------------------------------------- IP ROUTE COMMANDS FOR IPv4 -----------------------------------------------

# never IOAM because IOAM works only for ipv6
TEMPLATE_IP4_ROUTE_PATH = "/sbin/ip r a {} via {}"

# --------------------------------------- COMMANDS -----------------------------------------------

DROP_ICMP_REDIRECT = "iptables -A OUTPUT -p icmp --icmp-type 5 -j DROP && iptables -A INPUT -p icmp --icmp-type 5 -j DROP"
ADD_IOAM_NAMESPACE = "/sbin/ip ioam namespace add 123"

# --------------------------------------- FOR PARSING THE CONFIG -----------------------------------------------

# Types of entities supported by the generator
KNOWN_TYPES = ["service", "router"]

# Fields shared by all types
MANDATORY_COMMON_FIELDS = ["type"]

# Fields for services
SERVICE_FIELDS = ["port", "endpoints"]
SERVICE_ENDPOINT_FIELDS = ["entrypoint", "psize"]

# Ports used by telemtry
TELEMETRY_PORTS  = [1686, 14268, 4317, 4318, 7123]

# fields for connections
CONNECTION_ROUTER_MANDATORY_FIELDS = ["path"]
CONNECTION_SERVICE_MANDATORY_FIELDS = ["path", "url"]
CONNECTION_IMPAIRMENTS = ["mtu", "buffer_size", "rate", "delay", "jitter", "loss", "corrupt", "duplicate", "reorder", "timers"]
CONNECTION_OPTIONAL_FIELDS = ["timers"]
CONNECTION_OPTIONAL_FIELDS.extend(CONNECTION_IMPAIRMENTS)

# commands to modify the properties of the connections
MTU_OPTION = "/sbin/ip link set dev eth{} mtu {}"
BUFFER_SIZE_OPTION = "/sbin/ip link set dev eth{} txqueuelen {}"
MODIFY_IMPAIRMENT = "sleep {} && {}"
MODIFY_IMPAIRMENT_DELETE_TC = "sleep {} && tc qdisc del dev eth{} root && {}"

# regex to match iproute2 `tc` specifications
TC_PERCENTAGE_REGEX = "\A([0-9]{1,2}|100)%\Z"
TC_TIME_REGEX = "\A[0-9]+(s|ms|us)\Z"
TC_RATE_REGEX = "\A[0-9]+(bit|kbit|mbit|gbit|tbit|bps|kbps|mbps|gbps|tbps)\Z"

# timers
TIMER_EXPECTED_FIELDS = ["option", "start", "newValue"]
TIMER_OPTIONAL_FIELDS = ["duration"]
TIMER_TIME_REGEX = "\A(?=.)(([0-9]*)(\.([0-9]+))?)\Z"

# --------------------------------------- HTTPS -----------------------------------------------

PATH_CERTIFICATE = "/server.crt"
PATH_KEY_FILE = "/server.key"

# --------------------------------------- DOCKER ENGINE -----------------------------------------------

DE_GET_VERSION = "docker --version"

# --------------------------------------- KUBERNETES -----------------------------------------------

K8S_DEFAULT_NODE_PORT_MIN = 30000
K8S_DEFAULT_NODE_PORT_MAX = 32767
K8S_EXPORT_FOLDER = "./k8s_configs" # do NOT put a '/' at the end

K8S_GET_SERVICE_IP_RANGE_CMD = "kubectl cluster-info dump | grep -m 1 service-cluster-ip-range | tr -d '[:space:]' | grep -o '=.*' | cut -c 2- | rev | cut -c 3- | rev"
K8S_GET_PODS_IP_RANGE_CMD = "kubectl cluster-info dump | grep -m 1 cluster-cidr | tr -d '[:space:]' | grep -o '=.*' | cut -c 2- | rev | cut -c 3- | rev"
K8S_CHECK_MESHNET = "kubectl get daemonset -n meshnet | awk '{print $2,$3,$4,$5}'"
K8S_KUBECTL_CHECK_EXEC = "which kubectl"
K8S_KUBECTL_GET_CONFIG = "kubectl config view"
K8S_KUBECTL_GET_CLUSTER_INFO = "kubectl cluster-info"
K8S_KUBECTL_GET_NODES_COUNT = "kubectl get nodes | wc -l"

K8S_JAEGER_HOSTNAME = "jaeger-pod.jaeger-svc.default.svc.cluster.local"
K8S_COLLECTOR_HOSTNAME = "ioam-collector-pod.ioam-collector-svc.default.svc.cluster.local:7123"

# --------------------------------------- ASCII ART -----------------------------------------------

ASCII_ART = r"""
  __  __  _____ _______ _____
 |  \/  |/ ____|__   __/ ____|
 | \  / | (___    | | | |  __
 | |\/| |\___ \   | | | | |_ |
 | |  | |____) |  | | | |__| |
 |_|  |_|_____/   |_|  \_____|
"""
