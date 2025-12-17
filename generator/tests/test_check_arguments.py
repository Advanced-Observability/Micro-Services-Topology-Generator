import os
import pytest

import generator.generator


def test_no_arguments(capsys):
    # test with no arguments
    with pytest.raises(SystemExit):
        generator.generator.gen_config_files()

    captured = capsys.readouterr()
    assert "the following arguments are required" in captured.err, "Unexpected output"


def test_wrong_ip_version(capsys):
    with pytest.raises(SystemExit):
        generator.generator.gen_config_files(["--ip", "5"])

    captured = capsys.readouterr()
    assert "choose from 4, 6" in captured.err, "Unexpected output"


def test_ioam_with_ipv4(capsys):
    with pytest.raises(SystemExit):
        generator.generator.gen_config_files(["--ip", "4", "--ioam"])

    captured = capsys.readouterr()
    assert "IOAM requires IPv6!" in captured.out, "Unexpected output"


def test_clt_with_wrong_parameters(capsys):
    with pytest.raises(SystemExit):
        generator.generator.gen_config_files(["--clt", "--ip", "6"])
    captured = capsys.readouterr()
    assert "CLT requires Jaeger!" in captured.out, "Unexpected output"

    with pytest.raises(SystemExit):
        generator.generator.gen_config_files(["--clt", "--ip", "6", "--ioam"])
    captured = capsys.readouterr()
    assert "CLT requires Jaeger!" in captured.out, "Unexpected output"


def test_with_valid_configuration(capsys):
    ret = generator.generator.gen_config_files(
        [
            "--config",
            "tests/configurations/valid.yaml",
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
