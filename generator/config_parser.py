'''
Configuration parser for the generator of configuration files.
'''

import yaml, re, networkx as nx

from utils import *

def parse_config(filename : str) -> any:
    '''
    Parse the config in the file with the given `filename`.
    If unable to open file or parse yaml, crash the program.
    '''

    try:
        f = open(filename, 'r')
        # will check that names are unique
        config = yaml.load(f,Loader=UniqueKeyLoader)
        f.close()
        return config
    except OSError as err:
        raise RuntimeError("Unable to open the given config file: " + str(err))
    except yaml.YAMLError as err:
        f.close()
        raise RuntimeError("Unable to parse yaml in file: " + str(err))
    except ValueError as err:
        raise RuntimeError(err)

def get_entity(config, name : str):
    '''
    Return the entity with the given `name` from `config`.
    If not found, return None.
    '''
    for e in config:
        if e == name:
            return config[e]

    return None

def check_config(config) -> bool:
    '''
    Check if the given `config` is valid.
    True if the config is valid. Else, false.
    '''

    # Check the common fields
    valid = True
    for entity in config:
        if not check_common_fields(entity, config[entity]):
            valid = False

    # Allows to print all issues before crashing
    if not valid:
        return False

    print_info("passing check common fields")

    # Check the specific fields for each type
    valid = True
    for entity in config:
        if config[entity]['type'] == "service":
            if not check_service_fields(entity, config[entity]):
                valid = False
        elif config[entity]['type'] == "router":
            if not check_router_fields(entity, config[entity]):
                valid = False

    # Allows to print all issues before crashing
    if not valid:
        return False

    print_info("passing check service and router fields")

    # Check that all the connections are possible
    if not check_connectivity(config):
        return False

    print_info("passing check connections")

    # Check cycles in graph
    if not check_no_cycles(config):
        print_error("Cannot have cycles in the architecture")
        return False

    print_info("passing check no cycles")

    # Check that all the ports are unique
    if not check_unique_ports(config):
        print_error("Exposed ports need to be unique")
        return False

    print_info("passing check unique ports")

    return True

def check_common_fields(name : str, entity) -> bool:
    '''
    Check if the given `entity` with the given `name` has all the common fields.
    True if the given entity contains all the common fields. Else, false.
    '''

    valid = True

    if entity['type'] not in KNOWN_TYPES:
        print_error(f"Entity {name} has unknown type " + entity['type'])
        valid = False

    for field in MANDATORY_COMMON_FIELDS:
        if field not in entity:
            print_error(f"Entity {name} missing {field} field")
            valid = False

    return valid

def check_router_fields(name : str, entity) -> bool:
    '''
    Check if the given `entity` with the given `name` has all the fields for a router.
    True if the given entity contains all the router fields. Else, false.
    '''

    if "connections" not in entity or entity["connections"] == None:
        print_error(f"Router {name} must have some connections")
        return False

    if not check_connection_specifications(name, entity, entity["connections"]):
        return False

    return True

def check_service_fields(name : str, entity) -> bool:
    '''
    Check if the given `entity` with the given `name` has all the fields for a service.
    True if the given entity contains all the service fields. Else, false.
    '''
    valid = True

    # checking if all required fields for a service are present
    for field in SERVICE_FIELDS:
        if field not in entity:
            print_error(f"Entity {name} missing {field} field")
            valid = False

    # check endpoints
    for endpoint in entity["endpoints"]:
        # check if contains all expected fields
        for f in SERVICE_ENDPOINT_FIELDS:
            if f not in endpoint:
                print_error(f"Endpoint {endpoint} of entity {name} missing field {f}")
                valid = False

        # check the specified connections if any
        if "connections" in endpoint and endpoint["connections"] is not None:
            if not check_connection_specifications(name, entity, endpoint["connections"]):
                valid = False

    return valid

def check_connection_specifications(name : str, entity, connections : list) -> bool:
    """
    Check the `connections` specified for the `entity` with the given `name`.
    Return True if the connections respect the specifications. Else, False.
    """
    valid = True

    for connection in connections:
            if entity["type"] == "service":
                mandatoryList = CONNECTION_SERVICE_MANDATORY_FIELDS
            else:
                mandatoryList = CONNECTION_ROUTER_MANDATORY_FIELDS

            for mandatory in mandatoryList:
                if mandatory not in connection:
                    print_error(f"Service {name} missing field {mandatory} for connection {connection}")
                    valid = False

            for field in connection:
                if field not in CONNECTION_OPTIONAL_FIELDS and field not in CONNECTION_SERVICE_MANDATORY_FIELDS:
                    print_error(f"Service {name} has unexpected field {field} for connection {connection}")
                    valid = False

                # Check all impairments
                if field == "mtu" and type(connection[field]) is not int:
                    print_error(f"MTU option for connection {connection} of {entity} must be an int")
                    valid = False
                elif field == "buffer_size" and type(connection[field]) is not int:
                    print_error(f"Buffer size option for connection {connection} of {entity} must be an int")
                    valid = False
                elif field == "rate" and not match_tc_rate(connection[field]):
                    print_error(f"Rate option for connection {connection} of {entity} must be a rate")
                    valid = False
                elif field in ["delay", "jitter"] and not match_tc_time(connection[field]):
                    print_error(f"Option {field} for connection {connection} of {entity} must be a time")
                    valid = False
                elif field in ["loss", "corrupt", "duplicate", "reorder"] and not match_tc_percent:
                    print_error(f"Option {field} for connection {connection} of {entity} must be a percentage between 0% and 100%")
                    valid = False

                # check timers if any
                if field == "timers" and connection["timers"] is not None:
                    for timer in connection["timers"]:
                        # check if it has all fields
                        for expectedField in TIMER_EXPECTED_FIELDS:
                            if expectedField not in timer:
                                print_error(f"Missing field {expectedField} for timer {timer} for connection {connection} of {entity}")
                                valid = False

                            if expectedField == "option" and timer[expectedField] not in CONNECTION_IMPAIRMENTS:
                                print_error(f"Specified option {timer[expectedField]} for timer {timer} of connection {connection} for {entity} is not an impairment")
                                valid = False

                            if expectedField == "start" or expectedField == "duration":
                                if re.search(TIMER_TIME_REGEX, str(timer[expectedField])) is None:
                                    print_error(f"Start must be specified as an integer/float amount of seconds for timer {timer} of connection {connection} for {entity}")
                                    valid = False

                        # check given values
                        if timer["option"] in ["mtu", "buffer_size"] and type(timer["newValue"]) is not int:
                            print_error(f"Option {timer['option']} for timer {timer} of connection {connection} for {entity} must be specified as int")
                            valid = False
                        elif timer["option"] == "rate" and not match_tc_rate(timer["newValue"]):
                            print_error(f"Option {timer['option']} for timer {timer} of connection {connection} for {entity} must be specified as a rate")
                            valid = False
                        elif timer["option"] in ["delay", "jitter"] and not match_tc_time(timer["newValue"]):
                            print_error(f"Option {timer['option']} for timer {timer} of connection {connection} for {entity} must be specified as time")
                            valid = False
                        elif timer["option"] in ["loss", "corrupt", "duplicate", "reorder"] and not match_tc_percent(timer["newValue"]):
                            print_error(f"Option {timer['option']} for the timer {timer} of connection {connection} for {entity} must be specified as a percentage between 0% and 100%")
                            valid = False
    return valid

def check_connectivity(config) -> bool:
    '''
    Check if the paths for the connections are possible or not.
    Return True if all the paths are possible. Else, False.
    '''

    valid = True
    for entity in config:

        # extract connections
        connections = []
        if "connections" in entity and config[entity]["connections"] is not None:
            for connection in config[entity]["connections"]:
                connections.append(connection['path'])

        # verify each connection
        for connection in connections:
            if "->" in connection: # connection is path
                hops = connection.split("->")

                for hop in range(len(hops)):
                    # check that hops in path exists
                    if get_entity(config, hops[hop]) is None:
                        print_error("Destination {} for connection {} of {} does not exists".format(hops[hop], connection, entity))
                        valid = False

                    # check that intermediary hops are routers
                    if hop != len(hops) - 1 and config[hops[hop]]["type"] != "router":
                        print_error("Intermediary hop {} of connection {} for {} is not a router".format(hops[hop], connection, entity))
                        valid = False

                    # check coherency with conn in routers
                    if hop < len(hops) - 1:
                        conns = [conn["path"] for conn in config[hops[hop]]['connections']]
                        if hops[hop+1] not in conns:
                            print_error("Intermediary hop {} of connection {} for {} should specify {}".format(hops[hop], connection, entity, hops[hop+1]))
                            valid = False

                # check that last node in path is a service
                last = hops[len(hops) - 1]
                if config[last]["type"] != "service":
                    print_error(f"Last hop {last} in path {connection} for {entity} must be a service")
                    valid = False

            else: # connection is direct

                # check that destination exists
                if get_entity(config, connection) is None:
                    print_error(f"Connection {connection} for {entity} is to an entity that does not exists")
                    valid = False

                # check that destination is a service if the source is a service
                # a router can be connected to a router
                if config[entity]["type"] == "service" and config[connection]["type"] != "service":
                    print_error(f"Destination of connection {connection} for {entity} is not a service")
                    valid = False
    return valid

def check_no_cycles(config) -> bool:
    '''
    Check if the given `config` contains no cycles.
    True if no cycles. Else, false.
    '''

    graph = build_directed_graph(config)

    try:
        cycle = nx.find_cycle(graph, orientation="original")
    except nx.exception.NetworkXNoCycle:
        return True
    return cycle == None

def check_unique_ports(config) -> bool:
    '''
    Check that all exposed service ports in the `config` are unique and not used by telemetry services.
    True if ports are unique. Else, false.
    '''
    ports = {}
    valid = True

    for entity in config:
        if config[entity]['type'] != "service":
            continue

        # Port exposed by default
        if 'expose' in config[entity] and config[entity]['expose'] != True:
            continue

        port = config[entity]['port']
        if port in TELEMETRY_PORTS:
            print_error(f"The port {port} is used for telemetry. Do not use it. Requested for {entity}.")
            valid = False
        elif port in ports:
            print_error("This port is already used by {}. Cannot assign to {}.".format(ports[port], entity))
            valid = False
        else:
            ports[port] = entity

    return valid

def build_directed_graph(config) -> nx.DiGraph:
    '''
    Return the directed graph representing the given `config`.
    '''
    graph = nx.DiGraph()

    # add nodes in graph
    for entity in config:
        graph.add_node(entity)

    # add edges in graph
    for entity in config:
        connections = []

        if config[entity]["type"] == "router":
            if "connections" in config[entity]:
                connections.extend(config[entity]["connections"])
        elif config[entity]["type"] == "service":
            if config[entity]["endpoints"] is None:
                continue
            for endpoint in config[entity]["endpoints"]:
                if "connections" in endpoint:
                    connections.extend(endpoint["connections"])

        if connections is not None:
            for connection in connections:
                if "->" in connection['path']: # connection is path
                    conns = connection['path'].split("->")
                    graph.add_edge(entity, conns[0])
                    # take entities in connnection by pair
                    for i in range(len(conns)-1):
                        graph.add_edge(conns[i], conns[i+1])
                else: # connection is direct
                    graph.add_edge(entity, connection['path'])

    return graph

def extract_connections(entityConfig) -> list:
    '''
    Extract the connections from the given `entityConfig`.
    Return list of connections.
    '''

    if entityConfig["type"] == "router":
        if "connections" in entityConfig:
            conns = entityConfig["connections"]
            return conns if conns is not None else []
    elif entityConfig["type"] == "service":
        connections = []
        for endpoint in entityConfig["endpoints"]:
            if "connections" in endpoint:
                if endpoint["connections"] is not None:
                    connections.extend(endpoint["connections"])
        return connections

# From https://gist.github.com/pypt/94d747fe5180851196eb
# Check that keys are unique when loading yaml
class UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        mapping = set()
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in mapping:
                raise ValueError(f"Names of entities must be unique. Found {key!r} more than once.")
            mapping.add(key)
        return super().construct_mapping(node, deep)
