import os
import pytest

import generator.generator


def is_github_actions() -> bool:
    return os.getenv("GITHUB_ACTIONS") == "true"


def test_with_valid_configuration(capsys):
    for i in range(1, 14):
        # will skip switch in GitHub actions because environment does not have OVS kernel module
        if i in [12, 13] and is_github_actions():
            continue

        ret = generator.generator.gen_config_files(
            [
                "--config",
                f"tests/configurations/valid_{i}.yaml",
                "--clt",
                "--ip",
                "6",
                "--ioam",
                "--jaeger",
            ]
        )

        assert ret == os.EX_OK
        captured = capsys.readouterr()
        assert "Built architecture" in captured.out, "Unexepected output"
