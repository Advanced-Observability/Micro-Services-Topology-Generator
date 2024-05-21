package main

import (
	"encoding/binary"
	"encoding/hex"
	"log"
	"net"
	"strconv"

	"golang.org/x/net/context"
	"google.golang.org/grpc"
	empty "google.golang.org/protobuf/types/known/emptypb"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/jaeger"
	"go.opentelemetry.io/otel/sdk/resource"
	tracesdk "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.12.0"
	"go.opentelemetry.io/otel/trace"

	ioam_api "ioam-collector/github.com/Advanced-Observability/ioam-api"
)

var MASK_BIT0 = uint32(1 << 31)  // Hop_Lim + Node Id (short format)
var MASK_BIT1 = uint32(1 << 30)  // Ingress/Egress Ids (short format)
var MASK_BIT2 = uint32(1 << 29)  // Timestamp seconds
var MASK_BIT3 = uint32(1 << 28)  // Timestamp fraction
var MASK_BIT4 = uint32(1 << 27)  // Transit Delay
var MASK_BIT5 = uint32(1 << 26)  // Namespace Data (short format)
var MASK_BIT6 = uint32(1 << 25)  // Queue depth
var MASK_BIT7 = uint32(1 << 24)  // Checksum Complement
var MASK_BIT8 = uint32(1 << 23)  // Hop_Lim + Node Id (wide format)
var MASK_BIT9 = uint32(1 << 22)  // Ingress/Egress Ids (wide format)
var MASK_BIT10 = uint32(1 << 21) // Namespace Data (wide format)
var MASK_BIT11 = uint32(1 << 20) // Buffer Occupancy
var MASK_BIT22 = uint32(1 << 9)  // Opaque State Snapshot

func main() {
	exp, err := jaeger.New(jaeger.WithCollectorEndpoint())
	if err != nil {
		log.Fatal(err)
	}
	tp := tracesdk.NewTracerProvider(
		tracesdk.WithBatcher(exp),
		tracesdk.WithResource(resource.NewWithAttributes(
			semconv.SchemaURL,
			semconv.ServiceNameKey.String("network"),
		)),
	)
	otel.SetTracerProvider(tp)

	grpcServer := grpc.NewServer()
	var server Server
	ioam_api.RegisterIOAMServiceServer(grpcServer, server)
	listen, err := net.Listen("tcp", ":7123")
	if err != nil {
		log.Fatalf("Could not listen: %v", err)
	}

	log.Println("IOAM collector listening...")
	log.Fatal(grpcServer.Serve(listen))
}

type Server struct {
	ioam_api.UnimplementedIOAMServiceServer
}

var empty_inst = new(empty.Empty)

func (Server) Report(grpc_ctx context.Context, request *ioam_api.IOAMTrace) (*empty.Empty, error) {
	var traceID trace.TraceID
	binary.BigEndian.PutUint64(traceID[:8], request.GetTraceId_High())
	binary.BigEndian.PutUint64(traceID[8:], request.GetTraceId_Low())

	var spanID trace.SpanID
	binary.BigEndian.PutUint64(spanID[:], request.GetSpanId())

	span_ctx := trace.NewSpanContext(trace.SpanContextConfig{
		TraceID:    traceID,
		SpanID:     spanID,
		TraceFlags: trace.FlagsSampled,
	})
	ctx := trace.ContextWithSpanContext(context.Background(), span_ctx)

	tracer := otel.Tracer("ioam-tracer")
	_, span := tracer.Start(ctx, "ioam-span")

	i := 1
	for _, node := range request.GetNodes() {
		key := "ioam_namespace" + strconv.FormatUint(uint64(request.GetNamespaceId()), 10) + "_node" + strconv.Itoa(i)
		str := ParseNode(node, request.GetBitField())

		span.SetAttributes(attribute.String(key, str))
		i += 1
	}

	span.End()
	return empty_inst, nil
}

func ParseNode(node *ioam_api.IOAMNode, fields uint32) string {
	str := ""

	if (fields & MASK_BIT0) != 0 {
		str += "HopLimit=" + strconv.FormatUint(uint64(node.GetHopLimit()), 10) + "; "
		str += "Id=" + strconv.FormatUint(uint64(node.GetId()), 10) + "; "
	}
	if (fields & MASK_BIT1) != 0 {
		str += "IngressId=" + strconv.FormatUint(uint64(node.GetIngressId()), 10) + "; "
		str += "EgressId=" + strconv.FormatUint(uint64(node.GetEgressId()), 10) + "; "
	}
	if (fields & MASK_BIT2) != 0 {
		str += "TimestampSecs=" + strconv.FormatUint(uint64(node.GetTimestampSecs()), 10) + "; "
	}
	if (fields & MASK_BIT3) != 0 {
		str += "TimestampFrac=" + strconv.FormatUint(uint64(node.GetTimestampFrac()), 10) + "; "
	}
	if (fields & MASK_BIT4) != 0 {
		str += "TransitDelay=" + strconv.FormatUint(uint64(node.GetTransitDelay()), 10) + "; "
	}
	if (fields & MASK_BIT5) != 0 {
		str += "NamespaceData=0x" + hex.EncodeToString(node.GetNamespaceData()) + "; "
	}
	if (fields & MASK_BIT6) != 0 {
		str += "QueueDepth=" + strconv.FormatUint(uint64(node.GetQueueDepth()), 10) + "; "
	}
	if (fields & MASK_BIT7) != 0 {
		str += "CsumComp=" + strconv.FormatUint(uint64(node.GetCsumComp()), 10) + "; "
	}
	if (fields & MASK_BIT8) != 0 {
		str += "HopLimit=" + strconv.FormatUint(uint64(node.GetHopLimit()), 10) + "; "
		str += "IdWide=" + strconv.FormatUint(uint64(node.GetIdWide()), 10) + "; "
	}
	if (fields & MASK_BIT9) != 0 {
		str += "IngressIdWide=" + strconv.FormatUint(uint64(node.GetIngressIdWide()), 10) + "; "
		str += "EgressIdWide=" + strconv.FormatUint(uint64(node.GetEgressIdWide()), 10) + "; "
	}
	if (fields & MASK_BIT10) != 0 {
		str += "NamespaceDataWide=0x" + hex.EncodeToString(node.GetNamespaceDataWide()) + "; "
	}
	if (fields & MASK_BIT11) != 0 {
		str += "BufferOccupancy=" + strconv.FormatUint(uint64(node.GetBufferOccupancy()), 10) + "; "
	}
	if (fields & MASK_BIT22) != 0 {
		str += "OpaqueStateSchemaId=" + strconv.FormatUint(uint64(node.GetOSS().GetSchemaId()), 10) + "; "
		str += "OpaqueStateData=0x" + hex.EncodeToString(node.GetOSS().GetData()) + "; "
	}

	return str
}
