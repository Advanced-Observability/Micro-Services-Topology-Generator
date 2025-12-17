"""
Represent the architecture.
"""

import copy

import utils
import router
import switch
import network
import entities
import services
import firewall
import constants
import kubernetes
import config_parser


class Architecure:
    '''Represent the architecture.'''

    def __init__(self, conf_file: str, config):
        """
        Create the architecture.

        :param conf_file: Path towards config file.
        :param config: Loaded YAML configuration file.
        """
        self.filename = conf_file
        self.config = config
        self.entities: list[entities.Entity] = []
        self.networks: list[network.Network] = []
        self.kubernetes = kubernetes.Kubernetes() if utils.output_is_k8s() else None
        self.generate_architecture()

    def generate_architecture(self):
        """
        Generate the architecture based on the given config.
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

        # Generate entities
        print("\nCreating entities based on configuration...")
        self.generate_entities()
        utils.print_info("Generated entities")

        # Check network connections
        print("\nChecking network connections...")
        self.parse_e2e_connections()
        utils.print_info("Parsed network connections")

        # Generate networks and connect to entities
        print("\nCreating networks...")
        self.generate_networks()
        utils.print_info("Generated networks")

        # Generating ip route cmd
        print("\nGenerating ip route commands...")
        self.generate_ip_route_cmds()
        utils.print_info("Generated ip route commands")

        # Add entries into /etc/hosts of services
        print("\nConfiguring DNS...")
        self.modify_etc_hosts()
        utils.print_info("Configured DNS")

        # Associate each entity to the ones on which it depends
        print("\nAssociating entities to their dependencies...")
        self.associate_dependencies()
        utils.print_info("Associated entities to their dependencies")

        # Generate additional commands to configure entities
        print("\nGenerating additional commands...")
        self.generate_additional_cmds()
        utils.print_info("Generated additional commands")

    def print(self):
        """Print the architecture"""
        for net in self.networks:
            print(net)
        for e in self.entities:
            print(e)
        if self.kubernetes:
            print(self.kubernetes)

    def pretty_print(self):
        """Print in a pretty way the architecture."""
        for net in self.networks:
            print(net.pretty())
        for e in self.entities:
            print(e.pretty())
        if self.kubernetes:
            print(self.kubernetes.pretty())

    def generate_entities(self):
        '''Generate list of entities from the configuration.'''
        for entity in self.config:
            entity_type = self.config[entity]["type"]
            if entity_type == "service":
                self.entities.append(services.Service(
                    entity, self.config[entity],
                    False,
                    "mstg_service_clt" if utils.is_using_clt() else "mstg_service"
                ))
            elif entity_type == "external":
                self.entities.append(services.Service(
                    entity, self.config[entity],
                    True, self.config[entity]["image"]
                ))
            elif entity_type == "router":
                self.entities.append(router.Router(entity, self.config[entity]))
            elif entity_type == "firewall":
                self.entities.append(firewall.Firewall(entity, self.config[entity]))
            elif entity_type == "switch":
                self.entities.append(switch.Switch(entity, self.config[entity]))
            else:
                raise RuntimeError(f"Entity {entity} has unexpected type {entity_type}")

    def find_entity(self, name: str) -> entities.Entity | None:
        '''Find an entity in the architecture with the given `name`. If not found, return None.'''
        return next((entity for entity in self.entities if entity.name == name), None)

    def find_service(self, name: str) -> services.Service | None:
        '''Find service with given `name`. If not found, return None.'''
        entity = self.find_entity(name)
        return entity if isinstance(entity, services.Service) else None

    def find_switch(self, name: str) -> switch.Switch | None:
        '''Find switch with given `name`. If not found, return None.'''
        entity = self.find_entity(name)
        return entity if isinstance(entity, switch.Switch) else None

    def count_l3_networks(self) -> int:
        """Count number of L3 networks in the architecture."""
        return sum(1 for net in self.networks if net.type == network.NetworkType.L3_NET)

    def parse_e2e_connections(self) -> None:
        '''Parse E2E connections for the entities based on the architecture.'''

        for entity in self.entities:
            if not isinstance(entity, services.Service):
                continue

            conns = config_parser.extract_connections(entity.config)
            entity.e2e_conns.update([f"{entity.name}->"+conn["path"] for conn in conns])

            for conn in conns:
                hops = conn["path"].split("->")
                for hop in hops:
                    e = self.find_entity(hop)
                    if e is not None:
                        e.e2e_conns.add(f"{entity.name}->"+conn["path"])

    def get_interface_id(self, source: str, dest: str) -> int:
        '''
        Return the interface id to contact `dest` from `source`.
        If not found, return None.
        '''

        source_entity = self.find_entity(source)
        if source_entity is None:
            raise RuntimeError(f"Cannot find entity {source} in get_interface_id")

        # we need to add 1 for k8s because eth0 is assigned to default cni

        for i, net in enumerate(source_entity.attached_networks):
            if net.get_shared_interface(source, dest) is not None:
                return i if utils.output_is_compose() else i+1

        raise RuntimeError(f"Could not get interface between {source} and {dest}")

    def modify_etc_hosts(self) -> None:
        """
        Associate `extra_hosts` to services with connections to other entities.
        Required for docker compose to prevent DNS resolution on the wrong network.
        Otherwise, it uses the telemetry network for communication between the services.
        """
        for entity in self.entities:
            # no need to modify /etc/hosts for router and switches
            if isinstance(entity, (router.Router, switch.Switch)):
                continue

            for e2e in entity.e2e_conns:
                # if path and service:
                #   - add first node in /etc/hosts of last node
                #   - add last node in /etc/hosts of first node
                if "->" in e2e and isinstance(entity, services.Service):
                    hops = e2e.split("->")
                    if hops[0] != entity.name:  # if entity is not source of path do not process
                        continue

                    first = hops[1]
                    penultimate = hops[len(hops) - 2]
                    last = hops[len(hops) - 1]

                    # forward path
                    shared_penultimate_last = self.get_shared_network(penultimate, last)
                    if shared_penultimate_last is None:
                        raise RuntimeError(f"Unable to get network between {penultimate} and {last} in associate_extra_hosts")

                    entity.extra_hosts[last] = shared_penultimate_last.get_entity_ip(last)

                    # reverse path
                    shared_begin_first_hop = self.get_shared_network(entity.name, first)
                    if shared_begin_first_hop is None:
                        raise RuntimeError(f"Unable to get network between {entity.name} and {first} in associate_extra_hosts")

                    last_service = self.find_service(last)
                    if last_service is None:
                        raise RuntimeError("Unable to find service " + last)

                    last_service.extra_hosts[entity.name] = shared_begin_first_hop.get_entity_ip(entity.name)

                elif "->" in e2e and isinstance(entity, firewall.Firewall):  # for FW, we need to add every hop on path in /etc/hosts of fw
                    hops = e2e.split("->")
                    for i in range(len(hops)-1):
                        net = self.get_shared_network(hops[i], hops[i+1])
                        if net is None:
                            raise RuntimeError(f"Unable to get shared network between {hops[i]} and {hops[i+1]} in associate_extra_hosts")
                        if hops[i] != entity.name:
                            entity.extra_hosts[hops[i]] = net.get_entity_ip(hops[i])
                        if hops[i+1] != entity.name:
                            entity.extra_hosts[hops[i+1]] = net.get_entity_ip(hops[i+1])

                else:
                    # direct connection
                    #   - add current node in /etc/hosts of next node
                    #   - add next node in /etc/hosts of current node
                    net = self.get_shared_network(entity.name, e2e)
                    if net is None:
                        raise RuntimeError(f"Unable to get shared network between {entity.name} and {e2e} in associate_extra_hosts")

                    # forward path
                    entity.extra_hosts[e2e] = net.get_entity_ip(e2e)

                    # reverse path
                    service = self.find_service(e2e)
                    if service is None:
                        raise RuntimeError("Unable to find service " + e2e)
                    service.extra_hosts[entity.name] = net.get_entity_ip(entity.name)

    def associate_dependencies(self) -> None:
        """Associate all the entities to the ones they depend on"""

        for e in self.config:
            entity = self.find_entity(e)
            if entity is None:
                raise RuntimeError(f"Cannot find entity {e} in associate_dependencies")

            # SW can be started without dependency because configuration is done via
            # commands.sh file after every container has been started
            if isinstance(entity, switch.Switch):
                continue

            connections = [conn["path"] for conn in config_parser.extract_connections(self.config[e])]

            for connection in connections:
                if "->" in connection:  # connection is a path
                    entity.depends_on.update(connection.split("->"))
                else:  # connection is direct
                    entity.depends_on.add(connection)

    def get_shared_network(self, begin: str | None, end: str | None):
        """
        Get the network shared by `begin` and `end`.
        None if not found.
        """
        if begin is None or end is None:
            return None

        b = self.find_switch(begin)
        e = self.find_switch(end)
        if b is not None or e is not None:  # if begin or end is a switch
            for net in self.networks:
                if net.get_shared_interface(begin, end) is not None:
                    return net
        else:  # both entities are not switches
            for net in self.networks:
                iface = net.get_shared_interface(begin, end)
                if iface is None:
                    continue

                if net.type == network.NetworkType.L3_NET and iface.entity.name == begin and iface.next_hop.name == end:
                    return net

        return None

    def check_shared_network(self, begin: str, end: str) -> network.Network | None:
        """
        Check whether there is a network shared by `begin` and `end`.
        """

        for net in self.networks:
            if net.check_shared_network(begin, end):
                return net

        return None

    def generate_ip_route_cmds(self) -> None:
        '''Generate the IP route commands to configure the services.'''

        for e in self.entities:
            # Services are located at both ends of connection
            # Thus, we can limit to start from these entities to configure the routes of the other entities
            if not isinstance(e, services.Service):
                continue

            for conn in e.e2e_conns:
                # connection is path
                if "->" in conn:
                    self.ip_route_path_connection(conn)

                # connection is direct - only required if IOAM/CLT
                elif utils.is_using_clt() or utils.is_using_ioam_only():
                    self.ip_route_direct_connection(e, conn)

    def ip_route_path_connection(self, path: str) -> None:
        '''
        Generate ip route commands for `path` starting from `source_entity`.
        '''
        hops = path.split("->")

        # get source subnet
        shared_source_first_hop = self.get_shared_network(hops[0], hops[1])
        if shared_source_first_hop is None:
            raise RuntimeError(f"Unable to get network shared by {hops[0]} and {hops[1]}")
        source_ip_subnet = shared_source_first_hop.subnet

        # get dest subnet
        penultimate = hops[len(hops) - 2]
        end = hops[len(hops) - 1]
        shared_penultimate_end = self.get_shared_network(penultimate, end)
        if shared_penultimate_end is None:
            raise RuntimeError(f"Cannot get network shared by {penultimate} and {end}")
        dest_ip_subnet = shared_penultimate_end.subnet

        # configure all entities on path
        for i, curr_name in enumerate(hops):
            prev_name = hops[i - 1] if i > 0 else None
            next_name = hops[i + 1] if i < len(hops) - 1 else None

            curr_entity = self.find_entity(curr_name)
            if curr_entity is None:
                raise RuntimeError("Unable to get entity " + curr_name)

            # no need to configure L3 route on L2 switch
            if isinstance(curr_entity, switch.Switch):
                continue

            if next_name is not None:
                next_entity = self.find_entity(next_name)
                if next_entity is None:
                    raise RuntimeError("Unable to get entity " + next_name)

            if prev_name is not None:
                prev_entity = self.find_entity(prev_name)
                if prev_entity is None:
                    raise RuntimeError("Unable to get entity " + prev_name)

            # towards dest
            if i != len(hops) - 1:
                next_net = self.get_shared_network(curr_name, next_name)
                if next_net is None:
                    raise RuntimeError(f"Cannot get network shared by {curr_name} and {next_name}")

                # if next entity is switch, need to look ahead for L3 device
                ip = None
                if isinstance(next_entity, switch.Switch):
                    not_found = False
                    temp_i = i+1
                    while not not_found and temp_i <= len(hops) - 1:
                        entity = self.find_entity(hops[temp_i])
                        if entity is None:
                            raise RuntimeError(f"Could not find entity {hops[temp_i]}")
                        if isinstance(entity, switch.Switch):
                            temp_i += 1
                        else:
                            shared = self.check_shared_network(curr_name, entity.name)
                            if shared is None:
                                raise RuntimeError(f"Could not find network with {curr_name} and {entity.name}")
                            ip = shared.get_entity_ip(hops[temp_i])
                            if ip is None:
                                raise RuntimeError(f"Missing IP for {hops[temp_i]}")
                            not_found = True
                else:
                    ip = next_net.get_entity_ip(next_name)

                if ip is None:
                    raise RuntimeError(f"Cannot find IP of {ip}")

                cmd = ""
                if utils.topology_is_ipv6():
                    # if ioam and first node => encap ioam pto in route
                    if (utils.is_using_clt() or utils.is_using_ioam_only()) and i == 0:
                        ioam_trace_hex = "0x" + utils.build_ioam_trace_type()
                        size_ioam_data = utils.size_ioam_trace() * len(hops)
                        cmd = constants.IP6_ROUTE_PATH_IOAM.format(dest_ip_subnet, ioam_trace_hex, size_ioam_data, ip)
                    else:
                        cmd = constants.IP6_ROUTE_PATH_VANILLA.format(dest_ip_subnet, ip)
                elif utils.topology_is_ipv4():
                    cmd = constants.IP4_ROUTE_PATH_VANILLA.format(dest_ip_subnet, ip)
                curr_entity.add_command(cmd)

            # towards source
            if i != 0:
                prev_net = self.get_shared_network(prev_name, curr_name)
                if prev_net is None:
                    raise RuntimeError(f"Cannot get network shared by {prev_name} and {curr_name}")

                # if prev entity is switch, need to look backward for L3 device
                ip = None
                if isinstance(prev_entity, switch.Switch):
                    not_found = False
                    temp_i = i-1
                    while not not_found and temp_i >= 0:
                        entity = self.find_entity(hops[temp_i])
                        if entity is None:
                            raise RuntimeError(f"Could not find entity {hops[temp_i]}")
                        if isinstance(entity, switch.Switch):
                            temp_i -= 1
                        else:
                            shared = self.check_shared_network(entity.name, curr_name)
                            if shared is None:
                                raise RuntimeError(f"Could not find network with {curr_name} and {entity.name}")
                            ip = shared.get_entity_ip(hops[temp_i])
                            if ip is None:
                                raise RuntimeError(f"Missing IP for {hops[temp_i]}")
                            not_found = True
                else:
                    ip = prev_net.get_entity_ip(prev_name)

                if ip is None:
                    raise RuntimeError(f"Cannot find IP of {ip}")

                cmd = ""
                if utils.topology_is_ipv4():
                    cmd = constants.IP4_ROUTE_PATH_VANILLA.format(source_ip_subnet, ip)
                else:
                    cmd = constants.IP6_ROUTE_PATH_VANILLA.format(source_ip_subnet, ip)

                curr_entity.add_command(cmd)

    def ip_route_direct_connection(self, source_entity: services.Service, dest: str) -> None:
        '''
        Generate ip route command for direct connection between `source_entity` and `dest`.
        Only required for IOAM/CLT over IPv6.
        '''
        net = self.get_shared_network(source_entity.name, dest)
        if net is None:
            raise RuntimeError(f"Unable to get shared network for {source_entity.name} and "
                               f"{dest} in generate_ip_route_cmds")

        # if its a switch network, no need to configure a L3 route
        if net.type == network.NetworkType.L2_NET:
            return

        ioam_trace_hex = "0x" + utils.build_ioam_trace_type()
        size_ioam_data = utils.size_ioam_trace() * 2

        # towards dest

        # get interface id (ethX) of source to contact end host
        if_id = self.get_interface_id(source_entity.name, dest)
        if if_id is None:
            raise RuntimeError(f"Unable to get interface of {source_entity.name} to contact {dest}")

        ip = net.get_entity_ip(dest)
        if ip is None:
            raise RuntimeError(f"Cannot get ip of {dest}")

        source_entity.add_command(constants.IP6_ROUTE_DIRECT_IOAM.format(
            ip, ioam_trace_hex, size_ioam_data,
            utils.get_interface_name(if_id, source_entity.name))
        )

    def generate_networks(self) -> None:
        '''Generate all networks based on the architecture.'''

        net_names: list[str] = []

        for entity in self.entities:
            if not isinstance(entity, services.Service):
                continue

            for conn in entity.e2e_conns:  # parsing every end-to-end connections
                hops = conn.split("->")
                i = 0
                while i < len(hops) - 1:  # need to create every network for a given e2e connection
                    curr = self.find_entity(hops[i])
                    next = self.find_entity(hops[i+1])

                    if curr is None or next is None:
                        raise RuntimeError("Could not get entity")

                    if isinstance(next, switch.Switch):  # if it's a switch need to look ahead to find next entity which is not a switch
                        j = i+1
                        while j < len(hops):
                            tmp = self.find_entity(hops[j])
                            if tmp is not None and not isinstance(tmp, switch.Switch):  # entity ahead which is not a switch
                                name = network.Network.generate_l2_net_name(hops[i+1])
                                if name not in net_names:  # create network if not existant
                                    net = network.Network(network.NetworkType.L2_NET)
                                    net.set_l2_network(hops[i+1])
                                    self.networks.append(net)
                                    net_names.append(name)

                                    # add interfaces for every intermediary interfaces
                                    for k in range(i, j+1):
                                        start = self.find_entity(hops[k])
                                        if start is None:
                                            raise RuntimeError("Could not get start entity")
                                        end = self.find_entity(hops[k+1]) if k < j else None

                                        start.attached_networks.append(net)

                                        if isinstance(start, switch.Switch):
                                            net.add_network_interface(start, end, True, next.get_vlan_id(hops[k]))
                                        else:
                                            net.add_network_interface(start, end, False, next.get_vlan_id(hops[k]))
                                i = j  # parse hops after the entity (not switch) found ahead of the switch
                                break
                            j += 1  # if many switches inline, skip all of them
                    else:  # if its not a switch, add a normal L3 network
                        name = network.Network.generate_l3_net_name(curr.name, next.name)
                        if name not in net_names:
                            net = network.Network(network.NetworkType.L3_NET)
                            net.set_l3_network(curr, next)
                            self.networks.append(net)
                            net_names.append(name)
                            curr.attached_networks.append(net)
                            next.attached_networks.append(net)

                        i += 1  # parse remaining hops

    def generate_additional_cmds(self) -> None:
        '''Generate extra commands to configure the entities of the architecture.'''
        for entity in self.entities:
            cmds = self.generate_traffic_impairments(entity, entity.config)
            for cmd in cmds:
                entity.add_command(cmd)
            self.generate_timers(entity, entity.config)

    def generate_traffic_impairments(self, entity: entities.Entity, entity_config) -> list:
        '''
        Generate the list of commands to impair the traffic
        of `entity` with the given `entity_config`.
        '''
        connections = config_parser.extract_connections(entity_config)
        commands = []

        for conn in connections:
            if not any(impairment in conn for impairment in constants.CONNECTION_IMPAIRMENTS):
                continue

            first_hop = conn['path'].split("->")[0] if "->" in conn["path"] else conn["path"]

            if_id = self.get_interface_id(entity.name, first_hop)
            if if_id is None:
                raise RuntimeError(f"Cannot find interface to contact {first_hop} from {entity.name}")

            ifname = utils.get_interface_name(if_id, entity.name)

            # modify mtu
            if "mtu" in conn:
                if not isinstance(conn["mtu"], int):
                    raise RuntimeError("MTU must be an integer")
                if utils.topology_is_ipv6() and conn["mtu"] < 1280:
                    raise RuntimeError(f"MTU cannot be smaller than 1280 for IPv6")
                commands.append(constants.MTU_OPTION.format(ifname, conn['mtu']))

            # modify buffer size
            if "buffer_size" in conn:
                if not isinstance(conn["buffer_size"], int):
                    raise RuntimeError("Buffer size must be an integer")
                commands.append(constants.BUFFER_SIZE_OPTION.format(ifname, conn['buffer_size']))

            # impairments with tc command
            cmd = self.generate_tc_command(entity, ifname, conn)
            if len(cmd) > 0:
                commands.append(cmd)

        return commands

    def generate_tc_command(self, entity: entities.Entity, ifname: str, connection) -> str:
        """Generate tc command to modify network settings."""
        cmd = constants.IMPAIRMENT_OPTION.format(ifname)
        cmd_original_length = len(cmd)

        # modify rate
        if "rate" in connection:
            if isinstance(connection["rate"], str) and utils.match_tc_rate(connection["rate"]):
                cmd += f" rate {connection['rate']}"
            else:
                raise RuntimeError(f"Rate for connection {connection} of {entity.name} must be a int followed by a rate unit valid for tc")

        # modify delay
        if "delay" in connection:
            if isinstance(connection['delay'], str) and utils.match_tc_time(connection["delay"]):
                cmd += f" delay {connection['delay']}"
            else:
                raise RuntimeError(f"Delay for connection {connection} of {entity.name} must be a int followed by a time unit valid for tc")
            if "jitter" in connection:
                if isinstance(connection["jitter"], str) and utils.match_tc_time(connection["jitter"]):
                    cmd += f" {connection['jitter']}"
                else:
                    raise RuntimeError(f"Jitter for connection {connection} of {entity.name} must be a int followed by a time unit valid for tc")

        # modify jitter
        if "jitter" in connection and "delay" not in connection:
            raise RuntimeError(f"Cannot specify some jitter and not some delay for connection {connection} of {entity.name}")

        # modify loss
        if "loss" in connection:
            if isinstance(connection["loss"], str) and utils.match_tc_percent(connection["loss"]):
                cmd += f" loss {connection['loss']}"
            else:
                raise RuntimeError(f"Loss for connection {connection} of {entity.name} must be a int followed by %")

        # modify corrupt
        if "corrupt" in connection:
            if isinstance(connection["corrupt"], str) and utils.match_tc_percent(connection["corrupt"]):
                cmd += f" corrupt {connection['corrupt']}"
            else:
                raise RuntimeError(f"Corruption rate for connection {connection} of {entity.name} must be a int followed by %")

        # modify duplicate
        if "duplicate" in connection:
            if isinstance(connection["duplicate"], str) and utils.match_tc_percent(connection["duplicate"]):
                cmd += f" duplicate {connection['duplicate']}"
            else:
                raise RuntimeError(f"Duplicate rate for connection {connection} of {entity.name} must be a int followed by %")

        # modify reorder
        if "reorder" in connection:
            if isinstance(connection["reorder"], str) and utils.match_tc_percent(connection["reorder"]):
                cmd += f" reorder {connection['reorder']}"
            else:
                raise RuntimeError(f"Reorder rate for connection {connection} of {entity.name} must be a int followed by %")

        if len(cmd) != cmd_original_length:
            return cmd

        return ""

    def generate_timers(self, entity: entities.Entity, entity_config) -> None:
        '''Generate commands to handle the timers.'''

        connections = config_parser.extract_connections(entity_config)

        for conn in connections:
            if "timers" not in conn or conn["timers"] is None:
                continue

            first_hop = conn['path'].split("->")[0] if "->" in conn["path"] else conn["path"]
            if_id = self.get_interface_id(entity.name, first_hop)
            if if_id is None:
                raise RuntimeError(f"Unable to find interface for {entity.name} and {first_hop}")
            if_name = utils.get_interface_name(if_id, entity.name)

            for timer in conn["timers"]:
                # check if valid impairment
                if timer["option"] not in constants.CONNECTION_IMPAIRMENTS:
                    raise RuntimeError(f"{timer} for {conn} of {entity.name} is setting a timer on {timer['option']} which is not a connection impairment")

                # check if there is an original value
                if timer["option"] not in conn:
                    raise RuntimeError(f"Cannot modify {timer['option']} for {conn} of {entity.name} with a timer because an original value is not set")

                # generate commands for traffic impairment
                cmds = self.generate_traffic_impairments(entity, entity_config)

                # get command for particular option
                command = next((cmd for cmd in cmds if utils.filter_cmd(timer["option"], cmd, if_name)), None)
                if command is None:
                    raise RuntimeError(f"Unexpected length of commands for timer {timer['option']} for connection {conn} of entity {entity}")

                # generate new command
                if "mtu" in command:
                    cmd_modify = constants.MODIFY_IMPAIRMENT.format(timer["start"], constants.MTU_OPTION.format(if_name, timer["newValue"]))
                elif "txqueuelen" in command:
                    cmd_modify = constants.MODIFY_IMPAIRMENT.format(timer["start"], constants.BUFFER_SIZE_OPTION.format(if_name, timer["newValue"]))
                else:
                    connection = copy.deepcopy(conn)
                    connection[timer["option"]] = timer["newValue"]
                    cmd = self.generate_tc_command(entity, if_name, connection)
                    cmd_modify = constants.MODIFY_IMPAIRMENT_DELETE_TC.format(timer['start'], if_name, cmd)
                entity.add_command(cmd_modify, background=True)

                # generate command to restore original value for impairment
                if "duration" in timer:
                    cmds_reset = self.generate_traffic_impairments(entity, entity_config)
                    command = next((cmd for cmd in cmds_reset if utils.filter_cmd(timer["option"], cmd, if_name)), None)
                    if command is None:
                        raise RuntimeError(f"Unexpected length of commands for timer {timer['option']} for connection {conn} of entity {entity}")

                    if "tc" in command:
                        cmd_reset = constants.MODIFY_IMPAIRMENT_DELETE_TC.format(timer["start"] + timer["duration"], if_name, command)
                    else:
                        cmd_reset = constants.MODIFY_IMPAIRMENT.format(timer['start'] + timer['duration'], command)
                    entity.add_command(cmd_reset, background=True)
