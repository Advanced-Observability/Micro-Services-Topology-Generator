FROM ubuntu:22.04

RUN apt update && \
    apt install -y openvswitch-switch iproute2 iputils-ping tcpdump && \
    apt clean

CMD ["/bin/bash"]
