// Utilities for service

package main

import (
	"fmt"
	"log"
	"math/rand"
	"net"
	"os"
	"reflect"
	"strconv"
	"strings"
	"time"

	"gopkg.in/yaml.v3"
)

const (
	DEFAULT_CONFIG_PATH     = "../config.yml"                                                  // Default path to config file
	VERSION                 = "0.0.8"                                                          // Version of the service
	DEFAULT_PACKET_SIZE     = 64                                                               // Default packet size in bytes
	DEFAULT_JAEGER_HOSTNAME = "jaeger"                                                         // Default Jaeger hostname
	MAX_LEN_TRACE_RES       = 12                                                               // Maximum number of characters from random string into OTEL
	REQUEST_TIMEOUT         = 5 * time.Second                                                  // Timeout when contacting another service
	CHARSET                 = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" // Set for randome string
	MIN_PACKET_SIZE         = 12                                                               // Minimum size of packets
)

// Get file descriptor used by the socket for the given connection
// From https://github.com/higebu/netfd/blob/master/netfd.go
func GetFdFromConn(c net.Conn) int {
	v := reflect.Indirect(reflect.ValueOf(c))
	conn := v.FieldByName("conn")
	netFD := reflect.Indirect(conn.FieldByName("fd"))
	pfd := netFD.FieldByName("pfd")
	fd := int(pfd.FieldByName("Sysfd").Int())
	return fd
}

// Generates random string of n bytes
func randomString(n int) string {
	sb := strings.Builder{}
	sb.Grow(n)
	for range n {
		sb.WriteByte(CHARSET[rand.Intn(len(CHARSET))])
	}
	return sb.String()
}

// Returns address of service
func getAddress(services map[string]Service, service string) string {
	if _, ok := services[service]; !ok {
		log.Println("Service " + service + " not found in config file")
		return ""
	}
	if services[service].Port == 0 {
		if strings.Contains(services[service].Addr, ":") {
			return services[service].Addr
		} else {
			log.Println("Port not found for service " + service)
			return ""
		}
	}

	return services[service].Addr + ":" + strconv.Itoa(services[service].Port)
}

// Reads config file and returns map of services
func readConfig(file string) (map[string]Service, error) {
	yfile, err := os.ReadFile(file)
	if err != nil {
		return nil, err
	}

	data := make(map[string]Service)

	err2 := yaml.Unmarshal(yfile, &data)
	if err2 != nil {
		return nil, err2
	}

	// modify data for name indexing
	for name, service := range data {
		// remove routers -> a service should be unaware of them
		if service.Type != "service" {
			delete(data, name)
		}

		// save name in Name field
		if entry, ok := data[name]; ok {
			entry.Name = name
			entry.Addr = name
			data[name] = entry
		}
	}

	for name, service := range data {

		// create the _Endpoints and _MaxPsize field, indexed by the entrypoint string
		if len(service.Endpoints) > 0 {
			service._Endpoints = make(map[string]Endpoint)
			for _, endp := range service.Endpoints {
				if _, ok := service._Endpoints[endp.Entrypoint]; ok {
					log.Fatal("Multiple identical entrypoints in service " + service.Name + ": " + endp.Entrypoint)
				}

				// set default packet size
				if endp.Psize == 0 {
					endp.Psize = DEFAULT_PACKET_SIZE
				}

				// need to be MIN_PACKET_SIZE bytes minimum
				endp.Psize = max(endp.Psize, MIN_PACKET_SIZE)

				// compute maximum packet size in all endpoints
				service._MaxPsize = max(service._MaxPsize, endp.Psize)

				// keep last hop if Conn contains some paths
				if len(endp.Connections) > 0 {
					for index, conn := range endp.Connections {
						if strings.Contains(conn.Path, "->") {
							hops := strings.Split(conn.Path, "->")
							endp.Connections[index].Path = hops[len(hops)-1]
						}
					}
				}

				// assign new value
				service._Endpoints[endp.Entrypoint] = endp
			}
		}

		// assign new value
		data[name] = service

	}

	return data, nil
}

// Parse the CLI arguments
func parseCliArguments() {
	if len(os.Args) == 2 && os.Args[1] != "help" {
		conf.configPath = os.Args[1]
	} else if len(os.Args) == 1 {
		conf.configPath = DEFAULT_CONFIG_PATH
	} else {
		fmt.Println("Usage: " + os.Args[0] + " <config file>")
		os.Exit(1)
	}
}

// Parse environment variables.
func parseEnvVariables() {
	conf.ownName = os.Getenv("SERVICE_NAME")
	if conf.ownName == "" {
		log.Fatal("SERVICE_NAME environment variable not set")
	}

	if _, ok := conf.services[conf.ownName]; !ok {
		log.Fatal("SERVICE_NAME not found in config file")
	}

	conf.enableCLT = os.Getenv("CLT_ENABLE") == "1"
	conf.versionIP = os.Getenv("IP_VERSION")
	conf.enableJaeger = os.Getenv("JAEGER_ENABLE") == "True"
	conf.enableIOAM = os.Getenv("IOAM_ENABLE") == "1"
	conf.httpVersion = os.Getenv("HTTP_VERSION")
	conf.certFile = os.Getenv("CERT_FILE")
	conf.keyFile = os.Getenv("KEY_FILE")

	if conf.httpVersion == "" {
		log.Println("HTTP_VERSION env. variable not specified. Using HTTP by default.")
		conf.httpVersion = "http"
	}

	if os.Getenv("JAEGER_HOSTNAME") != "" {
		conf.jaegerHostname = os.Getenv("JAEGER_HOSTNAME")
	} else {
		conf.jaegerHostname = DEFAULT_JAEGER_HOSTNAME
	}

	if conf.enableCLT || conf.enableIOAM {
		if conf.versionIP == "4" {
			log.Fatal("IOAM/CLT cannot be used with IPv4")
		}
		conf.versionIP = "6"
	} else {
		if conf.versionIP == "" {
			log.Println("IP_VERSION environment variable not set")
			log.Println("Using IPv4 by default")
			conf.versionIP = "4"
		} else {
			if conf.versionIP != "4" && conf.versionIP != "6" {
				log.Fatal("Invalid IP version specified in IP_VERSION environment variable: 4 or 6 expected")
			}
		}
	}
}

// Print info about the service.
func serviceInfo() {
	fmt.Println("=== Starting service " + conf.ownName + " ===")
	fmt.Println("Version: " + VERSION)
	fmt.Println("Config file: " + conf.configPath)
	fmt.Println("Address: " + conf.services[conf.ownName].Addr)
	fmt.Println("Port: " + strconv.Itoa(conf.services[conf.ownName].Port))
	fmt.Println("IP version: " + conf.versionIP)
	fmt.Println("HTTP version: " + conf.httpVersion)

	if conf.enableIOAM {
		fmt.Println("Using IOAM")
	}

	if conf.enableJaeger {
		fmt.Println("Using Jaeger (hostaname: " + conf.jaegerHostname + ")")
	}

	if conf.enableCLT {
		fmt.Println("Using CLT")
	}

	if len(conf.services[conf.ownName]._Endpoints) != 0 {
		fmt.Println("Entrypoints:")
		for endp, endpoint := range conf.services[conf.ownName]._Endpoints {
			if len(endpoint.Connections) > 0 {
				fmt.Println("\t- " + endp + " which will contact:")
				for _, conn := range endpoint.Connections {
					fmt.Println(" \t\t- " + conn.Path + " at " + conn.Url)
				}
			} else {
				fmt.Println("\t- " + endp)
			}
		}
	}
}
