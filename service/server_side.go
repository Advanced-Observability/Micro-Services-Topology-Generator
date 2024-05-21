// Code for the service acting as a server.
// Listening for HTTP(S) requests.

package main

import (
	"fmt"
	"log"
	"net"
	"net/http"
	"strconv"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel/attribute"
)

// Handle HTTP(S) requests with Jaeger
func getRootJaeger(writer http.ResponseWriter, r *http.Request) {
	entrypoint := r.URL.Path

	// start span
	ctx, span := conf.tracer.Start(r.Context(), entrypoint[1:])
	defer span.End()

	// add random string to span
	span.SetAttributes(attribute.String("service.entrypoint", entrypoint))
	span.SetAttributes(attribute.String("service.resp.size", strconv.Itoa(len(conf.randStr))))
	span.SetAttributes(attribute.String("service.resp.head", conf.randStr[0:MAX_LEN_TRACE_RES]))

	// check if endpoint exists
	if _, ok := conf.services[conf.ownName]._Endpoints[entrypoint]; !ok {
		writer.WriteHeader(http.StatusNotFound)
		fmt.Fprint(writer, "Entrypoint does not exist: "+entrypoint)
		log.Println("Entrypoint does not exist: " + entrypoint)
		return
	}

	// build list of urls to contact
	var urls []string
	for _, connection := range conf.services[conf.ownName]._Endpoints[entrypoint].Connections {
		if conf.httpVersion == "https" {
			urls = append(urls, "https://"+getAddress(conf.services, connection.Path)+connection.Url)
		} else {
			urls = append(urls, "http://"+getAddress(conf.services, connection.Path)+connection.Url)
		}
	}

	// making requests to other services sequentially
	for i := 0; i < len(urls); i++ {
		span.AddEvent("Contacting " + urls[i])
		_, err := makeRequestTracePropagation(ctx, urls[i])
		if err == nil {
			span.AddEvent("Success when contacting " + urls[i])
		} else {
			log.Println("Failed when contacting " + urls[i])
			span.AddEvent("Failed when contacting " + urls[i])
			writer.WriteHeader(http.StatusInternalServerError)
			fmt.Fprint(writer, "Error when contacting "+urls[i])
			return
		}
	}

	span.AddEvent("Contacted all " + strconv.Itoa(len(urls)) + " URLs")

	// write response
	writer.WriteHeader(http.StatusOK)
	var psize = conf.services[conf.ownName]._Endpoints[entrypoint].Psize
	if _, err := fmt.Fprint(writer, conf.randStr[0:psize]); err != nil {
		log.Printf("Error to write response: %v\n", err)
	}
}

// Handle HTTP(S) requests without Jaeger
func getRootNoJaeger(writer http.ResponseWriter, r *http.Request) {
	entrypoint := r.URL.Path

	// check if endpoint exist
	if _, ok := conf.services[conf.ownName]._Endpoints[entrypoint]; !ok {
		writer.WriteHeader(http.StatusNotFound)
		fmt.Fprint(writer, "Entrypoint does not exist: "+entrypoint)
		log.Println("Entrypoint does not exist: " + entrypoint)
		return
	}

	// build list of urls to contact
	var urls []string
	for _, connection := range conf.services[conf.ownName]._Endpoints[entrypoint].Connections {
		if conf.httpVersion == "https" {
			urls = append(urls, "https://"+getAddress(conf.services, connection.Path)+connection.Url)
		} else {
			urls = append(urls, "http://"+getAddress(conf.services, connection.Path)+connection.Url)
		}
	}

	// making requests to other services sequentially
	for i := 0; i < len(urls); i++ {
		_, err := makeRequest(urls[i])
		if err != nil {
			log.Println("Failed when contacting " + urls[i])
			writer.WriteHeader(http.StatusInternalServerError)
			fmt.Fprint(writer, "Error when contacting "+urls[i])
			return
		}
	}

	// write response
	writer.WriteHeader(http.StatusOK)
	var psize = conf.services[conf.ownName]._Endpoints[entrypoint].Psize
	if _, err := fmt.Fprint(writer, conf.randStr[0:psize]); err != nil {
		log.Printf("Error to write response: %v\n", err)
	}
}

// HTTP(S) handler integrating OpenTelemetry
func newHTTPHandler() http.Handler {
	mux := http.NewServeMux()

	if conf.enableJaeger && !conf.enableIOAM {
		handleFunc := func(pattern string, handlerFunc func(http.ResponseWriter, *http.Request)) {
			handler := otelhttp.WithRouteTag(pattern, http.HandlerFunc(handlerFunc))
			mux.Handle(pattern, handler)
		}

		// register handlers
		handleFunc("/", getRootJaeger)

		// add HTTP instrumentation for the whole server
		handler := otelhttp.NewHandler(mux, "/")
		return handler
	} else {
		mux.HandleFunc("/", getRootNoJaeger)
		return mux
	}
}

// Listen for requests and serve using (IPv4 or IPv6) with (HTTP or HTTPS)
func ListenAndServe(server *http.Server, addr string) error {
	var ln net.Listener
	var err error

	if conf.versionIP == "6" {
		ln, err = net.Listen("tcp6", addr)
	} else {
		ln, err = net.Listen("tcp4", addr)
	}

	if err != nil {
		return err
	}

	if conf.httpVersion == "https" {
		return server.ServeTLS(ln, conf.certFile, conf.keyFile)
	} else {
		return server.Serve(ln)
	}
}
