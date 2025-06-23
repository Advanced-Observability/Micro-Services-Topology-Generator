'''
Python script to generate configuration files for Docker Compose or
Kubernetes based on an architecture defined in an yml file.
'''

import os
import sys
import time
import networkx as nx
import matplotlib.pyplot as plt

import config_parser
import architecture
import compose_exporter
import k8s_exporter
import utils
from constants import ASCII_ART, VERSION


def gen_config_files(args=None):
    """Generate configuration files to deploy topology."""

    if utils.is_measuring_time():
        start = time.process_time_ns()

    print(ASCII_ART)
    print(f"MicroServices Topology Generator v{VERSION}\n\n")

    print("Checking command line arguments...")
    conf_file = utils.check_arguments(args)
    utils.print_info(f"Got configuration file \"{conf_file}\"")
    utils.print_success("Checked command line arguments.")

    print("\nParsing the configuration file...")
    config = config_parser.parse_config(conf_file)
    utils.print_success("Extracted config.")

    print("\nBuilding architecture based on config file...\n")
    arch = architecture.Architecure(conf_file, config)
    if "--time" not in sys.argv:
        nx.draw_spring(
            arch.graph, node_color='deepskyblue',
            edge_color='dimgray', arrows=True, with_labels=True
        )
        plt.savefig("architecture.svg")
        plt.show(block=False)
    utils.print_success("Built architecture.")

    if not utils.is_measuring_time() and utils.debug_mode_is_on():
        print("\nDisplaying internal state...")
        arch.pretty_print()
        utils.print_success("Displayed internal state")

    if utils.output_is_compose():
        print("\nWriting architecture to Docker Compose file...")
        exporter = compose_exporter.ComposeExporter(arch, "docker-compose.yml")
        exporter.export()
        utils.print_success("Wrote architecture to Docker Compose file.")
    elif utils.output_is_k8s():
        print("\nWriting architecture to Kubernetes files...")
        exporter = k8s_exporter.K8SExporter(arch)
        exporter.export()
        utils.print_success("Wrote architecture to Kubernetes files.")

    if utils.is_measuring_time():
        end = time.process_time_ns()
        print(f"Generated configuration file(s) in {end - start} ns.")

    return os.EX_OK


if __name__ == '__main__':
    sys.exit(gen_config_files(sys.argv[1:]))
