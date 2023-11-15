"""pytest of utils.config.load_config_files()
"""
import os

from clev2er.utils.config.load_config_settings import load_config_files


def test_load_config_files():
    """pytest function for utils.config.load_config_files()"""

    chain_name = "testchain"

    try:
        (
            config,
            baseline,
            version,
            _,  # main_config_file
            _,  # chain_config_file
        ) = load_config_files(chain_name)
    except (KeyError, OSError, ValueError) as exc:
        assert False, f"Loading config file failed due to {exc}"

    assert isinstance(config, dict), "config is not a dictionary"

    # Test that we have read config settings from the main run control config

    assert "chain" in config, "chain setting should be a toplevel of config dict"
    assert (
        "use_multi_processing" in config["chain"]
    ), "use_multi_processing setting should be in config.chain dict"
    assert isinstance(
        config["chain"]["use_multi_processing"], bool
    ), "use_multi_processing should be of type bool"

    # Test that we have read config settings from the "testchain" chain config

    assert "log_files" in config
    assert config["log_files"]["info"] == "/tmp/info.log"

    assert config["chain"]["stop_on_error"]

    try:
        (
            config,
            baseline,
            version,
            _,  # main_config_file
            _,  # chain_config_file
        ) = load_config_files("cryotempo", baseline="C")
    except (KeyError, OSError, ValueError) as exc:
        assert False, f"Loading config file failed due to {exc}"

    assert config["sin_geolocation"]["phase_method"] == 3

    try:
        (
            config,
            baseline,
            version,
            _,  # main_config_file
            _,  # chain_config_file
        ) = load_config_files("cryotempo")
    except (KeyError, OSError, ValueError) as exc:
        assert False, f"Loading config file failed due to {exc}"

    assert config["sin_geolocation"]["phase_method"] == 3

    try:
        (
            config,
            baseline,
            version,
            _,  # main_config_file
            _,  # chain_config_file
        ) = load_config_files("cryotempo", baseline="C", version=1)
    except (KeyError, OSError, ValueError) as exc:
        assert False, f"Loading config file failed due to {exc}"

    assert config["sin_geolocation"]["phase_method"] == 3

    try:
        (
            config,
            baseline,
            version,
            _,  # main_config_file
            _,  # chain_config_file
        ) = load_config_files(
            "cryotempo",
            chain_config_file=f"{os.environ['CLEV2ER_BASE_DIR']}/"
            "config/chain_configs/cryotempo/cryotempo_C001.yml",
        )
    except (KeyError, OSError, ValueError) as exc:
        assert False, f"Loading config file failed due to {exc}"

    assert baseline == "C"
    assert version == 1

    assert config["sin_geolocation"]["phase_method"] == 3
