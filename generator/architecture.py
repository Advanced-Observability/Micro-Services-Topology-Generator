'''
Represent the architecture for the generator.
'''

import copy

import config_parser, kubernetes
from entities import *
from utils import *

class Architecure:
    '''Represent the architecture.'''

    def __init__(self, filename : str, config):
        self.filename = filename
        self.config = config
        self.graph = None
        self.entities = []
        self.dockerNetworks = []
        self.kubernetes = kubernetes.Kubernetes() if output_is_k8s() else None
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
        print_info("Config seems ok")

        # Create graph
        print("Creating graph based on configuration...")
        self.graph = config_parser.build_directed_graph(self.config)
        print_info("Generated graph")

        # Generate entities and parse connections
        print("Creating entities based on configuration...")
        self.generate_entities()
        print_info("Generated entities")

        self.parse_end_to_end_connections()
        print_info("Parsed e2e connections")

        # Generate docker networks
        print("Creating docker networks...")
        self.generate_docker_networks()
        print_info("Generated docker networks")

        # Associate entities to docker networks
        print("Associating entities with docker networks...")
        self.associate_docker_networks()
        print_info("Associated docker network to entities")

        # Generating ip route cmd
        print("Generating ip route commands...")
        self.generate_ip_route_cmds()
        print_info("Generated ip route commands")

        # Add entries into /etc/hosts of services
        print("Associating hosts that are connected to each others...")
        self.modify_etc_hosts()
        print_info("Associated hosts that are connected to each others")

        # Associate each entity to the ones on which it depends
        print("Associating entities to their dependencies...")
        self.associate_dependencies()
        print_info("Associated entities to their dependencies")

        # Generate additional commands to configure entities
        print("Generating additional commands...")
        self.generate_additional_commands()
        print_info("Generated additional commands")

        # Generate timers to trigger commands
        print("Generate timers...")
        self.generate_timers()
        print_info("Generated timers")

    def print(self):
        """Print the architecture"""
        for net in self.dockerNetworks:
            print(net)
        for e in self.entities:
            print(e)
        if self.kubernetes:
            print(self.kubernetes)

    def pretty_print(self):
        """Print in a pretty way the architecture."""
        for net in self.dockerNetworks:
            print(net.pretty())
        for e in self.entities:
            print(e.pretty())
        if self.kubernetes:
            print(self.kubernetes.pretty())

    def generate_entities(self):
        '''Generate list of entities from the configuration.'''
        for entity in self.config:
            if self.config[entity]["type"] == "service":
                self.entities.append(Service(entity, self.config[entity]))
            elif self.config[entity]["type"] == "router":
                self.entities.append(Router(entity))
            else:
                raise RuntimeError("Entity {} has unexpected type {}".format(entity, self.config[entity]["type"]))

    def find_entity(self, name : str):
        '''
        Find an entity in the architecture with the given `name`.
        If not found, return None.
        '''
        for entity in self.entities:
            if entity.name == name:
                return entity

        return None

    def find_service(self, name : str):
        '''
        Find service with given `name`.
        If not found, return None.
        '''
        for entity in self.entities:
            if entity.name == name and isinstance(entity, Service):
                return entity
        return None
    
    def find_network(self, name : str):
        '''
        Find DockerNetwork with given `name`.
        If not found, return None.
        '''

        for net in self.dockerNetworks:
            if net.name == name:
                return net, self.dockerNetworks.index(net)
            
        return None

    def parse_end_to_end_connections(self) -> None:
        '''Parse E2E connections for the services based on the architecture.'''

        for entity in self.entities:
            if isinstance(entity, Service):
                e = config_parser.get_entity(self.config, entity.name)
                if e is None:
                    raise RuntimeError(f"Unable to get entity {entity.name}")

                connections = []
                for endpoint in e["endpoints"]:
                    if "connections" in endpoint and endpoint["connections"] is not None:
                        connections.extend(conn["path"] for conn in endpoint["connections"])

                entity.e2eConnections.extend(connections)

    def get_interface_id(self, source : str, dest : str) -> int:
        '''
        Return the interface id to contact `dest` from `source`.
        If not found, return None.
        '''

        entity = self.find_entity(source)
        if entity is None:
            raise RuntimeError(f"Cannot find entity {source} in get_interface_id")

        names = [net["name"] for net in entity.attachedNetworks]

        # every service is connected to the telemetry network if otel/jaeger is used
        if isinstance(entity, Service) and is_using_jaeger() and output_is_compose():
            names.append("network_telemetry")

        if output_is_compose():
            """
            Docker does NOT assign interfaces in the order described in the docker compose file.
            It uses a dictionay => need to rely on the alphabetical order.
            """
            names.sort()
        elif output_is_k8s():
            """For Kubernetes, we keep the order of the list."""
            pass
        
        netName1 = DockerNetwork.generate_name(source, dest)
        netName2 = DockerNetwork.generate_name(dest, source)
        if netName1 in names:
            # +1 for k8s because eth0 is assigned by default cni
            return names.index(netName1) if output_is_compose() else names.index(netName1)+1
        elif netName2 in names:
            # +1 for k8s because eth0 is assigned by default cni
            return names.index(netName2) if output_is_compose() else names.index(netName2)+1
        else:
            raise RuntimeError(f"Cannot find network for {netName1} and {netName2}")

    def modify_etc_hosts(self) -> None:
        """
        Associate `extra_hosts` to services with connections to other entities.
        Required for docker compose to prevent DNS resolution on the wrong network.
        Otherwise, it uses the telemetry network for communication between the services.
        """
        for entity in self.entities:
            if not isinstance(entity, Service):
                continue

            for e2e in entity.e2eConnections:
                # path
                if "->" in e2e:
                    hops = e2e.split("->")

                    first = hops[0]
                    penultimate = hops[len(hops) - 2]
                    last = hops[len(hops) - 1]

                    # forward path
                    sharedPenultimateLast = self.get_shared_network(penultimate, last)
                    if sharedPenultimateLast is None:
                        raise RuntimeError(f"Unable to get network between {penultimate} and {last} in associate_extra_hosts")

                    entity.extraHosts.add((last, sharedPenultimateLast.endIP))

                    # reverse path
                    sharedBeginFirstHop = self.get_shared_network(entity.name, first)
                    if sharedBeginFirstHop is None:
                        raise RuntimeError(f"Unable to get network between {entity.name} and {first} in associate_extra_hosts")

                    lastService = self.find_service(last)
                    if lastService is None:
                        raise RuntimeError("Unable to find service " + last)

                    lastService.extraHosts.add((entity.name, sharedBeginFirstHop.beginIP))

                # direct connection
                else:
                    net = self.get_shared_network(entity.name, e2e)
                    if net is None:
                        raise RuntimeError(f"Unable to get shared network between {entity.name} and {e2e} in associate_extra_hosts")

                    # forward path
                    entity.extraHosts.add((e2e, net.endIP))

                    # reverse path
                    service = self.find_service(e2e)
                    if service is None:
                        raise RuntimeError("Unable to find service " + e2e)

                    service.extraHosts.add((entity.name, net.beginIP))

    def associate_dependencies(self) -> None:
        """Associate all the entities to the ones they depend on"""

        for e in self.config:
            entity = self.find_entity(e)
            if entity is None:
                raise RuntimeError(f"Cannot find entity {e} in associate_dependencies")

            connections = config_parser.extract_connections(self.config[e])
            connections = [conn["path"] for conn in connections]

            for connection in connections:
                if "->" in connection: # connection is a path
                    entity.depends_on.update(connection.split("->"))
                else: # connection is direct
                    entity.depends_on.add(connection)

    def get_shared_network(self, begin : str, end : str):
        """
        Get the Docker network shared by `begin` and `end`.
        None if not found.
        """
        for net in self.dockerNetworks:
            if net.begin == begin and net.end == end:
                return net

        return None

    def generate_ip_route_cmds(self) -> None:
        '''Generate the IP route commands to configure the services.'''

        for e in self.entities:
            if not isinstance(e, Service):
                continue

            for e2e in e.e2eConnections:

                # connection is path
                if "->" in e2e:
                    self.ip_route_path_connection(e, e2e)

                # connection is direct - only required if IOAM/CLT
                elif is_using_clt():
                    self.ip_route_direct_connection(e, e2e)

    def ip_route_path_connection(self, sourceEntity : Service, path : str) -> None:
        '''
        Generate ip route commands for `path` starting from `sourceEntity`.
        '''
        hops = path.split("->")
        hops.insert(0, sourceEntity.name)
        sizeIOAMData = len(hops) * 12

        penultimate = hops[len(hops) - 2]
        end = hops[len(hops)-1]

        # get source subnet
        sharedSourceFirstHop = self.get_shared_network(hops[0], hops[1])
        if sharedSourceFirstHop is None:
            raise RuntimeError(f"Unable to get network shared by {hops[0]} and {hops[1]}")
        sourceIPSubnet = sharedSourceFirstHop.subnet

        # get dest subnet
        sharedPenultimateEnd = self.get_shared_network(penultimate, end)
        if sharedPenultimateEnd is None:
            raise RuntimeError(f"Cannot get network shared by {penultimate} and {end}")
        destIPSubnet = sharedPenultimateEnd.subnet

        # configure all entities on path
        for i in range(0, len(hops)):
            prev = hops[i-1] if i > 0 else None
            curr = hops[i]
            next = hops[i+1] if i < len(hops) - 1 else None

            currEntity = self.find_entity(curr)
            if currEntity is None:
                raise RuntimeError("Unable to get entity " + curr)
            
            if next is not None:
                nextEntity = self.find_entity(next)
                if nextEntity is None:
                    raise RuntimeError("Unable to get entity " + next)
                
            if prev is not None:
                prevEntity = self.find_entity(prev)
                if prevEntity is None:
                    raise RuntimeError("Unable to get entity " + prev)

            # towards dest
            if i != len(hops) - 1:
                cmd = ""

                nextNet = self.get_shared_network(curr, next)
                if nextNet is None:
                    raise RuntimeError(f"Cannot get network shared by {curr} and {next}")
                
                if is_using_clt():
                    cmd = TEMPLATE_IP6_ROUTE_PATH.format(destIPSubnet, sizeIOAMData, nextNet.endIP)
                elif topology_is_ipv4():
                    cmd = TEMPLATE_IP4_ROUTE_PATH.format(destIPSubnet, nextNet.endIP)
                else:
                    cmd = TEMPLATE_IP6_ROUTE_PATH_NO_IOAM.format(destIPSubnet, nextNet.endIP)

                currEntity.ipRouteCommands.append(cmd)

            # towards source
            if i != 0:
                cmd = ""
                
                prevNet = self.get_shared_network(prev, curr)
                if prevNet is None:
                    raise RuntimeError(f"Cannot get network shared by {prev} and {curr}")
            
                if topology_is_ipv4():
                    cmd = TEMPLATE_IP4_ROUTE_PATH.format(sourceIPSubnet, prevNet.beginIP)
                else:
                    cmd = TEMPLATE_IP6_ROUTE_PATH_NO_IOAM.format(sourceIPSubnet, prevNet.beginIP)
                
                currEntity.ipRouteCommands.append(cmd)

    def ip_route_direct_connection(self, sourceEntity : Service, dest : str) -> None:
        '''
        Generate ip route command for direct connection between `sourceEntity` and `dest`.
        Only required for IOAM/CLT over IPv6.
        '''
        net = self.get_shared_network(sourceEntity.name, dest)
        if net is None:
            raise RuntimeError(f"Unable to get shared network for {sourceEntity.name} and {dest} in generate_ip_route_cmds")

        # towards dest

        # get interface id (ethX) of source to contact end host
        interfaceID = self.get_interface_id(sourceEntity.name, dest)
        if interfaceID is None:
            raise RuntimeError(f"Unable to get interface of {sourceEntity.name} to contact {dest}")
        
        sourceEntity.ipRouteCommands.append(TEMPLATE_IP6_ROUTE_DIRECT_CONNECTION.format(net.endIP, 36, interfaceID))

    def generate_docker_networks(self) -> None:
        '''Generate all docker networks based on the architecture.'''
        for pair in self.graph.edges:
            net = DockerNetwork(pair[0], pair[1])
            self.dockerNetworks.append(net)

    def associate_docker_networks(self) -> None:
        '''Associate all the entities to the appropriate docker networks.'''
        for entity in self.entities:
            for dockerNet in self.dockerNetworks:
                ip = None
                if dockerNet.begin == entity.name:
                    ip = dockerNet.beginIP
                elif dockerNet.end == entity.name:
                    ip = dockerNet.endIP
                if ip is not None:
                    entity.attachedNetworks.append({
                        "name": dockerNet.name,
                        "ip": ip
                    })

    def generate_traffic_impairments(self, entity : Entity, entityConfig) -> list:
        '''Generate the list of commands to impair the traffic of `entity` with the given `entityConfig`.'''
        connections = config_parser.extract_connections(entityConfig)

        commands = []

        for conn in connections:
            firstHop = conn['path'].split("->")[0] if "->" in conn["path"] else conn["path"]

            interface = self.get_interface_id(entity.name, firstHop)
            if interface is None:
                raise RuntimeError(f"Cannot find interface to contact {firstHop} from {entity.name}")

            # modify mtu
            if "mtu" in conn and type(conn["mtu"]) is int and conn["mtu"] >= 1280:
                cmd = MTU_OPTION.format(interface, conn['mtu'])
                commands.append(cmd)
            elif "mtu" not in conn:
                pass
            else:
                raise RuntimeError(f"MTU must be an integer and greater than 1280 because we are using IPv6 for connection {conn} of {entity.name}")

            # modify buffer size
            if "buffer_size" in conn and type(conn["buffer_size"]) is int:
                cmd = BUFFER_SIZE_OPTION.format(interface, conn['buffer_size'])
                commands.append(cmd)
            elif "buffer_size" not in conn:
                pass
            else:
                raise RuntimeError(f"Buffer size must be an integer for connection {conn} of {entity.name}")

            # build command
            ipTcCommand = f"tc qdisc add dev eth{interface} root netem"
            ipTcCommandOriginalLength = len(ipTcCommand)

            # modify rate
            if "rate" in conn and type(conn["rate"]) is str and match_tc_rate(conn["rate"]):
                ipTcCommand+=(f" rate {conn['rate']}")
            elif "rate" not in conn:
                pass
            else:
                raise RuntimeError(f"Rate for connection {conn} of {entity.name} must be a int followed by a rate unit valid for tc")

            # modify delay
            if "delay" in conn and type(conn['delay']) is str and match_tc_time(conn["delay"]):
                ipTcCommand+=(f" delay {conn['delay']}")
                if "jitter" in conn and type(conn["jitter"]) is str and match_tc_time(conn["jitter"]):
                    ipTcCommand+=(f" {conn['jitter']}")
                elif "jitter" not in conn:
                    pass
                else:
                    raise RuntimeError(f"Jitter for connection {conn} of {entity.name} must be a int followed by a time unit valid for tc")
            elif "delay" not in conn:
                pass
            else:
                raise RuntimeError(f"Delay for connection {conn} of {entity.name} must be a int followed by a time unit valid for tc")

            # modify jitter
            if "jitter" in conn and "delay" not in conn:
                raise RuntimeError(f"Cannot specify some jitter and not some delay for connection {conn} of {entity.name}")

            # modify loss
            if "loss" in conn and type(conn["loss"]) is str and match_tc_percent(conn["loss"]):
                ipTcCommand+=(f" loss {conn['loss']}")
            elif "loss" not in conn:
                pass
            else:
                raise RuntimeError(f"Loss for connection {conn} of {entity.name} must be a int followed by %")

            # modify corrupt
            if "corrupt" in conn and type(conn["corrupt"]) is str and match_tc_percent(conn["corrupt"]):
                ipTcCommand+=(f" corrupt {conn['corrupt']}")
            elif "corrupt" not in conn:
                pass
            else:
                raise RuntimeError(f"Corruption rate for connection {conn} of {entity.name} must be a int followed by %")

            # modify duplicate
            if "duplicate" in conn and type(conn["duplicate"]) is str and match_tc_percent(conn["duplicate"]):
                ipTcCommand+=(f" duplicate {conn['duplicate']}")
            elif "duplicate" not in conn:
                pass
            else:
                raise RuntimeError(f"Duplicate rate for connection {conn} of {entity.name} must be a int followed by %")

            # modify reorder
            if "reorder" in conn and type(conn["reorder"]) is str and match_tc_percent(conn["reorder"]):
                ipTcCommand+=(f" reorder {conn['reorder']}")
            elif "reorder" not in conn:
                pass
            else:
                raise RuntimeError(f"Reorder rate for connection {conn} of {entity.name} must be a int followed by %")

            if len(ipTcCommand) != ipTcCommandOriginalLength: # check that some options were added
                commands.append(ipTcCommand)

        return commands

    def generate_additional_commands(self) -> None:
        '''Generate extra commands to configure the entities of the architecture.'''
        for entity in self.entities:
            conf = config_parser.get_entity(self.config, entity.name)
            if conf is None:
                raise RuntimeError(f"Entity {entity.name} has not been found")

            cmds = self.generate_traffic_impairments(entity, conf)
            entity.additionalCommands.extend(cmds)

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
                
                firstHop = conn['path'].split("->")[0] if "->" in conn["path"] else conn["path"]
                interface = self.get_interface_id(entity.name, firstHop)
                if interface is None:
                    raise RuntimeError(f"Unable to find interface for {entity.name} and {firstHop}")

                for timer in conn["timers"]:
                    # check if valid impairment
                    if timer["option"] not in CONNECTION_IMPAIRMENTS:
                        raise RuntimeError(f"{timer} for {conn} of {entity.name} is setting a timer on {timer['option']} which is not a connection impairment")

                    # check if there is an original value
                    if timer["option"] not in conn:
                        raise RuntimeError(f"Cannot modify {timer['option']} for {conn} of {entity.name} with a timer because an original value is not set")

                    # create modified version of config
                    newConfig = copy.deepcopy(e)
                    if newConfig["type"] == "router":
                        if "connections" in newConfig and newConfig["connections"] is not None:
                            for connection in newConfig["connections"]:
                                if connection == conn:
                                    connection[timer["option"]] = timer["newValue"]
                    elif newConfig["type"] == "service":
                        for endpoint in newConfig["endpoints"]:
                            if "connections" in endpoint and endpoint["connections"] is not None:
                                for connection in endpoint["connections"]:
                                    if connection == conn:
                                        connection[timer["option"]] = timer["newValue"]

                    # generate command for traffic impairment
                    cmds = self.generate_traffic_impairments(entity, newConfig)
                    filtered = list(filter(lambda cmd: filterCmd(timer['option'], cmd, f"eth{interface}"), cmds))
                    if len(filtered) != 1:
                        raise RuntimeError(f"Unexpected length of commands for timer {timer['option']} for connection {conn} of entity {entity}")
                    index = filtered[0].find("eth")
                    if index == -1:
                        raise RuntimeError(f"Unable to find interface for {conn} of {entity.name}")
                    index+=3 # skip "eth"

                    # find interface id
                    interfaceID = ""
                    while filtered[0][index].isdigit():
                        interfaceID+=filtered[0][index]
                        index+=1

                    if "tc" in filtered[0]:
                        cmdModify = MODIFY_IMPAIRMENT_DELETE_TC.format(timer['start'], interfaceID, filtered[0])
                    else:
                        cmdModify = MODIFY_IMPAIRMENT.format(timer['start'], filtered[0])
                    entity.additionalCommands.append(cmdModify)

                    # generate command to restore original value for impairment
                    if "duration" in timer:
                        cmdsReset = self.generate_traffic_impairments(entity, e)
                        filtered = list(filter(lambda cmd: filterCmd(timer['option'], cmd, f"eth{interface}"), cmdsReset))
                        if len(filtered) != 1:
                            raise RuntimeError(f"Unexpected length of commands for timer {timer['option']} for connection {conn} of entity {entity}")

                        if "tc" in filtered[0]:
                            cmdReset = MODIFY_IMPAIRMENT_DELETE_TC.format(timer["start"] + timer["duration"], interfaceID, filtered[0])
                        else:
                            cmdReset = MODIFY_IMPAIRMENT.format(timer['start'] + timer['duration'], filtered[0])

                        entity.additionalCommands.append(cmdReset)
