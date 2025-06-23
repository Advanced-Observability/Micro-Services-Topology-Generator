'''
Represent the architecture for the generator.
'''

import copy

import config_parser
import kubernetes
import utils
import entities
import constants


class Architecure:
    '''Represent the architecture.'''

    def __init__(self, conf_file: str, config):
        self.filename = conf_file
        self.config = config
        self.entities: list[entities.Entity] = []
        self.docker_networks: list[entities.DockerNetwork] = []
        self.kubernetes = kubernetes.Kubernetes() if utils.output_is_k8s() else None
        self.generate_architecture()

    def generate_architecture(self):
        """
        Generate the architecture based on the given config and generate a docker compose
        or launches the pods/services on the Kubernetes cluster.
        """
        # Check if the given configuration is valid
        print("Checking validity of configuration...")
        if not config_parser.check_config(self.config):
            raise RuntimeError("Invalid configuration")
        utils.print_info("Configuration passed all checks")

        # Create graph
        print("\nCreating graph based on configuration...")
        self.graph = config_parser.build_directed_graph(self.config)
        utils.print_info("Generated graph")

        # Generate entities and parse connections
        print("\nCreating entities based on configuration...")
        self.generate_entities()
        utils.print_info("Generated entities")

        print("\nChecking network connections...")
        self.parse_end_to_end_connections()
        utils.print_info("Parsed network connections")

        # Generate docker networks
        print("\nCreating docker networks...")
        self.generate_docker_networks()
        utils.print_info("Generated docker networks")

        # Associate entities to docker networks
        print("\nAssociating entities with docker networks...")
        self.associate_docker_networks()
        utils.print_info("Associated docker network to entities")

        # Generating ip route cmd
        print("\nGenerating ip route commands...")
        self.generate_ip_route_cmds()
        utils.print_info("Generated ip route commands")

        # Add entries into /etc/hosts of services
        print("\nAssociating hosts that are connected to each others...")
        self.modify_etc_hosts()
        utils.print_info("Associated hosts that are connected to each others")

        # Associate each entity to the ones on which it depends
        print("\nAssociating entities to their dependencies...")
        self.associate_dependencies()
        utils.print_info("Associated entities to their dependencies")

        # Generate additional commands to configure entities
        print("\nGenerating additional commands...")
        self.generate_additional_cmds()
        utils.print_info("Generated additional commands")

        # Generate timers to trigger commands
        print("\nGenerating timers...")
        self.generate_timers()
        utils.print_info("Generated timers\n")

    def print(self):
        """Print the architecture"""
        for net in self.docker_networks:
            print(net)
        for e in self.entities:
            print(e)
        if self.kubernetes:
            print(self.kubernetes)

    def pretty_print(self):
        """Print in a pretty way the architecture."""
        for net in self.docker_networks:
            print(net.pretty())
        for e in self.entities:
            print(e.pretty())
        if self.kubernetes:
            print(self.kubernetes.pretty())

    def generate_entities(self):
        '''Generate list of entities from the configuration.'''
        for entity in self.config:
            if self.config[entity]["type"] == "service":
                self.entities.append(entities.Service(entity, self.config[entity]))
            elif self.config[entity]["type"] == "router":
                self.entities.append(entities.Router(entity))
            else:
                raise RuntimeError(f"Entity {entity} has unexpected "
                                   f"type {self.config[entity]["type"]}")

    def find_entity(self, name: str):
        '''
        Find an entity in the architecture with the given `name`.
        If not found, return None.
        '''
        for entity in self.entities:
            if entity.name == name:
                return entity

        return None

    def find_service(self, name: str):
        '''
        Find service with given `name`.
        If not found, return None.
        '''
        for entity in self.entities:
            if entity.name == name and isinstance(entity, entities.Service):
                return entity
        return None

    def find_network(self, name: str):
        '''
        Find DockerNetwork with given `name`.
        If not found, return None.
        '''

        for net in self.docker_networks:
            if net.name == name:
                return net, self.docker_networks.index(net)

        return None

    def parse_end_to_end_connections(self) -> None:
        '''Parse E2E connections for the services based on the architecture.'''

        for entity in self.entities:
            if not isinstance(entity, entities.Service):
                continue

            e = config_parser.get_entity(self.config, entity.name)
            if e is None:
                raise RuntimeError(f"Unable to get entity {entity.name}")

            connections: list[str] = []
            for endpoint in e["endpoints"]:
                if "connections" in endpoint and endpoint["connections"] is not None:
                    connections.extend(conn["path"] for conn in endpoint["connections"])

            entity.e2e_conns.extend(connections)

    def get_interface_id(self, source: str, dest: str) -> int:
        '''
        Return the interface id to contact `dest` from `source`.
        If not found, return None.
        '''

        entity = self.find_entity(source)
        if entity is None:
            raise RuntimeError(f"Cannot find entity {source} in get_interface_id")

        names = [net["name"] for net in entity.attached_networks]

        # every service is connected to the telemetry network if otel/jaeger is used
        if isinstance(entity, entities.Service) and utils.is_using_jaeger() and \
                        utils.output_is_compose():
            names.append("network_telemetry")

        net_name1 = entities.DockerNetwork.generate_name(source, dest)
        net_name2 = entities.DockerNetwork.generate_name(dest, source)
        if net_name1 in names:
            # +1 for k8s because eth0 is assigned by default cni
            return names.index(net_name1) if utils.output_is_compose() else names.index(net_name1) + 1
        if net_name2 in names:
            # +1 for k8s because eth0 is assigned by default cni
            return names.index(net_name2) if utils.output_is_compose() else names.index(net_name2) + 1

        raise RuntimeError(f"Cannot find network for {net_name1} and {net_name2}")

    def modify_etc_hosts(self) -> None:
        """
        Associate `extra_hosts` to services with connections to other entities.
        Required for docker compose to prevent DNS resolution on the wrong network.
        Otherwise, it uses the telemetry network for communication between the services.
        """
        for entity in self.entities:
            if not isinstance(entity, entities.Service):
                continue

            for e2e in entity.e2e_conns:
                # path
                if "->" in e2e:
                    hops = e2e.split("->")

                    first = hops[0]
                    penultimate = hops[len(hops) - 2]
                    last = hops[len(hops) - 1]

                    # forward path
                    shared_penultimate_last = self.get_shared_network(penultimate, last)
                    if shared_penultimate_last is None:
                        raise RuntimeError(f"Unable to get network between {penultimate} "
                                           f"and {last} in associate_extra_hosts")

                    entity.extra_hosts.add((last, shared_penultimate_last.end_ip))

                    # reverse path
                    shared_begin_first_hop = self.get_shared_network(entity.name, first)
                    if shared_begin_first_hop is None:
                        raise RuntimeError(f"Unable to get network between {entity.name} "
                                           f"and {first} in associate_extra_hosts")

                    last_service = self.find_service(last)
                    if last_service is None:
                        raise RuntimeError("Unable to find service " + last)

                    last_service.extra_hosts.add((entity.name, shared_begin_first_hop.begin_ip))

                # direct connection
                else:
                    net = self.get_shared_network(entity.name, e2e)
                    if net is None:
                        raise RuntimeError(f"Unable to get shared network between {entity.name} "
                                           f"and {e2e} in associate_extra_hosts")

                    # forward path
                    entity.extra_hosts.add((e2e, net.end_ip))

                    # reverse path
                    service = self.find_service(e2e)
                    if service is None:
                        raise RuntimeError("Unable to find service " + e2e)

                    service.extra_hosts.add((entity.name, net.begin_ip))

    def associate_dependencies(self) -> None:
        """Associate all the entities to the ones they depend on"""

        for e in self.config:
            entity = self.find_entity(e)
            if entity is None:
                raise RuntimeError(f"Cannot find entity {e} in associate_dependencies")

            connections = config_parser.extract_connections(self.config[e])
            connections = [conn["path"] for conn in connections]

            for connection in connections:
                if "->" in connection:  # connection is a path
                    entity.depends_on.update(connection.split("->"))
                else:  # connection is direct
                    entity.depends_on.add(connection)

    def get_shared_network(self, begin: str | None, end: str | None):
        """
        Get the Docker network shared by `begin` and `end`.
        None if not found.
        """
        if begin is None or end is None:
            return None

        for net in self.docker_networks:
            if net.begin == begin and net.end == end:
                return net

        return None

    def generate_ip_route_cmds(self) -> None:
        '''Generate the IP route commands to configure the services.'''

        for e in self.entities:
            if not isinstance(e, entities.Service):
                continue

            for e2e in e.e2e_conns:
                # connection is path
                if "->" in e2e:
                    self.ip_route_path_connection(e, e2e)

                # connection is direct - only required if IOAM/CLT
                elif utils.is_using_clt() or utils.is_using_ioam_only():
                    self.ip_route_direct_connection(e, e2e)

    def ip_route_path_connection(self, source_entity: entities.Service, path: str) -> None:
        '''
        Generate ip route commands for `path` starting from `source_entity`.
        '''
        hops = path.split("->")
        hops.insert(0, source_entity.name)
        ioam_trace_hex = "0x" + utils.build_ioam_trace_type()
        size_ioam_data = utils.size_ioam_trace() * len(hops)

        penultimate = hops[len(hops) - 2]
        end = hops[len(hops) - 1]

        # get source subnet
        shared_source_first_hop = self.get_shared_network(hops[0], hops[1])
        if shared_source_first_hop is None:
            raise RuntimeError(f"Unable to get network shared by {hops[0]} and {hops[1]}")
        source_ip_subnet = shared_source_first_hop.subnet

        # get dest subnet
        shared_penultimate_end = self.get_shared_network(penultimate, end)
        if shared_penultimate_end is None:
            raise RuntimeError(f"Cannot get network shared by {penultimate} and {end}")
        dest_ip_subnet = shared_penultimate_end.subnet

        # configure all entities on path
        for i in range(0, len(hops)):
            prev = hops[i - 1] if i > 0 else None
            curr = hops[i]
            next_node = hops[i + 1] if i < len(hops) - 1 else None

            curr_entity = self.find_entity(curr)
            if curr_entity is None:
                raise RuntimeError("Unable to get entity " + curr)

            if next_node is not None:
                next_entity = self.find_entity(next_node)
                if next_entity is None:
                    raise RuntimeError("Unable to get entity " + next_node)

            if prev is not None:
                prev_entity = self.find_entity(prev)
                if prev_entity is None:
                    raise RuntimeError("Unable to get entity " + prev)

            # towards dest
            if i != len(hops) - 1:
                cmd = ""

                next_net = self.get_shared_network(curr, next_node)
                if next_net is None:
                    raise RuntimeError(f"Cannot get network shared by {curr} and {next_node}")

                if utils.topology_is_ipv6():
                    # if ioam and first node => encap ioam pto in route
                    if (utils.is_using_clt() or utils.is_using_ioam_only()) and i == 0:
                        cmd = constants.TEMPLATE_IP6_ROUTE_PATH.format(
                            dest_ip_subnet, ioam_trace_hex, size_ioam_data, next_net.end_ip
                        )
                    else:
                        cmd = constants.TEMPLATE_IP6_ROUTE_PATH_NO_IOAM.format(
                            dest_ip_subnet, next_net.end_ip
                        )
                elif utils.topology_is_ipv4():
                    cmd = constants.TEMPLATE_IP4_ROUTE_PATH.format(dest_ip_subnet, next_net.end_ip)
                curr_entity.iproute_cmds.add(cmd)

            # towards source
            if i != 0:
                cmd = ""

                prev_net = self.get_shared_network(prev, curr)
                if prev_net is None:
                    raise RuntimeError(f"Cannot get network shared by {prev} and {curr}")

                if utils.topology_is_ipv4():
                    cmd = constants.TEMPLATE_IP4_ROUTE_PATH.format(
                        source_ip_subnet, prev_net.begin_ip
                    )
                else:
                    cmd = constants.TEMPLATE_IP6_ROUTE_PATH_NO_IOAM.format(
                        source_ip_subnet, prev_net.begin_ip
                    )

                curr_entity.iproute_cmds.add(cmd)

    def ip_route_direct_connection(self, source_entity: entities.Service, dest: str) -> None:
        '''
        Generate ip route command for direct connection between `source_entity` and `dest`.
        Only required for IOAM/CLT over IPv6.
        '''
        net = self.get_shared_network(source_entity.name, dest)
        if net is None:
            raise RuntimeError(f"Unable to get shared network for {source_entity.name} and "
                               f"{dest} in generate_ip_route_cmds")

        ioam_trace_hex = "0x" + utils.build_ioam_trace_type()
        size_ioam_data = utils.size_ioam_trace() * 2

        # towards dest

        # get interface id (ethX) of source to contact end host
        interface_id = self.get_interface_id(source_entity.name, dest)
        if interface_id is None:
            raise RuntimeError(f"Unable to get interface of {source_entity.name} to contact {dest}")

        source_entity.iproute_cmds.add(constants.TEMPLATE_IP6_ROUTE_DIRECT_CONNECTION.format(
            net.end_ip, ioam_trace_hex, size_ioam_data, f"{interface_id}_{source_entity.name}")
        )

    def generate_docker_networks(self) -> None:
        '''Generate all docker networks based on the architecture.'''
        for pair in self.graph.edges:
            net = entities.DockerNetwork(pair[0], pair[1])
            self.docker_networks.append(net)

    def associate_docker_networks(self) -> None:
        '''Associate all the entities to the appropriate docker networks.'''
        for entity in self.entities:
            for docker_net in self.docker_networks:
                ip = None
                if docker_net.begin == entity.name:
                    ip = docker_net.begin_ip
                elif docker_net.end == entity.name:
                    ip = docker_net.end_ip
                if ip is not None:
                    entity.attached_networks.append({
                        "name": docker_net.name,
                        "ip": ip
                    })

    def generate_traffic_impairments(self, entity: entities.Entity, entity_config) -> list:
        '''
        Generate the list of commands to impair the traffic
        of `entity` with the given `entity_config`.
        '''
        connections = config_parser.extract_connections(entity_config)

        commands = []

        for conn in connections:
            first_hop = conn['path'].split("->")[0] if "->" in conn["path"] else conn["path"]

            interface = self.get_interface_id(entity.name, first_hop)
            if interface is None:
                raise RuntimeError(f"Cannot find interface to contact {first_hop} "
                                   f"from {entity.name}")

            # modify mtu
            if "mtu" in conn and isinstance(conn["mtu"], int) and conn["mtu"] >= 1280:
                cmd = constants.MTU_OPTION.format(f"{interface}_{entity.name}", conn['mtu'])
                commands.append(cmd)
            elif "mtu" not in conn:
                pass
            else:
                raise RuntimeError(f"MTU must be an integer and greater than 1280 because we are "
                                   f"using IPv6 for connection {conn} of {entity.name}")

            # modify buffer size
            if "buffer_size" in conn and isinstance(conn["buffer_size"], int):
                cmd = constants.BUFFER_SIZE_OPTION.format(
                    f"{interface}_{entity.name}", conn['buffer_size']
                )
                commands.append(cmd)
            elif "buffer_size" not in conn:
                pass
            else:
                raise RuntimeError(f"Buffer size must be an integer for connection "
                                   f"{conn} of {entity.name}")

            # build command
            ip_tc_cmd = f"tc qdisc add dev eth{interface} root netem"
            ip_tc_command_original_length = len(ip_tc_cmd)

            # modify rate
            if "rate" in conn and isinstance(conn["rate"], str) and\
                utils.match_tc_rate(conn["rate"]):
                ip_tc_cmd += f" rate {conn['rate']}"
            elif "rate" not in conn:
                pass
            else:
                raise RuntimeError(f"Rate for connection {conn} of {entity.name} must be a "
                                   f"int followed by a rate unit valid for tc")

            # modify delay
            if "delay" in conn and isinstance(conn['delay'], str) and\
                  utils.match_tc_time(conn["delay"]):
                ip_tc_cmd += f" delay {conn['delay']}"
                if "jitter" in conn and isinstance(conn["jitter"], str) and\
                    utils.match_tc_time(conn["jitter"]):
                    ip_tc_cmd += f" {conn['jitter']}"
                elif "jitter" not in conn:
                    pass
                else:
                    raise RuntimeError(f"Jitter for connection {conn} of {entity.name} must be "
                                       f"a int followed by a time unit valid for tc")
            elif "delay" not in conn:
                pass
            else:
                raise RuntimeError(f"Delay for connection {conn} of {entity.name} must be a int "
                                   f"followed by a time unit valid for tc")

            # modify jitter
            if "jitter" in conn and "delay" not in conn:
                raise RuntimeError(f"Cannot specify some jitter and not some delay for connection "
                                   f"{conn} of {entity.name}")

            # modify loss
            if "loss" in conn and isinstance(conn["loss"], str) and\
                utils.match_tc_percent(conn["loss"]):
                ip_tc_cmd += f" loss {conn['loss']}"
            elif "loss" not in conn:
                pass
            else:
                raise RuntimeError(f"Loss for connection {conn} of {entity.name} must be a int "
                                   f"followed by %")

            # modify corrupt
            if "corrupt" in conn and isinstance(conn["corrupt"], str) and\
                utils.match_tc_percent(conn["corrupt"]):
                ip_tc_cmd += f" corrupt {conn['corrupt']}"
            elif "corrupt" not in conn:
                pass
            else:
                raise RuntimeError(f"Corruption rate for connection {conn} of {entity.name} must "
                                   f"be a int followed by %")

            # modify duplicate
            if "duplicate" in conn and isinstance(conn["duplicate"], str) and\
                utils.match_tc_percent(conn["duplicate"]):
                ip_tc_cmd += f" duplicate {conn['duplicate']}"
            elif "duplicate" not in conn:
                pass
            else:
                raise RuntimeError(f"Duplicate rate for connection {conn} of {entity.name} must "
                                   f"be a int followed by %")

            # modify reorder
            if "reorder" in conn and isinstance(conn["reorder"], str) and\
                utils.match_tc_percent(conn["reorder"]):
                ip_tc_cmd += f" reorder {conn['reorder']}"
            elif "reorder" not in conn:
                pass
            else:
                raise RuntimeError(f"Reorder rate for connection {conn} of {entity.name} must be "
                                   f"a int followed by %")

            # check that some options were added
            if len(ip_tc_cmd) != ip_tc_command_original_length:
                commands.append(ip_tc_cmd)

        return commands

    def generate_additional_cmds(self) -> None:
        '''Generate extra commands to configure the entities of the architecture.'''
        for entity in self.entities:
            conf = config_parser.get_entity(self.config, entity.name)
            if conf is None:
                raise RuntimeError(f"Entity {entity.name} has not been found")

            cmds = self.generate_traffic_impairments(entity, conf)
            entity.additional_cmds.extend(cmds)

    def generate_timers(self) -> None:
        '''Generate commands to handle the timers.'''

        for entity in self.entities:
            e = config_parser.get_entity(self.config, entity.name)
            if e is None:
                raise RuntimeError(f"Entity {entity.name} has not been found")

            connections = config_parser.extract_connections(e)

            for conn in connections:
                if "timers" not in conn or conn["timers"] is None:
                    continue

                first_hop = conn['path'].split("->")[0] if "->" in conn["path"] else conn["path"]
                interface = self.get_interface_id(entity.name, first_hop)
                if interface is None:
                    raise RuntimeError(f"Unable to find interface for "
                                       f"{entity.name} and {first_hop}")

                for timer in conn["timers"]:
                    # check if valid impairment
                    if timer["option"] not in constants.CONNECTION_IMPAIRMENTS:
                        raise RuntimeError(f"{timer} for {conn} of {entity.name} is setting a "
                                           f"timer on {timer['option']} which is not a connection "
                                           f"impairment")

                    # check if there is an original value
                    if timer["option"] not in conn:
                        raise RuntimeError(f"Cannot modify {timer['option']} for {conn} of "
                                           f"{entity.name} with a timer because an original value "
                                           f"is not set")

                    # create modified version of config
                    new_config = copy.deepcopy(e)
                    if new_config["type"] == "router":
                        if "connections" in new_config and new_config["connections"] is not None:
                            for connection in new_config["connections"]:
                                if connection == conn:
                                    connection[timer["option"]] = timer["newValue"]
                    elif new_config["type"] == "service":
                        for endpoint in new_config["endpoints"]:
                            if "connections" in endpoint and endpoint["connections"] is not None:
                                for connection in endpoint["connections"]:
                                    if connection == conn:
                                        connection[timer["option"]] = timer["newValue"]

                    # generate command for traffic impairment
                    cmds = self.generate_traffic_impairments(entity, new_config)
                    filtered = list(filter(
                        lambda cmd: utils.filter_cmd(timer['option'], cmd, f"eth{interface}"), cmds
                    ))
                    if len(filtered) != 1:
                        raise RuntimeError(f"Unexpected length of commands for timer "
                                           f"{timer['option']} for connection {conn} "
                                           f"of entity {entity}")
                    index = filtered[0].find("eth")
                    if index == -1:
                        raise RuntimeError(f"Unable to find interface for {conn} of {entity.name}")
                    index += 3  # skip "eth"

                    # find interface id
                    interface_id = ""
                    while filtered[0][index].isdigit():
                        interface_id += filtered[0][index]
                        index += 1

                    if "tc" in filtered[0]:
                        cmd_modify = constants.MODIFY_IMPAIRMENT_DELETE_TC.format(
                            timer['start'], f"{interface_id}_{entity.name}", filtered[0]
                        )
                    else:
                        cmd_modify = constants.MODIFY_IMPAIRMENT.format(timer['start'], filtered[0])
                    entity.additional_cmds.append(cmd_modify)

                    # generate command to restore original value for impairment
                    if "duration" in timer:
                        cmds_reset = self.generate_traffic_impairments(entity, e)
                        filtered = list(filter(
                            lambda cmd: utils.filter_cmd(timer['option'], cmd, f"eth{interface}"),
                            cmds_reset
                        ))
                        if len(filtered) != 1:
                            raise RuntimeError(f"Unexpected length of commands for timer "
                                               f"{timer['option']} for connection {conn} of "
                                               f"entity {entity}")

                        if "tc" in filtered[0]:
                            cmd_reset = constants.MODIFY_IMPAIRMENT_DELETE_TC.format(
                                timer["start"] + timer["duration"], f"{interface_id}_{entity.name}",
                                filtered[0]
                            )
                        else:
                            cmd_reset = constants.MODIFY_IMPAIRMENT.format(
                                timer['start'] + timer['duration'], filtered[0]
                            )

                        entity.additional_cmds.append(cmd_reset)
