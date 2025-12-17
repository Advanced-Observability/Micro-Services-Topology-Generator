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

def print_info(text: str):
    '''Print an info text.'''
    print(f"\033[94m[INFO] {text}\033[0m")

def print_warning(text: str):
    '''Print a warning text.'''
    print(f"\033[93m[WARNING] {text}\033[0m")

def is_github_actions() -> bool:
    return os.getenv("GITHUB_ACTIONS") == "true"

def is_root() -> bool:
    return os.getuid() == 0


if __name__ == "__main__":

    configurations = os.listdir("configuration_examples")
    configurations = [conf for conf in configurations if conf.endswith(".yml")]
    configurations.sort()
    print(configurations)

    for config in configurations:
        print(f"\n{'-'*80}\n")

        if "switch" in config and (not is_root() or is_github_actions()):
            print_warning(f"Will skip {config} because it uses a switch. Thus, it requires to be root (sudo) to manipulate veth.")
            continue

        path = os.path.join("configuration_examples", config)
        print_info(f"Testing {path}...\n")

        # build docker image for external container
        if "external" in config:
            p = subprocess.run(
                "cd generator/tests/docker_myimage && docker build -t myimage .",
                shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            if p.returncode != 0:
                print_error("Could not build image for external container")
                print(p.stdout.decode("utf-8"))
                print(p.stderr.decode("utf-8"))
                sys.exit(1)

        p = subprocess.run(f"cp {path} config.yml", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode != 0:
            print_error(f"Error cp of {path}")
            print(p.stdout.decode("utf-8"))
            print(p.stderr.decode("utf-8"))
            sys.exit(1)

        p = subprocess.run(
            "make clean && make images && make ipv6",
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if p.returncode != 0:
            print_error("Could not make")
            print(p.stdout.decode("utf-8"))
            print(p.stderr.decode("utf-8"))
            sys.exit(1)

        p = subprocess.run(
            "make start", shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if p.returncode != 0:
            print_error("Could not start")
            print(p.stdout.decode("utf-8"))
            print(p.stderr.decode("utf-8"))
            sys.exit(1)

        print("Executing commands.sh script...")
        p = subprocess.run("chmod +x commands.sh && ./commands.sh", shell=True)

        print("Waiting for startup before executing curl...")
        time.sleep(3)

        print("Requesting...")
        p = subprocess.run("curl -6 \"http://[::1]:80/\"", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p2 = subprocess.run("curl http://127.0.0.1:80", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode != 0 and p2.returncode != 0:
            print_error("Could not curl first")
            print(p.stdout.decode("utf-8"))
            print(p.stderr.decode("utf-8"))
            print_error("Could not curl second")
            print(p2.stdout.decode("utf-8"))
            print(p2.stderr.decode("utf-8"))

            sys.exit(1)
        else:
            print_success(f"\nPassed {path}")

        p = subprocess.run("make stop", shell=True)
        if p.returncode != 0:
            print("Cannot stop")
            print(p.stdout.decode("utf-8"))
            print(p.stderr.decode("utf-8"))
            sys.exit(1)

    sys.exit(os.EX_OK)
