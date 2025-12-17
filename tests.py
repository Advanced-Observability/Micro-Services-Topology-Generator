"""Automatically test all configuration examples."""

import os
import sys
import time
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

        # build docker image for external container
        if "external" in config:
            subprocess.run("cd generator/tests/docker_myimage && docker build -t myimage .", shell=True)

        p = subprocess.run(f"cp {path} config.yml", shell=True)
        if p.returncode != 0:
            print_error(f"Error cp of {path}")
            sys.exit(1)

        p = subprocess.run(f"make clean > /dev/null 2> /dev/null && make images > /dev/null 2> /dev/null && make ipv6 > /dev/null 2> /dev/null", shell=True)
        if p.returncode != 0:
            print_error("Could not make")
            sys.exit(1)

        p = subprocess.run("make start > /dev/null 2> /dev/null", shell=True)
        if p.returncode != 0:
            print_error("Could not start")
            sys.exit(1)

        p = subprocess.run("chmod +x commands.sh && ./commands.sh 2> /dev/null", shell=True)

        time.sleep(3)

        p = subprocess.run("curl -6 \"http://[::1]:80/\"", shell=True)
        p2 = subprocess.run("curl http://127.0.0.1:80", shell=True)
        if p.returncode != 0 and p2.returncode != 0:
            print_error("Could not curl")
            sys.exit(1)
        else:
            print_success(f"\n\nPassed {path}")

        p = subprocess.run("make stop > /dev/null 2> /dev/null", shell=True)
        if p.returncode != 0:
            print("Cannot stop")
            sys.exit(1)

    sys.exit(os.EX_OK)
