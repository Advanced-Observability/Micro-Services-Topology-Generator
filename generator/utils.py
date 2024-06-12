'''
Utilities for the generator of docker compose and
kubernetes configuration files.
'''

import sys, os, ipaddress, re, argparse, subprocess

import kubernetes
from constants import *

def check_arguments() -> str:
    '''
    Check the arguments and return the name of the config file.
    If invalid arguments, exit the program.
    '''

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=DEFAULT_CONFIG_FILE, required=False, help=f"Path to config file (default = {DEFAULT_CONFIG_FILE})")
    parser.add_argument("--kubernetes", action='store_true', help="Generate Kubernetes configuration files")
    parser.add_argument("--ip", required=True, choices=[4, 6], type=int, help="IP version")
    parser.add_argument("--https", action="store_true", help="Use HTTPS for communication")
    parser.add_argument("--jaeger", action='store_true', help="Enable Jaeger")
    parser.add_argument("--ioam", action="store_true", help="Enable only IOAM (no CLT)")
    parser.add_argument("--clt", action='store_true', help="Enable CLT")
    # debug flags
    parser.add_argument("--time", action='store_true', help="Show the time in nanoseconds to generate the architecture")
    parser.add_argument("--debug", action='store_true', help="Show internal state")
    
    args = parser.parse_args()

    if args.ip == 4:
        print_info("Generating architecture with IPv4")
        os.environ[IP_VERSION_ENV] = "4"
    elif args.ip == 6:
        print_info("Generating architecture with IPv6")
        os.environ[IP_VERSION_ENV] = "6"
    
    if args.jaeger:
        print_info("Generating architecture with Jaeger")
        os.environ[JAEGER_ENABLE_ENV] = "True"
    else:
        print_info("Generating architecture without Jaeger")
        os.environ[JAEGER_ENABLE_ENV] = "False"

    if args.ioam:
        print_info("Generating architecture with IOAM")
        os.environ[IOAM_ENABLE_ENV] = "1"
        # counter intuitive - used to generate with ioam
        # clt will not be enable inside the microservices
        os.environ[JAEGER_ENABLE_ENV] = "1"
        os.environ[CLT_ENABLE_ENV] = "1"
    else:
        os.environ[IOAM_ENABLE_ENV] = "0"
    
    if args.clt:
        print_info("Generating architecture with CLT")
        os.environ[CLT_ENABLE_ENV] = "1"
        if args.ip == 4:
            print_error("CLT requires IPv6!")
            sys.exit(1)
        if not args.jaeger:
            print_error("CLT requires Jaeger!")
            sys.exit(1)
    else:
        print_info("Generating architecture without CLT")
        os.environ[CLT_ENABLE_ENV] = "0"

    if args.debug:
        print_info("Generating with debug mode")
        os.environ[DEBUG_VAR_ENV] = "True"
    else:
        os.environ[DEBUG_VAR_ENV] = "False"

    if args.kubernetes:
        print_info("Generating configurations for Kubernetes:")
        os.environ[OUTPUT_FORMAT_ENV] = K8S_OUT_ENV
        if not kubernetes.Kubernetes.check_kubectl():
            raise RuntimeError("Issue(s) with K8S cluster.")
        print_info(f"\t- IP range for services: {kubernetes.Kubernetes.get_service_ip_range()}")
        print_info(f"\t- IP range for pods: {kubernetes.Kubernetes.get_pod_ip_range()}")
        print_info(f"\t- Number of nodes in cluster: {kubernetes.Kubernetes.get_nb_nodes()}")
        if not kubernetes.Kubernetes.check_meshnet_cni():
            raise RuntimeError("Meshnet CNI is not properly installed on the cluster.")
    else:
        print_info("Generating configuration for Docker Compose")
        os.environ[OUTPUT_FORMAT_ENV] = COMPOSE_OUT_ENV

    if args.https:
        print_info("Generating architecture with HTTPS")
        os.environ[HTTP_VER_ENV] = "https"
    else:
        print_info("Generating architecture with HTTP")
        os.environ[HTTP_VER_ENV] = "http"

    return args.config

def check_docker_engine_version():
    """
    Check version of Docker Engine running on host
    due to issues with sysctl and Docker Engine == 26.0.0.
    """

    versionCheck = subprocess.run(DE_GET_VERSION, shell=True, stdout=subprocess.PIPE)

    if versionCheck.returncode != 0:
        raise RuntimeError("Could not get version of Docker Engine")

    version = versionCheck.stdout.decode("utf-8").strip()

    vNumber = re.search("\d+.\d+.\d+", version).group(0)
    vNumbers = vNumber.split(".")
    if len(vNumbers) != 3:
        raise RuntimeError("Unexpected format of docker engine version number")

    # only version 26.0.0 is problematic
    if not (int(vNumbers[0]) == 26 and int(vNumbers[1]) == 0 and int(vNumbers[2]) == 0):
        os.environ[DE_ENV_SYSCTL] = "1"
        return

    print_warning("Docker Engine 26 introduces a modification that prevents configuration of interfaces during container creation with sysctl.")
    print_warning("See issue https://github.com/moby/moby/issues/47619")
    print_warning("See issue https://github.com/moby/moby/issues/47639")
    print_warning("Fixed in commit https://github.com/moby/moby/commit/fc14d8f9329acd938e22afd0ed4edcfa71dfc40a")
    print_warning("Details in merge request https://github.com/moby/moby/pull/47646")
    print_warning("This may lead to unexpected behavior!")
    print_warning("It has been patched in v26.0.1 of the Docker Engine.")
    print_warning("You should consider updating to v26.0.1 or a newer version.")

    os.environ[DE_ENV_SYSCTL] = "0"
    return

def output_is_compose() -> bool:
    """True if output is Docker Compose."""
    return os.environ[OUTPUT_FORMAT_ENV] == COMPOSE_OUT_ENV

def output_is_k8s() -> bool:
    """True if output is Kubernetes."""
    return os.environ[OUTPUT_FORMAT_ENV] == K8S_OUT_ENV

def debug_mode_is_on() -> bool:
    """True if debug mode is on."""
    return os.environ[DEBUG_VAR_ENV] == "True"

def is_measuring_time() -> bool:
    """True if we are measuring the time."""
    return "--time" in sys.argv

def is_using_clt() -> bool:
    """True if the architecture is using CLT."""
    return os.environ[CLT_ENABLE_ENV] == "1"

def is_using_jaeger() -> bool:
    """True if the architecture includes Jaeger."""
    return os.environ[JAEGER_ENABLE_ENV] == "True"

def topology_is_ipv4() -> bool:
    """True if the topology is using IPv4."""
    return os.environ[IP_VERSION_ENV] == "4"

def topology_is_ipv6() -> bool:
    """True if the topology is using IPv6."""
    return os.environ[IP_VERSION_ENV] == "6"

def topology_is_http() -> bool:
    """True if the topology is using HTTP."""
    return os.environ[HTTP_VER_ENV] == "http"

def topology_is_https() -> bool:
    """True if the topology is using HTTPS."""
    return os.environ[HTTP_VER_ENV] == "https"

def generate_sysctls() -> bool:
    """True if need to generate interface dependant sysctls."""
    return os.environ[DE_ENV_SYSCTL] == "1"

def convert_network_id_to_ip6_network(prefix : int) -> ipaddress.IPv6Network:
    '''
    Convert the given network `prefix` to IPv6 network.
    Assumption: every network as a prefix of 64 bits.
    Thus, maximum 2^64 - 1 networks can be generated and 2^64 - 2 services.
    '''
    string  = "{0:b}".format(prefix)
    remaining = 128 - len(string) - 64
    string = '0' * remaining + string + '0'*64

    return ipaddress.IPv6Network((int(string, 2), 64))

def convert_network_id_to_ip4_network(prefix : int) -> ipaddress.IPv4Network:
    '''
    Convert the given network `prefix` to IPv4 network.
    Assumption: every network as a prefix of 22 bits.
    Thus, maximum 4,194,303 (2^22 - 1) networks can be generated and
    1,022 services.
    '''
    string = "{0:b}".format(prefix)
    remaining = 32 - len(string) - 10
    string = '0' * remaining + string + '0' * 10

    return ipaddress.IPv4Network((int(string, 2), 22))

def convert_network_id_to_k8s_ipv4(prefix : int) -> ipaddress.IPv4Network:
    """
    Conver the given network `prefix` to IPv4 network.
    Assumption: every network is a /30 subnet of 10.0.0.0/8.
    Thus, maximum 2^(32-8-2) networks.
    """
    string = "{0:b}".format(prefix)
    remaining = 32 - 8 - len(string) - 2
    string = '00001010' + '0' * remaining + string + '0' * 2

    return ipaddress.IPv4Network((int(string, 2), 30))

def convert_network_id_to_k8s_ipv6(prefix : int) -> ipaddress.IPv6Network:
    """
    Conver the given network `prefix` to IPv6 network.
    Assumption: every network is a /124 subnet of fd00::/8 (ipv6 unique local address).
    Thus, maximum 2^(128-8-4) networks.
    """
    string = "{0:b}".format(prefix)
    remaining = 128 - 8 - len(string) - 4
    string = '11111101' + '0' * remaining + string + '0' * 4

    return ipaddress.IPv6Network((int(string, 2), 124))

def match_tc_percent(toCheck: str) -> bool:
    '''
    Check if the given string matches the specifications for a percentage
    for the command `tc` from iproute2.
    '''

    return True if re.search(TC_PERCENTAGE_REGEX, toCheck) is not None else False

def match_tc_rate(toCheck: str) -> bool:
    '''
    Check if the given string matches the specifications for a rate
    for the command `tc` from iproute2.
    '''

    return True if re.search(TC_RATE_REGEX, toCheck) is not None else False

def match_tc_time(toCheck: str) -> bool:
    '''
    Check if the given string matches the specifications for a time
    for the command `tc` from iproute2.
    '''

    return True if re.search(TC_TIME_REGEX, toCheck) is not None else False

def filterCmd(option : str, cmd : str, interface : str) -> bool:
    '''Check if the given `cmd` can be used to modify `option` on given `interface`.'''

    if option == "mtu" and "mtu" in cmd and interface in cmd:
            return True
    elif option == "buffer_size" and "txqueuelen" in cmd and interface in cmd:
            return True
    elif option not in ["mtu", "buffer_size"] and "qdisc" in cmd and interface in cmd:
            return True
    return False

def print_success(text: str):
    print(f"\033[92m{text}\033[0m")

def print_error(text: str):
    print(f"\033[91m[ERROR] {text}\033[0m")

def print_warning(text: str):
    print(f"\033[93m[WARNING] {text}\033[0m")

def print_info(text: str):
    print(f"\033[94m[INFO] {text}\033[0m")
