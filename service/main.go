// Main file for service.

package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"time"

	"go.opentelemetry.io/otel"
)

// Configuration of the service
var conf Config

// Main function of service
func main() {
	configureService()

	startService()
}

// Configure the service
func configureService() {
	parseCliArguments()

	// Read config
	var err error
	conf.services, err = readConfig(conf.configPath)
	if err != nil {
		log.Fatal(err)
	}

	parseEnvVariables()

	serviceInfo()

	// Generate random string
	conf.randStr = randomString(conf.services[conf.ownName]._MaxPsize)
}

// Start the service
func startService() {
	// Create tracer
	if conf.enableJaeger {
		conf.tracer = otel.Tracer(conf.ownName)
	}

	// Handle SIGINT (CTRL+C) gracefully.
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()

	// Set up OpenTelemetry.
	if conf.enableJaeger {
		serviceVersion := VERSION
		jaegerURL := "http://" + conf.jaegerHostname + ":14268/api/traces"
		otelShutdown, err := setupOTelSDK(ctx, conf.ownName, serviceVersion, jaegerURL)
		if err != nil {
			return
		}
		// Handle shutdown properly so nothing leaks.
		defer func() {
			err = errors.Join(err, otelShutdown(context.Background()))
		}()
	}

	// Build listening address
	listenAddr := ":" + strconv.FormatInt(int64(conf.services[conf.ownName].Port), 10)
	fmt.Printf("HTTP(S) server listening on %s\n", listenAddr)

	// Start HTTP server.
	srv := &http.Server{
		Addr:         listenAddr,
		BaseContext:  func(_ net.Listener) context.Context { return ctx },
		ReadTimeout:  time.Second,
		WriteTimeout: 10 * time.Second,
		Handler:      newHTTPHandler(),
	}
	srvErr := make(chan error, 1)
	go func() {
		srvErr <- ListenAndServe(srv, listenAddr)
	}()

	// Wait for interruption.
	select {
	case err := <-srvErr:
		// Error when starting HTTP server.
		log.Fatal("Error when starting the server: " + err.Error())
		return
	case <-ctx.Done():
		// Wait for first CTRL+C.
		// Stop receiving signal notifications as soon as possible.
		stop()
	}

	// When Shutdown is called, ListenAndServe immediately returns ErrServerClosed.
	srv.Shutdown(context.Background())
}
