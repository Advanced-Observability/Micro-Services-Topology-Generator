"""
Configuration parser for MSTG.
"""

import re
from string import printable
import yaml
import networkx as nx
from typing import Any

import utils
import constants


def parse_config(filename: str) -> Any:
    """
    Parse the config in the file with the given `filename`.
    If unable to open file or parse yaml, crash the program.
    """

    try:
        with open(filename, "r", encoding="utf-8") as f:
            # will check that names are unique
            config = yaml.load(f, Loader=UniqueKeyLoader)
            return config
    except OSError as err:
        raise RuntimeError("Unable to open the given config file") from err
    except yaml.YAMLError as err:
        raise RuntimeError("Unable to parse yaml in file") from err
    except ValueError as err:
        raise RuntimeError(err) from err


def get_entity(config, name: str):
    """
    Return the entity with the given `name` from `config`.
    If not found, return None.
    """
    for e in config:
        if e == name:
            return config[e]

    return None


def check_config(config) -> bool:
    """
    Check if the given `config` is valid.
    True if the config is valid. Else, false.
    """

    # Check the common fields
    for entity in config:
        if not check_common_fields(entity, config[entity]):
            return False

    utils.print_info("passing check common fields")
    ovs_module_checked = False

    # Check the specific fields for each type
    for entity in config:
        entity_type = config[entity]["type"]
        if entity_type == "service":
            if not check_service_fields(entity, config[entity]):
                return False
        elif entity_type == "router":
            if not check_router_fields(entity, config[entity]):
                return False
        elif entity_type == "external":
            if not check_external_fields(entity, config[entity]):
                return False
        elif entity_type == "firewall":
            if not check_firewall_fields(entity, config[entity]):
                return False
        elif entity_type == "switch":
            if not ovs_module_checked:
                if not utils.check_ovs_kernel_module():
                    raise RuntimeError("Missing openvswitch kernel module!")
                ovs_module_checked = True
            if utils.output_is_k8s():
                raise RuntimeError("Switches cannot be exported to Kubernetes")
            if not check_switch_fields(entity, config[entity]):
                return False
        else:
            utils.print_error(f"Entity {entity} has unknown type {entity_type}")
            return False

    utils.print_info("passing check entity-specific fields")

    # Check that all the connections are possible
    if not check_connectivity(config):
        return False

    utils.print_info("passing check connections")

    # Check cycles in graph
    if not check_no_cycles(config):
        utils.print_error("Cannot have cycles in the architecture")
        return False
    utils.print_info("passing check no cycles")

    # Check that all the ports are unique
    if not check_unique_ports(config):
        utils.print_error("Exposed ports need to be unique")
        return False

    utils.print_info("passing check unique ports")

    return True


def check_common_fields(name: str, entity) -> bool:
    """
    Check if the given `entity` with the given `name` has all the common fields.
    True if the given entity contains all the common fields. Else, false.
    """

    for field in constants.MANDATORY_COMMON_FIELDS:
        if field not in entity:
            utils.print_error(f"Entity {name} missing {field} field")
            return False

    if entity["type"] not in constants.KNOWN_TYPES:
        utils.print_error(f"Entity {name} has unknown type " + entity["type"])
        return False

    return True


def check_external_fields(name: str, entity) -> bool:
    """
    Check if the given `entity` with the given `name` has all the fields for an
    externale container.
    True if the given entity contains all the external fields. Else, false.
    """

    for field in constants.EXTERNAL_FIELDS:
        if field not in entity:
            utils.print_error(f"Entity {name} missing {field} field")
            return False

    if not check_connection_specifications(name, entity, entity["connections"]):
        return False

    return True


def check_router_fields(name: str, entity) -> bool:
    """
    Check if the given `entity` with the given `name` has all the fields for a router.
    True if the given entity contains all the router fields. Else, false.
    """

    for field in constants.ROUTER_FIELDS:
        if field not in entity:
            utils.print_error(f"Router {name} missing {field} field")
            return False

    if not check_connection_specifications(name, entity, entity["neighbors"]):
        return False

    return True


def check_service_fields(name: str, entity) -> bool:
    """
    Check if the given `entity` with the given `name` has all the fields for a service.
    True if the given entity contains all the service fields. Else, false.
    """

    # checking if all required fields for a service are present
    for field in constants.SERVICE_FIELDS:
        if field not in entity:
            utils.print_error(f"Entity {name} missing {field} field")
            return False

    # check endpoints
    for endpoint in entity["endpoints"]:
        # check if contains all expected fields
        for f in constants.SERVICE_ENDPOINT_FIELDS:
            if f not in endpoint:
                utils.print_error(
                    f"Endpoint {endpoint} of entity {name} missing field {f}"
                )
                return False

        # check the specified connections if any
        if "connections" in endpoint and endpoint["connections"] is not None:
            if not check_connection_specifications(
                name, entity, endpoint["connections"]
            ):
                return False

    return True


def check_firewall_fields(name: str, entity) -> bool:
    """
    Check if the given `entity` with the given `name` has all the fields
    for a firewall.
    True if the given entity contains all the firewall fields. Else, False.
    """

    for required in constants.FIREWALL_FIELDS:
        if required not in entity:
            utils.print_error(f"Firewall {name} missing field {required}")
            return False

    if entity["default"].lower() not in ("accept", "drop"):
        raise RuntimeError(f'Firewall {name} default policy must be "accept" or "drop"')

    if "rules" in entity and entity["rules"] is not None:
        for rule in entity["rules"]:
            for field in rule:
                if field not in constants.FIREWALL_RULES_FIELDS:
                    utils.print_error(
                        f"Rule {rule} of firewall {name} has unexpected field {field}"
                    )
            if "custom" in rule and len(rule) != 1:
                raise RuntimeError(
                    f"Rule {rule} for firewall {name} cannot have other fields with custom rule"
                )

    if not check_connection_specifications(name, entity, entity["neighbors"]):
        return False

    return True


def check_switch_fields(name: str, entity) -> bool:
    """
    Check if the given `entity` with the given `name` has all the fields
    for a switch.
    True if the given entity contains all the firewall fields. Else, false.
    """

    for required in constants.SWITCH_FIELDS:
        if required not in entity:
            utils.print_error(f"Switch {name} missing field {required}")
            return False

    if not check_connection_specifications(name, entity, entity["neighbors"]):
        return False

    return True


def check_impairments(entity, connection, field) -> bool:
    """Check impariments specified in connections."""

    if not check_single_impairment(field, connection[field]):
        utils.print_error(f"Issue with connection {connection} of {entity}")
        return False

    return True


def check_single_impairment(name, value) -> bool:
    """Check given impairment."""

    if name not in constants.CONNECTION_IMPAIRMENTS:
        return True

    if name == "mtu" and not isinstance(value, int):
        utils.print_error("MTU option must be an int")
        return False
    if name == "buffer_size" and not isinstance(value, int):
        utils.print_error("Buffer size option must be an int")
        return False
    if name == "rate" and not utils.match_tc_rate(value):
        utils.print_error("Rate option must be a rate")
        return False
    if name in ["delay", "jitter"] and not utils.match_tc_time(value):
        utils.print_error(f"{name} option must be a time")
        return False
    if name in [
        "loss",
        "corrupt",
        "duplicate",
        "reorder",
    ] and not utils.match_tc_percent(value):
        utils.print_error(f"{name} option must be a percentage between 0% and 100%")
        return False
    return True


def check_timers(entity, connection, field) -> bool:
    """Check timers in connections."""

    if field != "timers" or connection["timers"] is None:
        return True

    for timer in connection["timers"]:
        # check if it has all fields
        for expected_field in constants.TIMER_EXPECTED_FIELDS:
            if expected_field not in timer:
                utils.print_error(
                    f"Missing field {expected_field} for timer {timer} for connection {connection} of {entity}"
                )
                return False

            if (
                expected_field == "option"
                and timer[expected_field] not in constants.CONNECTION_IMPAIRMENTS
            ):
                utils.print_error(
                    f"Specified option {timer[expected_field]} for "
                    f"timer {timer} of connection {connection} for {entity} is not an impairment"
                )
                return False

            if expected_field in ("start", "duration"):
                if (
                    re.search(constants.TIMER_TIME_REGEX, str(timer[expected_field]))
                    is None
                ):
                    utils.print_error(
                        f"Start must be specified as an integer/float "
                        f"amount of seconds for timer {timer} of connection {connection} for {entity}"
                    )
                    return False

        # check given values
        if not check_single_impairment(timer["option"], timer["newValue"]):
            utils.print_error(
                f"Option {timer['option']} for timer {timer} of "
                f"connection {connection} for {entity} has unexpected format"
            )
            return False

    return True


def check_connection_specifications(name: str, entity, connections: list) -> bool:
    """
    Check the `connections` specified for the `entity` with the given `name`.
    Return True if the connections respect the specifications. Else, False.
    """

    entity_type = entity["type"]

    if entity_type == "service":
        mandatory_list = constants.CONNECTION_SERVICE_MANDATORY_FIELDS
    elif entity_type == "router":
        mandatory_list = constants.CONNECTION_ROUTER_MANDATORY_FIELDS
    elif entity_type == "external":
        mandatory_list = constants.CONNECTION_EXTERNAL_MANDATORY_FIELDS
    elif entity_type == "firewall":
        mandatory_list = constants.CONNECTION_FIREWALL_MANDATORY_FIELDS
    elif entity_type == "switch":
        mandatory_list = constants.CONNECTION_SW_MANDATORY_FIELDS
    else:
        utils.print_error(f"Entity {entity} has unknown type {entity_type}")
        return False

    for connection in connections:
        for mandatory in mandatory_list:
            if mandatory not in connection:
                utils.print_error(
                    f"Entity {name} missing field {mandatory} for connection {connection}"
                )
                return False

        if isinstance(connection, dict):
            for field in connection:
                if (
                    field not in constants.CONNECTION_OPTIONAL_FIELDS
                    and field not in mandatory_list
                ):
                    utils.print_error(
                        f"Entity {name} has unexpected field {field} for connection {connection}"
                    )
                    return False

            # Check all impairments
            if not check_impairments(entity, connection, field):
                return False

            if not check_timers(entity, connection, field):
                return False

    return True


def check_connectivity(config) -> bool:
    """
    Check if the paths for the connections are possible or not.
    Return True if all the paths are possible. Else, False.
    """

    for entity in config:
        connections = extract_connections(config[entity])

        # verify each connection
        for connection in connections:
            if "->" in connection:  # connection is path
                hops = connection.split("->")

                for i, hop in enumerate(hops):
                    # check that hops in path exist
                    if get_entity(config, hop) is None:
                        utils.print_error(
                            f"Destination {hop} for connection {connection} "
                            f"of {entity} does not exist"
                        )
                        return False

                    # check that intermediary hops are routers, firewalls, or switches
                    if (
                        i != len(hops) - 1
                        and config[hop]["type"] not in constants.INTERMEDIARY_TYPES
                    ):
                        utils.print_error(
                            f"Intermediary hop {hop} of connection "
                            f"{connection} for {entity} is not an intermediary node"
                        )
                        return False

                    # check coherency with conn in intermediary hop
                    if i < len(hops) - 1:
                        conns = extract_connections(config[hop])
                        if hops[i + 1] not in conns:
                            utils.print_error(
                                f"Intermediary hop {hop} of connection "
                                f"{connection} for {entity} should specify one of {conns}"
                            )
                            return False

                # check that last node in path is a end host
                last = hops[len(hops) - 1]
                if config[last]["type"] not in constants.END_HOST_TYPES:
                    utils.print_error(
                        f"Last hop {last} in path {connection} for {entity} must "
                        f"be a end host"
                    )
                    return False

            else:  # connection is direct
                # check that destination exists
                if get_entity(config, connection) is None:
                    utils.print_error(
                        f"Connection {connection} for {entity} is to an entity that does not exists"
                    )
                    return False

                # check that destination is a service if the source is a service
                # a router can be connected to a router
                if (
                    config[entity]["type"] in constants.END_HOST_TYPES
                    and config[connection]["type"] not in constants.END_HOST_TYPES
                ):
                    utils.print_error(
                        f"Destination of connection {connection} for {entity} is not a end host."
                    )
                    return False

    return True


def check_no_cycles(config) -> bool:
    """
    Check if the given `config` contains no cycles.
    True, if no cycles. Else, false.
    """

    graph = build_directed_graph(config)

    try:
        cycle = nx.find_cycle(graph, orientation="original")
    except nx.exception.NetworkXNoCycle:
        return True
    return cycle is None


def check_unique_ports(config) -> bool:
    """
    Check that all exposed service ports in the `config` are unique and not
    used by telemetry services.
    True if ports are unique. Else, false.
    """
    ports: dict[int, Any] = {}

    for entity in config:
        if config[entity]["type"] in constants.INTERMEDIARY_TYPES:
            continue

        # Port exposed by default
        if "expose" in config[entity] and not config[entity]["expose"]:
            continue

        entity_ports = []
        if config[entity]["type"] == "service":
            entity_ports.append(config[entity]["port"])
        elif config[entity]["type"] == "external":
            entity_ports.extend(config[entity]["ports"])
        else:
            utils.print_error(
                f"Entity {entity} has unexpected type {config[entity]['type']}"
            )
            return False

        for port in entity_ports:
            if port in constants.TELEMETRY_PORTS:
                utils.print_error(
                    f"The port {port} is used for telemetry. Do not use it. Requested for {entity}."
                )
                return False
            if port in ports:
                utils.print_error(
                    f"This port is already used by {ports[port]}. Cannot assign to {entity}."
                )
                return False
            ports[port] = entity

    return True


def build_directed_graph(config) -> nx.DiGraph:
    """
    Return the directed graph representing the given `config`.
    """
    graph: nx.DiGraph = nx.DiGraph()

    for entity in config:
        graph.add_node(entity)

        # not parsing connections of switch on purpose
        if config[entity]["type"] == "switch":
            continue

        # add edges of node
        connections = extract_connections(config[entity])
        if connections is None:
            continue

        for connection in connections:
            if "->" in connection:  # connection is path
                conns = connection.split("->")
                graph.add_edge(entity, conns[0])
                # take entities in connnection by pair
                for i in range(len(conns) - 1):
                    graph.add_edge(conns[i], conns[i + 1])
            else:  # connection is direct
                graph.add_edge(entity, connection)

    return graph


def extract_connections(entity_config) -> list:
    """
    Extract the connections from the given `entity_config`.
    Return list of connections.
    """

    entity_type = entity_config["type"]

    if entity_type in ("router", "external", "firewall", "switch"):
        if "neighbors" in entity_config:
            conns = entity_config["neighbors"]
            if conns:
                if isinstance(conns[0], dict):
                    return [conn["hop"] for conn in conns]
                return conns if conns is not None else []
    elif entity_type == "service":
        connections = []
        for endpoint in entity_config["endpoints"]:
            if "connections" in endpoint and endpoint["connections"] is not None:
                return [conn["path"] for conn in endpoint["connections"]]
        return connections

    return []


# From https://gist.github.com/pypt/94d747fe5180851196eb
# Check that keys are unique when loading yaml
class UniqueKeyLoader(yaml.SafeLoader):
    """Load YAML with unique keys."""

    def construct_mapping(self, node, deep=False):
        mapping = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ValueError(
                    f"Names of entities must be unique. Found {key!r} more than once."
                )
            mapping.add(key)
        return super().construct_mapping(node, deep)
