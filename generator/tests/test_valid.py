import os
import pytest

import generator.generator


def test_with_valid_configuration(capsys):
    for i in range(1, 12):
        ret = generator.generator.gen_config_files([
            '--config', f'tests/configurations/valid_{i}.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])

        assert ret == os.EX_OK
        captured = capsys.readouterr()
        assert "Built architecture" in captured.out, "Unexepected output"
