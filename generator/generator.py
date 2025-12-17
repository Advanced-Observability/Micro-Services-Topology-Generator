"""
Main file for MSTG.
"""

import os
import sys
import time
import networkx as nx
import matplotlib.pyplot as plt

import utils
import k8s_exporter
import architecture
import config_parser
import compose_exporter
from constants import ASCII_ART, VERSION


def gen_config_files(args=None):
    """Generate configuration files to deploy topology."""

    if utils.is_measuring_time():
        start = time.process_time_ns()

    print(ASCII_ART)
    print(f"MicroServices Topology Generator v{VERSION}\n\n")

    print("Checking command line arguments...")
    conf_file = utils.check_arguments(args)
    utils.print_info(f'Got configuration file "{conf_file}"')
    utils.print_success("Checked command line arguments.")

    print("\nParsing the configuration file...")
    config = config_parser.parse_config(conf_file)
    utils.print_success("Extracted config.")

    print("\nBuilding the architecture based on the configuration file...\n")
    arch = architecture.Architecture(conf_file, config)
    if "--time" not in sys.argv:
        nx.draw_spring(
            arch.graph,
            node_color="deepskyblue",
            edge_color="dimgray",
            arrows=True,
            with_labels=True,
        )
        plt.savefig("architecture.svg")
    utils.print_success("Built architecture.")

    if not utils.is_measuring_time() and utils.debug_mode_is_on():
        print("\nDisplaying internal state...")
        arch.pretty_print()
        utils.print_success("Displayed internal state")

    if utils.output_is_compose():
        print("\nWriting architecture to Docker Compose file...")
        exporter = compose_exporter.ComposeExporter(arch, "docker-compose.yaml")
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


if __name__ == "__main__":
    sys.exit(gen_config_files(sys.argv[1:]))
