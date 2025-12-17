"""Automatically test all configuration examples."""

import os
import sys
import time
import argparse
import subprocess

MAKE_COMMAND = "make"
MAKE_CLEAN_COMMAND = "make clean"
START_COMMAND = "make start"
STOP_COMMAND = "make stop"

OUTPUT_COMPOSE = "compose"
OUTPUT_K8S = "kubernetes"


def print_success(text: str):
    """Print a success text."""
    print(f"\033[92m{text}\033[0m")


def print_error(text: str):
    """Print an error text."""
    print(f"\033[91m[ERROR] {text}\033[0m")


def print_info(text: str):
    """Print an info text."""
    print(f"\033[94m[INFO] {text}\033[0m")


def print_warning(text: str):
    """Print a warning text."""
    print(f"\033[93m[WARNING] {text}\033[0m")


def is_github_actions() -> bool:
    """Check if being executed as GitHub CI."""
    return os.getenv("GITHUB_ACTIONS") == "true"


def is_root() -> bool:
    return os.getuid() == 0


def check_subprocess(p, err_msg):
    """Check output of `subprocess.run`."""
    if p.returncode != 0:
        print_error(f"{err_msg}")
        print(p.stdout.decode("utf-8"))
        print(p.stderr.decode("utf-8"))
        sys.exit(1)


def check_arguments(args) -> str:
    """Check given arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        required=False,
        choices=[OUTPUT_COMPOSE, OUTPUT_K8S],
        type=str,
        default="compose",
    )
    args = parser.parse_args(args)
    return args.output


def build_external_image(output):
    """Building image for testing external container in MSTG."""
    print("Building external image...")
    p = subprocess.run(
        "cd generator/tests/docker_myimage && docker build -t myimage .",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    check_subprocess(p, "Could not build image for external container")

    if output == OUTPUT_K8S:
        subprocess.run("kind load docker-image --name meshnet myimage", shell=True)


def requesting(output):
    """Test request in deployed architecture."""
    if output == OUTPUT_K8S:
        p = subprocess.run(
            'kubectl exec -it frontend-pod -- sh -c "wget "http://[::1]:80/" -O index.html"',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        check_subprocess(p, "Could not curl")
        return 0

    if "switch" not in config:
        p = subprocess.run(
            'curl -6 "http://[::1]:80/"',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        p2 = subprocess.run(
            "curl http://127.0.0.1:80",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if p.returncode != 0 and p2.returncode != 0:
            print_error("Could not curl first")
            print(p.stdout.decode("utf-8"))
            print(p.stderr.decode("utf-8"))
            print_error("Could not curl second")
            print(p2.stdout.decode("utf-8"))
            print(p2.stderr.decode("utf-8"))
            return 1
        else:
            return 0

    if "switch" in config:
        p = subprocess.run(
            'docker exec frontend sh -c "ping -c 1 db"',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        check_subprocess(p, "Could not ping")
        return 0

    return 1


if __name__ == "__main__":
    output = check_arguments(sys.argv[1:])

    configurations = os.listdir("config-examples")
    configurations = [conf for conf in configurations if conf.endswith(".yaml")]
    configurations.sort()

    for config in configurations:
        print(f"\n{'-' * 80}\n")

        if "switch" in config and (
            not is_root() or is_github_actions() or output == OUTPUT_K8S
        ):
            print_warning(
                f"Will skip {config} because it uses a switch. Thus, it requires to be root (sudo) to manipulate veth."
            )
            continue

        path = os.path.join("config-examples", config)
        print_info(f"Testing {path}...\n")

        # build docker image for external container
        if "external" in config:
            build_external_image(output)

        p = subprocess.run(
            f"cp {path} config.yaml",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        check_subprocess(p, f"Error cp of {path}")

        print("Building images and generating IPv6 configuration...")
        make_cmd = "make ipv6" if output == OUTPUT_COMPOSE else "make k8s_ipv6"
        cmd = f"make clean && make images && {make_cmd}"
        p = subprocess.run(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        check_subprocess(p, "Could not make")

        print("Starting...")
        make_cmd = "make start" if output == OUTPUT_COMPOSE else "make k8s_start"
        p = subprocess.run(
            make_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        check_subprocess(p, "Could not start")

        print("Waiting for startup before executing curl...")
        time.sleep(3 if output == OUTPUT_COMPOSE else 25)

        print("Requesting...")
        req = requesting(output)
        if not req:
            print_success(f"\nPassed {path}")
        else:
            sys.exit(-1)

        make_cmd = "make stop" if output == OUTPUT_COMPOSE else "make k8s_stop"
        p = subprocess.run(
            make_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        check_subprocess(p, "Cannot stop")

    sys.exit(os.EX_OK)
