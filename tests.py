"""Automatically test all configuration examples."""

import os
import sys
import subprocess

MAKE_COMMAND = "make"
MAKE_CLEAN_COMMAND = "make clean"
START_COMMAND = "make start"
STOP_COMMAND = "make stop"

def print_success(text: str):
    '''Print a success text.'''
    print(f"\033[92m{text}\033[0m")


def print_error(text: str):
    '''Print an error text.'''
    print(f"\033[91m[ERROR] {text}\033[0m")


if __name__ == "__main__":

    configurations = os.listdir("configuration_examples")
    configurations = [conf for conf in configurations if conf.endswith(".yml")]
    configurations.sort()
    print(configurations)

    for config in configurations:
        print("\n--------")
        path = os.path.join("configuration_examples", config)
        print(f"Testing {path}...")

        p = subprocess.run(f"cp {path} config.yml", shell=True)
        if p.returncode != 0:
            print_error(f"Error cp of {path}")
            sys.exit(1)

        p = subprocess.run(f"make clean > /dev/null 2> /dev/null && make images > /dev/null 2> /dev/null && make ipv6_ioam > /dev/null 2> /dev/null", shell=True)
        if p.returncode != 0:
            print_error("Could not make")
            sys.exit(1)

        p = subprocess.run("make start > /dev/null 2> /dev/null", shell=True)
        if p.returncode != 0:
            print_error("Could not start")
            sys.exit(1)

        p = subprocess.run("curl http://localhost:80", shell=True)
        if p.returncode != 0:
            print_error("Could not curl")
            sys.exit(1)
        else:
            print_success(f"\n\nPassed {path}")

        p = subprocess.run("make stop > /dev/null 2> /dev/null", shell=True)
        if p.returncode != 0:
            print("Cannot stop")
            sys.exit(1)

    sys.exit(os.EX_OK)
