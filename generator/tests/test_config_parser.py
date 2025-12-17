import pytest

import generator.generator


def test_entities_with_same_name():
    with pytest.raises(RuntimeError) as exception:
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_0.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])

    assert "Names of entities must be unique" in str(exception.value), "Unexpected exception message"


def test_entity_with_unknown_type(capsys):
    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_1.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])

    captured = capsys.readouterr()
    assert "Entity frontend has unknown type" in captured.out, "Unexpected output"


def test_router_without_mandatory_field(capsys):
    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_2.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])

    captured = capsys.readouterr()
    assert "Router r1 must have some connections" in captured.out, "Unexpcted output"


def test_service_without_mandatory_field(capsys):
    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_3.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])

    captured = capsys.readouterr()
    assert "Entity frontend missing endpoints field" in captured.out, "Unexpected output"

    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_3_2.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])

    captured = capsys.readouterr()
    assert "Entity frontend missing port field" in captured.out, "Unexpected output"


def test_service_with_bad_endpoint(capsys):
    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_4.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])

    captured = capsys.readouterr()
    assert "Endpoint" in captured.out and "of entity frontend missing field psize" in captured.out, "Unexpcted output"

    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_4_2.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])

    captured = capsys.readouterr()
    assert "Endpoint" in captured.out and "of entity frontend missing field entrypoint" in captured.out, "Unexpcted output"


def test_with_cycles(capsys):
    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_5.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])

    captured = capsys.readouterr()
    assert "Cannot have cycles in the architecture" in captured.out, "Unexpcted output"


def test_without_unique_ports(capsys):
    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_6.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])

    captured = capsys.readouterr()
    assert "This port is already used by" in captured.out, "Unexpcted output"


def test_check_connectivity(capsys):
    # intermediary does not exist
    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_7.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])
    captured = capsys.readouterr()
    assert "Destination r1" in captured.out and "does not exists" in captured.out, "Unexpected output"

    # intermediary is not a router
    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_7_2.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])
    captured = capsys.readouterr()
    assert "Intermediary hop" in captured.out and "is not a router" in captured.out, "Unexpected output"

    # no coherency with connections in router
    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_7_3.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])
    captured = capsys.readouterr()
    assert "Intermediary hop" in captured.out and "should specify" in captured.out, "Unexpected output"

    # last node must be a service
    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_7_4.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])
    captured = capsys.readouterr()
    assert "Last hop" in captured.out and "must be a end host" in captured.out, "Unexpected output"

    # direct connection: neighbour must exist
    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_7_5.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])
    captured = capsys.readouterr()
    assert "entity that does not exists" in captured.out, "Unexpected output"

    # direct connection: last node must be a service
    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_7_6.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])
    captured = capsys.readouterr()
    assert "Destination of connection" in captured.out and "is not a service" in captured.out, "Unexpected output"

def test_check_connection_specifications(capsys):
    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_8_1.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])
    captured = capsys.readouterr()
    assert "Entity frontend missing field path for connection" in captured.out, "Unexpected output"

    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_8_2.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])
    captured = capsys.readouterr()
    assert "Entity frontend has unexpected field maxime for connection" in captured.out, "Unexpected output"

    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_8_3.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])
    captured = capsys.readouterr()
    assert "Entity r1 missing field path for connection" in captured.out, "Unexpected output"

def test_check_impairments(capsys):
    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_9_1.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])
    captured = capsys.readouterr()
    assert "MTU option must be an int" in captured.out, "Unexpected output"

    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_9_2.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])
    captured = capsys.readouterr()
    assert "Buffer size option must be an int" in captured.out, "Unexpected output"

    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_9_3.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])
    captured = capsys.readouterr()
    assert "Rate option must be a rate" in captured.out, "Unexpected output"

    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_9_4.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])
    captured = capsys.readouterr()
    assert "delay option must be a time" in captured.out, "Unexpected output"

    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_9_5.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])
    captured = capsys.readouterr()
    assert "loss option must be a percentage" in captured.out, "Unexpected output"

def test_check_timers(capsys):
    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_10_1.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])
    captured = capsys.readouterr()
    assert "Missing field option for timer" in captured.out, "Unexpected output"

    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_10_2.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])
    captured = capsys.readouterr()
    assert "Specified option someOption for timer" in captured.out and "is not an impairment" in captured.out, "Unexpected output"


    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_10_3.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])
    captured = capsys.readouterr()
    assert "Start must be specified as an integer/float amount of seconds" in captured.out, "Unexpected output"

    with pytest.raises(RuntimeError):
        generator.generator.gen_config_files([
            '--config', 'tests/configurations/invalid_10_4.yml',
            '--clt', '--ip', '6', '--ioam', '--jaeger'
        ])
    captured = capsys.readouterr()
    assert "Option buffer_size for timer" in captured.out and "has unexpected format" in captured.out, "Unexpected output"
