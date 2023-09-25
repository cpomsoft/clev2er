"""utils.config.load_config_settings.py

Common functions to load chain configuration files
"""

import os
import string

import xmltodict  # for parsing xml to python dict
from envyaml import (  # for parsing YAML files which include environment variables
    EnvYAML,
)

from clev2er.utils.xml.xml_funcs import set_xml_dict_types

# pylint: disable=too-many-branches


def load_config_files(chain_name: str, baseline: str = "") -> dict:
    """function to load config files for a chain

    Args:
        chain_name (str) : name of the chain to load
        baseline (str, optional): baseline char A..Z, default="" (none specified)
                                  in which case the highest baseline (close to Z) is found

    Raises: KeyError, OSError, ValueError
    """
    base_dir = os.environ["CLEV2ER_BASE_DIR"]

    # --------------------------------------------
    # Load main run control XML config file
    #   $CLEV2ER_BASE_DIR/config/main_config.xml
    # --------------------------------------------

    config_file = f"{base_dir}/config/main_config.xml"
    if not os.path.exists(config_file):
        raise OSError(f"{config_file} not found")

    with open(config_file, "r", encoding="utf-8") as file:
        config_xml = file.read()

    # Use xmltodict to parse and convert the XML document
    try:
        config = dict(xmltodict.parse(config_xml))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise OSError(f"{config_file} xml format error : {exc}") from exc

    # Convert all str values from XML to correct types: bool, int, float, str
    # and evaluate env variables
    set_xml_dict_types(config)

    print(f"Using Main config file {config_file}")

    # --------------------------------------------
    # Load chain config file
    #   $CLEV2ER_BASE_DIR/config/main_config.xml
    # --------------------------------------------

    # Load chain config file by finding latest chain baseline
    # ie baseline B before A
    chain_config_file = None
    if baseline:
        reverse_alphabet_list = [baseline]
    else:
        reverse_alphabet_list = list(string.ascii_uppercase[::-1])
    for _baseline in reverse_alphabet_list:
        _config_file = (
            f"{base_dir}/config/chain_configs/{chain_name}_{_baseline}001.yml"
        )
        if os.path.exists(_config_file):
            baseline = _baseline
            chain_config_file = _config_file
            break
        _config_file = (
            f"{base_dir}/config/chain_configs/{chain_name}_{_baseline}001.xml"
        )
        if os.path.exists(_config_file):
            baseline = _baseline
            chain_config_file = _config_file
            break
    if not chain_config_file:
        raise OSError(f"No chain config file found for chain {chain_name}")

    if chain_config_file[-4:] == ".xml":
        print(f"Using XML chain config file {chain_config_file}")

        with open(chain_config_file, "r", encoding="utf-8") as file:
            config_xml = file.read()

        # Use xmltodict to parse and convert the XML document
        try:
            chain_config = dict(xmltodict.parse(config_xml))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            raise OSError(f"{config_file} xml format error : {exc}") from exc

        # Convert all str values from XML to correct types: bool, int, float, str
        # and evaluate env variables
        set_xml_dict_types(chain_config)

        # Remove the root xml level as we don't need it
        chain_config = chain_config["configuration"]

    if chain_config_file[-4:] == ".yml":
        print(f"Using YML chain config file {chain_config_file}")

        chain_config = EnvYAML(
            chain_config_file
        ).export()  # read the YML and parse environment variables

    # override "chain" settings from chain_config if present
    if "chain" in chain_config:
        for key in chain_config["chain"]:
            if key in config["chain"]:
                config["chain"][key] = chain_config["chain"][key]
        chain_config.pop("chain", None)

    config = config | chain_config

    return config
