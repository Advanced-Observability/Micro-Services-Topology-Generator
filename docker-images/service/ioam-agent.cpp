// From https://github.com/Advanced-Observability/ioam-agent-cpp

#include <iostream>
#include <stdio.h>
#include <unistd.h>
#include <getopt.h>
#include <string.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <net/if.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <linux/if_packet.h>
#include <net/ethernet.h>

#include <grpc/grpc.h>
#include <grpcpp/create_channel.h>
#include <google/protobuf/empty.pb.h>

#include "ioam_api.grpc.pb.h"

using grpc::Server;
using grpc::ServerBuilder;
using grpc::ServerContext;
using grpc::Status;

using ioam_api::IOAMService;
using ioam_api::IOAMTrace;
using ioam_api::IOAMNode;
using ioam_api::Opaque;


#define ETH_P_IPV6 0x86DD
#define IPV6_TLV_IOAM 49
#define IOAM_PREALLOC_TRACE 0

#define MIN(a,b) (((a)<(b))?(a):(b))
#define SAFE_GUARD(max,curr) \
    if (max < curr) {throw std::out_of_range(__func__);}

constexpr uint32_t TRACE_TYPE_BIT0_MASK  = 1u << 23;  // Hop_Lim + Node Id (short)
constexpr uint32_t TRACE_TYPE_BIT1_MASK  = 1u << 22;  // Ingress/Egress Ids (short)
constexpr uint32_t TRACE_TYPE_BIT2_MASK  = 1u << 21;  // Timestamp seconds
constexpr uint32_t TRACE_TYPE_BIT3_MASK  = 1u << 20;  // Timestamp fraction
constexpr uint32_t TRACE_TYPE_BIT4_MASK  = 1u << 19;  // Transit Delay
constexpr uint32_t TRACE_TYPE_BIT5_MASK  = 1u << 18;  // Namespace Data (short)
constexpr uint32_t TRACE_TYPE_BIT6_MASK  = 1u << 17;  // Queue depth
constexpr uint32_t TRACE_TYPE_BIT7_MASK  = 1u << 16;  // Checksum Complement
constexpr uint32_t TRACE_TYPE_BIT8_MASK  = 1u << 15;  // Hop_Lim + Node Id (wide)
constexpr uint32_t TRACE_TYPE_BIT9_MASK  = 1u << 14;  // Ingress/Egress Ids (wide)
constexpr uint32_t TRACE_TYPE_BIT10_MASK = 1u << 13;  // Namespace Data (wide)
constexpr uint32_t TRACE_TYPE_BIT11_MASK = 1u << 12;  // Buffer Occupancy
constexpr uint32_t TRACE_TYPE_BIT22_MASK = 1u << 1;   // Opaque State Snapshot


class IOAMServiceClient {
 public:
  IOAMServiceClient(std::shared_ptr<grpc::Channel> channel)
      : stub_(IOAMService::NewStub(channel)) {}

  bool Report(ioam_api::IOAMTrace trace) {
    grpc::ClientContext context;
    google::protobuf::Empty empty;

    Status status = stub_->Report(&context, trace, &empty);
    if (!status.ok()) {
      std::cout << "GetFeature rpc failed." << std::endl;
      return false;
    }

    return true;
  }

 private:
  std::unique_ptr<IOAMService::Stub> stub_;
};

template <class T>
void big_bytecpy(T *dst, const unsigned char *src, size_t n) {
    T *d = dst;
    *d = 0;
    for (size_t i = 0; i < n; i++) {
        *d <<= 8;
        *d += src[i];
    }
}


// Function to parse IOAMNode data
struct IOAMNode parse_node_data(const uint8_t *p, uint32_t ttype, ssize_t len) {
    IOAMNode node;
    ssize_t i = 0;

    if (ttype & TRACE_TYPE_BIT0_MASK) {
        SAFE_GUARD(len, i + 4);
        uint32_t hoplimit, id;
        big_bytecpy(&hoplimit, &p[i], 1);
        i += 1;
        big_bytecpy(&id, &p[i], 3);
        i += 3;

        node.set_hoplimit(hoplimit);
        node.set_id(id);
    }

    if (ttype & TRACE_TYPE_BIT1_MASK) {
        SAFE_GUARD(len, i + 4);
        uint32_t ingressid, egressid;
        big_bytecpy(&ingressid, &p[i], 2);
        i += 2;
        big_bytecpy(&egressid, &p[i], 2);
        i += 2;

        node.set_ingressid(ingressid);
        node.set_egressid(egressid);
    }

    if (ttype & TRACE_TYPE_BIT2_MASK) {
        SAFE_GUARD(len, i + 4);
        uint32_t timestampsecs;
        big_bytecpy(&timestampsecs, &p[i], 4);
        i += 4;

        node.set_timestampsecs(timestampsecs);
    }

    if (ttype & TRACE_TYPE_BIT3_MASK) {
        SAFE_GUARD(len, i + 4);
        uint32_t timestampfrac;
        big_bytecpy(&timestampfrac, &p[i], 4);
        i += 4;

        node.set_timestampfrac(timestampfrac);
    }

    if (ttype & TRACE_TYPE_BIT4_MASK) {
        SAFE_GUARD(len, i + 4);
        uint32_t transitdelay;
        big_bytecpy(&transitdelay, &p[i], 4);
        i += 4;

        node.set_transitdelay(transitdelay);
    }

    if (ttype & TRACE_TYPE_BIT5_MASK) {
        SAFE_GUARD(len, i + 4);
        char string_nsd[4];
        float nsd = *(float *)&p[i];
        i += 4;

        memcpy(string_nsd, &nsd, 4);
        node.set_namespacedata(string_nsd);
    }

    if (ttype & TRACE_TYPE_BIT6_MASK) {
        SAFE_GUARD(len, i + 4);
        uint32_t queuedepth;
        big_bytecpy(&queuedepth, &p[i], 4);
        i += 4;

        node.set_queuedepth(queuedepth);
    }

    if (ttype & TRACE_TYPE_BIT7_MASK) {
        SAFE_GUARD(len, i + 4);
        uint32_t csumcomp;
        big_bytecpy(&csumcomp, &p[i], 4);
        i += 4;

        node.set_queuedepth(csumcomp);
    }

    if (ttype & TRACE_TYPE_BIT8_MASK) {
        SAFE_GUARD(len, i + 8);
        uint32_t hoplimit;
        uint64_t idwide;
        big_bytecpy(&hoplimit, &p[i], 1);
        i += 1;
        big_bytecpy(&idwide, &p[i], 7);
        i += 7;

        node.set_hoplimit(hoplimit);
        node.set_idwide(idwide);
    }

    if (ttype & TRACE_TYPE_BIT9_MASK) {
        SAFE_GUARD(len, i + 8);
        uint32_t ingressidwide, egressidwide;
        big_bytecpy(&ingressidwide, &p[i], 4);
        i += 4;
        big_bytecpy(&egressidwide, &p[i], 4);
        i += 4;

        node.set_ingressid(ingressidwide);
        node.set_egressid(egressidwide);
    }

    if (ttype & TRACE_TYPE_BIT10_MASK) {
        SAFE_GUARD(len, i + 8);
        char string_nsdw[8];
        double nsdw = *(double *)&p[i];
        i += 8;

        memcpy(string_nsdw, &nsdw, 8);
        node.set_namespacedatawide(string_nsdw);
    }
    if (ttype & TRACE_TYPE_BIT11_MASK) {
        SAFE_GUARD(len, i + 4);
        uint32_t bufferoccupancy;
        big_bytecpy(&bufferoccupancy, &p[i], 4);
        i += 4;

        node.set_bufferoccupancy(bufferoccupancy);
    }

    return node;
}

// Function to parse IOAMTrace data
IOAMTrace parse_ioam_trace(const uint8_t* p, ssize_t len) {
    SAFE_GUARD(len, 32);
    ssize_t i = 0;
    uint32_t ns, nodelen, remlen, ttype;
    uint64_t tid_high, tid_low, sid;
    big_bytecpy<uint32_t>(&ns, &p[i], 2);
    i += 2;
    big_bytecpy<uint32_t>(&nodelen, &p[i], 1);
    i += 1;
    nodelen >>= 3;
    big_bytecpy<uint32_t>(&remlen, &p[i], 1);
    i += 1;
    remlen &= 0b01111111;
    big_bytecpy<uint32_t>(&ttype, &p[i], 3);
    i += 4;
    big_bytecpy<uint64_t>(&tid_high, &p[i], 8);
    i += 8;
    big_bytecpy<uint64_t>(&tid_low, &p[i], 8);
    i += 8;
    big_bytecpy<uint64_t>(&sid, &p[i], 8);
    i += 8;

    std::vector<IOAMNode> nodes;
    i += remlen * 4;

    while (i < len) {
        IOAMNode node = parse_node_data(&p[i], ttype, MIN(nodelen * 4, len > i ? len - i : 0));
        i += nodelen * 4;

        if (ttype & TRACE_TYPE_BIT22_MASK) {
            SAFE_GUARD(len, i + 4);
            uint8_t opaque_len;
            uint32_t schemaid;
            big_bytecpy<uint8_t>(&opaque_len, &p[i], 1);
            i+=1;
            big_bytecpy<uint32_t>(&schemaid, &p[i], 3);
            i+=3;
            node.mutable_oss()->set_schemaid(schemaid);

            if (opaque_len > 0) {
                SAFE_GUARD(len, i + (opaque_len * 4));

                std::string data;
                data.assign(p + i, p + i + (opaque_len * 4));
                node.mutable_oss()->set_data(data);
            }

            i += opaque_len * 4;
        }

        if (!node.DebugString().empty()) {
            nodes.insert(nodes.begin(), node);
        }
    }

    IOAMTrace trace;
    trace.set_bitfield(ttype << 8);
    trace.set_namespaceid(ns);
    trace.set_traceid_high(tid_high);
    trace.set_traceid_low(tid_low);
    trace.set_spanid(sid);
    for (const auto& node : nodes) {
        *trace.add_nodes() = node;
    }

    return trace;
}

std::vector<IOAMTrace> parse(const uint8_t* p, ssize_t len) {
    SAFE_GUARD(len, 42);
    uint8_t nextHdr = p[6];

    if (nextHdr != IPPROTO_HOPOPTS) {
        return std::vector<IOAMTrace>();
    }

    int hbh_len = (p[41] + 1) << 3;
    unsigned i = 42;
    
    std::vector<IOAMTrace> traces;
    while (hbh_len > 0) {
        SAFE_GUARD(len, i + 4);
        uint8_t opt_type = p[i];
        ssize_t opt_len = p[i+1] + 2;
        
        if ((opt_type == IPV6_TLV_IOAM) && (p[i + 3] == IOAM_PREALLOC_TRACE)) {
            IOAMTrace trace = parse_ioam_trace(&p[i + 4], MIN(opt_len > 4 ? opt_len - 4 : 0, len > i ? len - i : 0));
            if (!trace.DebugString().empty()) {
                traces.push_back(trace);
            }
        }

        i += opt_len;
        hbh_len -= opt_len;
    }

    return traces;
}

void listen(char *interface, char *collector, bool output) {
    struct sockaddr_ll sa;
    socklen_t addrlen = sizeof(sa);

    int sock = socket(AF_PACKET, SOCK_DGRAM, htons(ETH_P_IPV6));
    if (sock == -1) {
        exit(EXIT_FAILURE);
    }

    memset((void*)&sa, 0, addrlen);
    sa.sll_family = AF_PACKET;
    sa.sll_protocol = htons(ETH_P_IPV6);
    sa.sll_ifindex = if_nametoindex(interface);
    
    if (setsockopt(sock, SOL_SOCKET, SO_BINDTODEVICE, interface, strlen(interface) + 1) == -1) {
        exit(EXIT_FAILURE);
    }

    IOAMServiceClient *client = NULL;
    if (output) {
        std::cout << "[IOAM Agent] Printing IOAM traces..." << std::endl;
    } else {
        client = new IOAMServiceClient(grpc::CreateChannel(collector, grpc::InsecureChannelCredentials()));
        std::cout << "[IOAM Agent] Reporting to IOAM collector..." << std::endl;
    }

    ssize_t received = 0;
    uint8_t *buf = (uint8_t*)malloc(2048);
    if (buf == NULL) {
        exit(EXIT_FAILURE);
    }

    while (1) {
        received = recv(sock, buf, 2048, 0);
        if (received != -1) {
            try {
                std::vector<ioam_api::IOAMTrace> traces = parse(buf, received);
                for(ioam_api::IOAMTrace trace : traces) {
                    if (((trace.traceid_high() != 0) || (trace.traceid_low() != 0)) \
                        && (trace.spanid() != 0)) {
                        
                        if (output) {
                            std::cout << trace.DebugString() << std::endl;
                        } else {
                            client->Report(trace);
                        }
                    }
                }
            } catch(const std::exception& e) {
                std::cout << "[IOAM Agent] error: " << e.what() << std::endl;
            }
        }
    }

    if (client != NULL) {
        delete client;
    }
    close(sock);
}

int main(int argc, char* argv[]) {
    char *interface = NULL;
    bool output = false;
    for(;;) {
        switch(getopt(argc, argv, "i:oh")) {
            case 'i':
            interface = strdup(optarg);
            continue;

            case 'o':
            output = true;

            continue;

            case 'h':
            default :
            std::cout << "Syntax: " << argv[0] << " -i <interface> [-o]" << std::endl;
            break;

            case -1:
            break;
        }

        break;
    }

    if (interface == NULL || if_nametoindex(interface) == 0) {
        std::cout << "Unknown interface" << std::endl;
        std::cout << "Syntax: " << argv[0] << " -i <interface> [-o]" << std::endl;
        exit(EXIT_FAILURE);
    }

    char *collector = NULL;
    collector = std::getenv("IOAM_COLLECTOR");
    if (!output && (collector == NULL)) {
        std::cout << "IOAM collector is not defined" << std::endl;
        exit(EXIT_FAILURE);
    }

    listen(interface, collector, output);

    exit(EXIT_SUCCESS);
}
