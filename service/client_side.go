// Code for the service acting as a client.
// Sending HTTP(S) requests.

package main

import (
	"context"
	"crypto/tls"
	"io"
	"log"
	"math/big"
	"net"
	"net/http"
	"strconv"

	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
	"go.opentelemetry.io/otel/trace"
)

// Make request to given `url` with trace propagation
func makeRequestTracePropagation(ctx context.Context, url string) (string, error) {
	var socketId uint32
	if conf.enableCLT {
		// add pointer to local variable in context to be able to store
		// the identifier of the socket from myDialContext
		ctx = context.WithValue(ctx, "socketID", &socketId)
	}

	// Create request WithContext to transfer context used by OpenTelemetry
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return "", err
	}

	client := createClient()

	resp, errReq := client.Do(req)
	if errReq != nil {
		return "", errReq
	}

	// Parse response body
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	if conf.enableCLT {
		// Disable clt for given socket
		err = clt_disable(uint32(socketId))
		if err != nil {
			log.Println("Error while calling CLT disable")
		}
	}

	return string(body), nil
}

// Make request to given `url` without trace propagation
func makeRequest(url string) (string, error) {
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return "", err
	}

	client := createClient()

	resp, errReq := client.Do(req)
	if errReq != nil {
		return "", errReq
	}

	// Parse response body
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	return string(body), nil
}

// Create http client
func createClient() http.Client {
	if conf.httpVersion == "https" {
		return http.Client{
			Transport: otelhttp.NewTransport(&http.Transport{
				DialContext: myDialContext,
				// need to skip verify because self signed certificate
				TLSClientConfig: &tls.Config{InsecureSkipVerify: true}}),
			Timeout: REQUEST_TIMEOUT,
		}
	} else {
		return http.Client{
			Transport: otelhttp.NewTransport(&http.Transport{DialContext: myDialContext}),
			Timeout:   REQUEST_TIMEOUT,
		}
	}
}

// Modified from https://forum.golangbridge.org/t/net-http-dialcontext/8200/7
// Called before creating TCP connections
func myDialContext(ctx context.Context, network, addr string) (net.Conn, error) {
	// create connection
	var conn net.Conn
	var err error
	if conf.versionIP == "6" {
		conn, err = net.Dial("tcp6", addr)
	} else {
		conn, err = net.Dial("tcp4", addr)
	}

	if err != nil {
		log.Println("Could not dial connection")
		log.Println(err.Error())
		return nil, err
	}

	if !conf.enableCLT {
		return conn, nil
	}

	// extract trace and span ids from context
	span := trace.SpanFromContext(ctx)
	traceHex := span.SpanContext().TraceID().String()
	spanHex := span.SpanContext().SpanID().String()
	spanDec, _ := strconv.ParseUint(spanHex, 16, 64)

	// get identifier of fd associated to socket2
	socketFd := GetFdFromConn(conn)

	// store socket fd
	ptr := ctx.Value("socketID")
	if ptr == nil {
		log.Println("Cannot get socket field in context")
	} else {
		*(ptr.(*uint32)) = uint32(socketFd)
	}

	// convert trace id to big.Int for bit manipulations
	var traceIDint big.Int
	traceIDint.SetString(traceHex, 16)

	// extract MSB 64 bits
	var traceID_high big.Int
	traceID_high.Rsh(&traceIDint, 64)

	// extract LSB 64 bits
	var mask big.Int
	mask.SetString("0000000000000000ffffffffffffffff", 16)
	var traceID_low big.Int
	traceID_low.And(&traceIDint, &mask)

	// add trace and span ids to packets by using generic netlink to communicate with kernel
	err = clt_enable(uint32(socketFd), traceID_high.Uint64(), traceID_low.Uint64(), spanDec)
	if err != nil {
		log.Println("Error during CLT enable in callback:" + err.Error())
		return nil, err
	}

	return conn, nil
}
