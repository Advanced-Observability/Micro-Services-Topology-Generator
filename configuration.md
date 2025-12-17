# Configuration file

## About

This file explains the configuration file format expected by the tool.

## Structure of a configuration file

A configuration file is a `yml` file describing all the entities of the architecture along with the network links between them.

### Specifying a service

A service is specified by the following template:

```yml
<service_name>:
  type: service
  port: <port>
  expose: true|false
  endpoints:
    - entrypoint: <entrypoint>
      psize: <packet_size>
      connections:
        - path: <path>
          url: <url>
```

The values in the template are described as follows:
- `<service_name>` is the name of the service;
- `<port>` is the port used to interact with the service;
- `expose` specifies whether or not the service port will be accessible to the host (only for Docker). If omitted, port is exposed;
- `<entrypoint>` URL at which the service can be contacted;
- `<packet_size>` is the size of the packets (or responses) returned by the service for the endpoint;
- `connections` represent the request**s** that the service will make to other services before replying to the requests where `<path>` describes the path made by the request and `<url>` is the url to contact at the end of the path.

Connections towards the other services need to be specified as `<path>` and `<url>` by either:
- Using a path when they are multiple hops before reaching the destination. An example of a path is `r1->db` for a service that contacts the service with the name `db` by going through the router with the name `r1`;
- Using the name of another service when the 2 services are directly connected (e.g. `db`).

Multiple paths can be specified if a service contacts more than one service, as shown below:
```yml
connections:
  - path: <path1>
    url: <url1>
  - path: <path2>
    url: <url2>
```

If the microservice does not contact any other service, the following lines can be omitted.
```yml
  connections:
    - path: <path>
      url: <url>
```

Therefore, `connections` represents the interconnections between the various microservices.

### Specifying a router

A router is specified by the following template:
```yml
<router_name>:
  type: router
  connections:
    - path: <connection>
```

The values in the template are the following:
- `connection` represents the service/router to which the router is connected.

The specified `connections` need to be coherent with the `connections` for the other entities.
For instance, if a service specified `r1->r2->db`, the router `r1` needs to specify `r2` as connection while router `r2` need to specify `db`.

### Using an external container

Since v0.0.5, MSTG allows the usage of existing Docker containers.

The following template can be used to integrate an existing Docker container in the generated architecture.

```yml
frontend:
  type: external
  image: <dockerImage>
  ports:
    - <port>
  connections:
    - path: <path>
```

The values in the template are the following:
- `dockerImage` is the name of the Docker image, which **MUST** be available on the host;
- `port` is a port to be opened for the container. The container can have multiple open ports;
- `path`is a connection as specified for a router. The container can have multiple connections.

> [!WARNING]
> This functionality comes with some additional requirements:
> - The image must be available on the host. The generated configurations will **not** pull from Docker hub;
> - The command `ip` must be available in the container in order to configure the routes;
> - If you decide to use IOAM, the command `sysctl` must be available in the container;
> - If you decide to use the network options, the command `tc` must be available in the container.

> [!CAUTION]
> Due to the requirements imposed by CLT, one should refrain from using CLT with existing Docker containers.

### Specifying a firewall

Since v0.0.6, MSTG allows to add firewalls to the generated topologies.

The firewall uses `iptables` under the hood.

A firewall can be specified with the following template:
```yml
<name>:
  type: firewall
  default: <ACCEPT|DROP>
  connections:
    - path: <nexthop>
  rules:
    - source: <source>
      sport: <sport>
      destination: <destination>
      dport: <dport>
      protocol: <udp|tcp>
      action: <action>
      extension: <extension>
    - custom: <custom>
```

The values in the template are the following:
- `default` is the default action of the firewall;
- `nexthop` is a connection as specified for a router. The firewall can have multiple connections;
- `source` is the source of the packets;
- `sport` is the source port. Use `"*"` to signify any port;
- `destination` is the destination of the packets;
- `dport` is the destination port. Use `"*"` to signify any port;
- `protocol` is the network protocol of the packets;
- `action` is any builtin target available in `iptables`. See [man page of iptables](https://linux.die.net/man/8/iptables);
- `extension` is any match extension available in `iptables`, such as `conntrack`. See [man page of iptables](https://linux.die.net/man/8/iptables);
- `custom` is a custom `iptables` command. It **cannot** be used with other fields.

A firewall can have many rules.

### Network options

Network parameters can be configured on the connections between entities, they must be added in the connection description. The available parameter fields are:
- `mtu`: Adjusts the Maximum Transmission Unit (MTU). Warning: This tool uses IPv6, so the MTU must be at least 1280 bytes. Using a smaller MTU will not work;
- `buffer_size`: Sets the buffer size;
- `rate`: Sets the link rate;
- `delay`: Sets the delay;
- `jitter`: Sets the jitter;
- `reorder`: Sets the rate of packet reordering;
- `corrupt`: Sets the rate of corrupt packets;
- `duplicate`: Sets the rate of duplicate packets;
- `loss`: Sets the packet loss rate.

These options are based on [tc-netem](https://man7.org/linux/man-pages/man8/tc-netem.8.html) and [iproute2](https://wiki.linuxfoundation.org/networking/iproute2).

See [6_modify_traffic.yml](./configuration_examples/6_modify_traffic.yml) for an example using network options.

### Timers for network options

Timers can be specified to modify network parameters over a certain period of time.

To create a timer, add a `timers` field in the connection description, followed by a list of timers. Each timer should include the following fields:
- `option`: The parameter to be modified;
- `start`: The time in seconds after which the parameter will be modified;
- `duration`: The time in seconds after which the parameter will be restored to its original value;
- `newValue`: The new value of the parameter.

See [7_timers.yml](./configuration_examples/7_timers.yml) for an example using these timers.

## Examples

Example of a simple valid configuration file:

```yml
frontend:
  type: service
  port: 80
  endpoints:
    - entrypoint: /
      psize: 128
      connections:
        - path: r1->db
          url: /
          mtu: 2500
r1:
  type: router
  connections:
    - path: db
db:
  type: service
  port: 7000
  expose: false
  endpoints:
    - entrypoint: /
      psize: 64
```

More examples are available in the folder [`configuration_examples`](./configuration_examples/).
