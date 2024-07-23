'''
Python script to generate configuration files for Docker Compose or
Kubernetes based on an architecture defined in an yml file.
'''

import sys, time, networkx as nx, matplotlib.pyplot as plt

from constants import ASCII_ART, VERSION
from utils import *
import config_parser, architecture, compose_exporter, k8s_exporter

def gen_config_files():
    """Generate configuration files to deploy topology."""

    if is_measuring_time():
        start = time.process_time_ns()

    print(ASCII_ART)
    print(f"Micro-Services Topology Generator v{VERSION}\n\n")

    print("Checking command line arguments...")
    filename = check_arguments()
    print_info(f"Got filename {filename}")
    print_success("Checked command line arguments.")

    print("\nParsing the configuration file...")
    config = config_parser.parse_config(filename)
    print_success("Extracted config.")

    print("\nBuilding architecture based on config file...")
    arch = architecture.Architecure(filename, config)
    if "--time" not in sys.argv:
        nx.draw_spring(arch.graph, node_color='deepskyblue', edge_color='dimgray', arrows=True, with_labels=True)
        plt.savefig("architecture.svg")
        plt.show(block=False)
    print_success("Built architecture.")

    if not is_measuring_time() and debug_mode_is_on():
        print("\nDumping internal state...")
        arch.pretty_print()
        print_success("Dumped internal state")

    if output_is_compose():
        print("\nWriting architecture to Docker Compose file...")
        exporter = compose_exporter.ComposeExporter(arch, "docker-compose.yml")
        exporter.export()
        print_success("Wrote architecture to Docker Compose file.")
    elif output_is_k8s():
        print("\nWriting architecture to Kubernetes files...")
        exporter = k8s_exporter.K8SExporter(arch)
        exporter.export()
        print_success("Wrote architecture to Kubernetes files.")

    if is_measuring_time():
        end = time.process_time_ns()
        print(f"Generated configuration file(s) in {end-start} ns.")

if __name__ == '__main__':
    gen_config_files()
    sys.exit(0)
