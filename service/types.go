// Types for the service.

package main

import "go.opentelemetry.io/otel/trace"

// Configuration of the service
type Config struct {
	tracer         trace.Tracer       // OTEL tracer
	configPath     string             // path towards config file
	randStr        string             // random string for responses
	services       map[string]Service // all services indexed by service name
	ownName        string             // own service name
	enableCLT      bool               // using CLT or not
	enableIOAM     bool               // enable IOAM only
	versionIP      string             // version of IP (4, 6)
	enableJaeger   bool               // using Jaeger or not
	jaegerHostname string             // jaeger hostname
	httpVersion    string             // version of http (http or https)
	certFile       string             // path to certificate for https
	keyFile        string             // path to key for https
}

// A service in the config file
type Service struct {
	Type       string
	Name       string
	Addr       string
	Port       int
	Endpoints  []Endpoint          // list of endpoints that can be queried
	_Endpoints map[string]Endpoint // field built for easier indexing
	_MaxPsize  int                 // maximum packet size in all endpoints
}

// Represent a reachable endpoint of the service
type Endpoint struct {
	Entrypoint  string       // path to reach endpoint
	Psize       int          // size of returned packets
	Connections []Connection // list of services to connect to
}

// Represent a connection of a service
type Connection struct {
	Path        string
	Url         string
	Mtu         int
	Buffer_size int
	Rate        string
	Delay       string
	Jitter      string
	Loss        string
	Corrupt     string
	Duplicate   string
	Reorder     string
	Timers      []map[string]string
}
