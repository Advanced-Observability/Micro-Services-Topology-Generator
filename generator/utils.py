"""
Utilities for MSTG.
"""

import os
import re
import sys
import argparse
import bitarray
import ipaddress
import subprocess
import bitarray.util

import constants
import kubernetes


def check_arguments(args) -> str:
    '''
    Check the arguments and return the name of the config file.
    If invalid arguments, exit the program.
    '''

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default=constants.DEFAULT_CONFIG_FILE,
        required=False,
        help=f"Path to config file (default = {constants.DEFAULT_CONFIG_FILE})"
    )
    parser.add_argument(
        "--kubernetes",
        action='store_true',
        help="Generate Kubernetes configuration files"
    )
    parser.add_argument("--ip", required=True, choices=[4, 6], type=int, help="IP version")
    parser.add_argument("--https", action="store_true", help="Use HTTPS for communication")
    parser.add_argument("--jaeger", action='store_true', help="Enable Jaeger")
    parser.add_argument("--ioam", action="store_true", help="Enable only IOAM (no CLT)")
    parser.add_argument("--clt", action='store_true', help="Enable CLT")
    # debug flags
    parser.add_argument(
        "--time",
        action='store_true',
        help="Show the time in nanoseconds to generate the architecture"
    )
    parser.add_argument("--debug", action='store_true', help="Show internal state")

    args = parser.parse_args(args)

    if args.ip == 4:
        print_info("Generating architecture with IPv4")
        os.environ[constants.IP_VERSION_ENV] = "4"
    elif args.ip == 6:
        print_info("Generating architecture with IPv6")
        os.environ[constants.IP_VERSION_ENV] = "6"

    if args.jaeger:
        print_info("Generating architecture with Jaeger")
        os.environ[constants.JAEGER_ENABLE_ENV] = "True"
    else:
        print_info("Generating architecture without Jaeger")
        os.environ[constants.JAEGER_ENABLE_ENV] = "False"

    if args.ioam:
        if args.ip == 4:
            print_error("IOAM requires IPv6!")
            sys.exit(1)
        print_info("Generating architecture with IOAM (without CLT)")
        os.environ[constants.IOAM_ENABLE_ENV] = "1"
    else:
        os.environ[constants.IOAM_ENABLE_ENV] = "0"

    if args.clt:
        print_info("Generating architecture with CLT")
        os.environ[constants.CLT_ENABLE_ENV] = "1"
        if args.ip == 4:
            print_error("CLT requires IPv6!")
            sys.exit(1)
        if not args.jaeger:
            print_error("CLT requires Jaeger!")
            sys.exit(1)
    else:
        print_info("Generating architecture without CLT")
        os.environ[constants.CLT_ENABLE_ENV] = "0"

    if args.debug:
        print_info("Generating with debug mode")
        os.environ[constants.DEBUG_VAR_ENV] = "True"
    else:
        os.environ[constants.DEBUG_VAR_ENV] = "False"

    if args.kubernetes:
        print_info("Generating configurations for Kubernetes:")
        os.environ[constants.OUTPUT_FORMAT_ENV] = constants.K8S_OUT_ENV
        if not kubernetes.Kubernetes.check_kubectl():
            raise RuntimeError("Issue(s) with K8S cluster.")
        print_info(f"\t- IP range for services: {kubernetes.Kubernetes.get_service_ip_range()}")
        print_info(f"\t- IP range for pods: {kubernetes.Kubernetes.get_pod_ip_range()}")
        print_info(f"\t- Number of nodes in cluster: {kubernetes.Kubernetes.get_nb_nodes()}")
        if not kubernetes.Kubernetes.check_meshnet_cni():
            raise RuntimeError("Meshnet CNI is not properly installed on the cluster.")
    else:
        print_info("Generating configuration for Docker Compose")
        os.environ[constants.OUTPUT_FORMAT_ENV] = constants.COMPOSE_OUT_ENV

    if args.https:
        print_info("Generating architecture with HTTPS")
        os.environ[constants.HTTP_VER_ENV] = "https"
    else:
        print_info("Generating architecture with HTTP")
        os.environ[constants.HTTP_VER_ENV] = "http"

    return args.config


def get_interface_name(iface: int, name: str) -> str:
    """Get the name of an interface."""
    if output_is_k8s():
        return f"eth{iface}"

    return f"eth{iface}_{name}"


def generate_command(cmd: str, entity: str, background=False):
    """
    Generate command to execute `cmd`.

    :param cmd: Command to execute.
    :param entity: Entity in which to execute.
    :param background: Execute command in background.
    """

    if output_is_compose() and background:
        return constants.DOCKER_CMD_BACKGROUND.format(entity, cmd)
    if output_is_compose():
        return constants.DOCKER_CMD.format(entity, cmd)
    return cmd


def export_single_command(cmd: str):
    """Export a given single command `cmd`."""

    # sleep to be sure that interfaces had time to be configured properly by meshnet cni
    return f"({cmd})" if output_is_compose() else f"(sleep 20 && {cmd})"


def combine_commands(cmds: list[str], separator="&") -> str:
    """
    Combine all commands in a single one.

    :param cmds: List of commands to combine.
    :param separator: Separator to use between the commands.
    """
    return separator.join(f" {export_single_command(cmd)} " for cmd in cmds)


def output_is_compose() -> bool:
    """True if output is Docker Compose."""
    return os.environ[constants.OUTPUT_FORMAT_ENV] == constants.COMPOSE_OUT_ENV


def output_is_k8s() -> bool:
    """True if output is Kubernetes."""
    return os.environ[constants.OUTPUT_FORMAT_ENV] == constants.K8S_OUT_ENV


def debug_mode_is_on() -> bool:
    """True if debug mode is on."""
    return os.environ[constants.DEBUG_VAR_ENV] == "True"


def is_measuring_time() -> bool:
    """True if we are measuring the time."""
    return "--time" in sys.argv


def is_using_ioam_only() -> bool:
    """True if we are using IOAM without CLT."""
    return os.environ[constants.IOAM_ENABLE_ENV] == "1"


def is_using_clt() -> bool:
    """True if the architecture is using CLT."""
    return os.environ[constants.CLT_ENABLE_ENV] == "1"


def is_using_jaeger() -> bool:
    """True if the architecture includes Jaeger."""
    return os.environ[constants.JAEGER_ENABLE_ENV] == "True"


def topology_is_ipv4() -> bool:
    """True if the topology is using IPv4."""
    return os.environ[constants.IP_VERSION_ENV] == "4"


def topology_is_ipv6() -> bool:
    """True if the topology is using IPv6."""
    return os.environ[constants.IP_VERSION_ENV] == "6"


def topology_is_http() -> bool:
    """True if the topology is using HTTP."""
    return os.environ[constants.HTTP_VER_ENV] == "http"


def topology_is_https() -> bool:
    """True if the topology is using HTTPS."""
    return os.environ[constants.HTTP_VER_ENV] == "https"


def convert_net_id_to_mac_addresses(identifier: int) -> list[str]:
    '''Convert the given network `identifier` to 2 mac addresses.'''

    # convert to hex without 0x
    prefix = hex(identifier)[2:]
    size = len(prefix)

    # ensure 10 bytes of prefix and convert to str
    prefix = '0' * (10 - size) + prefix
    mac_prefix = ':'.join(prefix[i:i+2] for i in range(0, len(prefix), 2))

    # use addr 01 and 02 of calculated prefix
    macs = [f'{mac_prefix}:01', f'{mac_prefix}:02']
    return macs


def convert_net_id_to_ip6_net(prefix: int) -> ipaddress.IPv6Network:
    '''
    Convert the given network `prefix` to IPv6 network.
    Assumption: every network as a prefix of 64 bits.
    Thus, maximum 2^64 - 1 networks can be generated and 2^64 - 2 services.
    '''
    string = bin(prefix)[2:]
    remaining = 128 - len(string) - 64
    string = '0' * remaining + string + '0' * 64

    return ipaddress.IPv6Network((int(string, 2), 64))


def convert_net_id_to_ip4_net(prefix: int) -> ipaddress.IPv4Network:
    '''
    Convert the given network `prefix` to IPv4 network.
    Assumption: every network as a prefix of 22 bits.
    Thus, maximum 4,194,303 (2^22 - 1) networks can be generated and
    1,022 services.
    '''
    string = bin(prefix)[2:]
    remaining = 32 - len(string) - 10
    string = '0' * remaining + string + '0' * 10

    return ipaddress.IPv4Network((int(string, 2), 22))


def convert_net_id_to_k8s_ipv4(prefix: int) -> ipaddress.IPv4Network:
    """
    Conver the given network `prefix` to IPv4 network.
    Assumption: every network is a /30 subnet of 10.0.0.0/8.
    Thus, maximum 2^(32-8-2) networks.
    """
    string = bin(prefix)[2:]
    remaining = 32 - 8 - len(string) - 2
    string = '00001010' + '0' * remaining + string + '0' * 2

    return ipaddress.IPv4Network((int(string, 2), 30))


def convert_net_id_to_k8s_ipv6(prefix: int) -> ipaddress.IPv6Network:
    """
    Conver the given network `prefix` to IPv6 network.
    Assumption: every network is a /124 subnet of fd00::/8 (ipv6 unique local address).
    Thus, maximum 2^(128-8-4) networks.
    """
    string = bin(prefix)[2:]
    remaining = 128 - 8 - len(string) - 4
    string = '11111101' + '0' * remaining + string + '0' * 4

    return ipaddress.IPv6Network((int(string, 2), 124))


def match_tc_percent(to_check: str) -> bool:
    '''
    Check if the given string matches the specifications for a percentage
    for the command `tc` from iproute2.
    '''

    return re.search(constants.TC_PERCENTAGE_REGEX, to_check) is not None


def match_tc_rate(to_check: str) -> bool:
    '''
    Check if the given string matches the specifications for a rate
    for the command `tc` from iproute2.
    '''

    return re.search(constants.TC_RATE_REGEX, to_check) is not None


def match_tc_time(to_check: str) -> bool:
    '''
    Check if the given string matches the specifications for a time
    for the command `tc` from iproute2.
    '''

    return re.search(constants.TC_TIME_REGEX, to_check) is not None


def filter_cmd(option: str, cmd: str, interface: str) -> bool:
    '''Check if the given `cmd` can be used to modify `option` on given `interface`.'''

    if option == "mtu" and "mtu" in cmd and interface in cmd:
        return True
    if option == "buffer_size" and "txqueuelen" in cmd and interface in cmd:
        return True
    if option not in ["mtu", "buffer_size"] and "qdisc" in cmd and interface in cmd:
        return True
    return False


def build_ioam_trace_type() -> str:
    """Generate ioam trace type as hex based on configuration."""
    trace_type = bitarray.bitarray(24)

    if constants.IOAM_BIT0:
        trace_type[0] = 1

    if constants.IOAM_BIT1:
        trace_type[1] = 1

    if constants.IOAM_BIT2:
        trace_type[2] = 1

    if constants.IOAM_BIT3:
        trace_type[3] = 1

    if constants.IOAM_BIT5:
        trace_type[5] = 1

    if constants.IOAM_BIT6:
        trace_type[6] = 1

    if constants.IOAM_BIT8:
        trace_type[8] = 1

    if constants.IOAM_BIT9:
        trace_type[9] = 1

    if constants.IOAM_BIT10:
        trace_type[10] = 1

    if constants.IOAM_BIT22:
        trace_type[22] = 1

    return bitarray.util.ba2hex(trace_type)


def size_ioam_trace() -> int:
    """Calculate size of ioam trace based on ioam trace type for a single node."""

    size = 0

    if constants.IOAM_BIT0:
        size += 4

    if constants.IOAM_BIT1:
        size += 4

    if constants.IOAM_BIT2:
        size += 4

    if constants.IOAM_BIT3:
        size += 4

    if constants.IOAM_BIT5:
        size += 4

    if constants.IOAM_BIT6:
        size += 4

    if constants.IOAM_BIT8:
        size += 8

    if constants.IOAM_BIT9:
        size += 8

    if constants.IOAM_BIT10:
        size += 8

    if constants.IOAM_BIT22:
        # size of OSS is not included
        pass

    return size


def check_ovs_kernel_module() -> bool:
    '''Check whether the kernel module for OVS is properly loaded.'''

    res = subprocess.run(constants.OVS_CHECK_CMD, shell=True, stdout=subprocess.PIPE, check=False)

    if "openvswitch" not in res.stdout.decode('utf-8').strip():
        return False

    return res.returncode == 0


def print_success(text: str):
    '''Print a success text.'''
    print(f"\033[92m{text}\033[0m")


def print_error(text: str):
    '''Print an error text.'''
    print(f"\033[91m[ERROR] {text}\033[0m")


def print_warning(text: str):
    '''Print a warning text.'''
    print(f"\033[93m[WARNING] {text}\033[0m")


def print_info(text: str):
    '''Print an info text.'''
    print(f"\033[94m[INFO] {text}\033[0m")
