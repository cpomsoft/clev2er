"""pytest functions to test
        src/clev2er/tools/run_chain.py: runc_chain()
"""

import logging
import multiprocessing as mp
import os

import pytest
import xmltodict  # for parsing xml to python dict
from envyaml import (  # for parsing YAML files which include environment variables
    EnvYAML,
)

from clev2er.tools.run_chain import run_chain
from clev2er.utils.xml.xml_funcs import set_xml_dict_types

# pylint: disable=too-many-locals

log = logging.getLogger(__name__)


@pytest.mark.parametrize("mp_enabled", [(False), (True)])
def test_run_chain(mp_enabled):
    """pytest functions to test src/clev2er/tools/run_chain.py: runc_chain()"""
    chain_name = "testchain"
    base_dir = os.environ["CLEV2ER_BASE_DIR"]
    assert base_dir is not None

    config_file = f"{base_dir}/config/main_config.xml"
    assert os.path.exists(config_file), f"config file {config_file} does not exist"

    with open(config_file, "r", encoding="utf-8") as file:
        config_xml = file.read()

    # Use xmltodict to parse and convert
    # the XML document
    try:
        config = dict(xmltodict.parse(config_xml))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        assert False, f"ERROR: config file {config_file} xml format error : {exc}"

    # Convert all str values to correct types: bool, int, float, str
    set_xml_dict_types(config)
    config["chain"]["chain_name"] = chain_name
    config["chain"]["use_multi_processing"] = mp_enabled

    # Need to set MP mode, so Linux doesn't default to fork()
    if mp_enabled:
        mp.set_start_method("spawn")

    algorithm_list_file = f"{base_dir}/config/algorithm_lists/{chain_name}_A001.yml"

    assert os.path.exists(algorithm_list_file)

    # Load and parse the algorithm list
    try:
        yml = EnvYAML(
            algorithm_list_file
        )  # read the YML and parse environment variables
    except ValueError as exc:
        assert False, f"can not read algorithm list YML file {exc}"

    # Extract the algorithms list from the dictionary read from the YAML file
    try:
        algorithm_list = yml["algorithms"]
    except KeyError:
        assert False, "KeyError for key algorithms"

    l1b_file_list = [
        f"{os.environ['CLEV2ER_BASE_DIR']}/"
        "testdata/cs2/l1bfiles/CS_OFFL_SIR_LRM_1B_20200930T235609_20200930T235758_D001.nc",
        f"{os.environ['CLEV2ER_BASE_DIR']}/"
        "testdata/cs2/l1bfiles/CS_OFFL_SIR_SIN_1B_20190511T005631_20190511T005758_D001.nc",
    ]

    success, num_errors, num_files_processed, num_skipped = run_chain(
        l1b_file_list=l1b_file_list,
        config=config,
        algorithm_list=algorithm_list,
        log=log,
    )

    assert success, "run_chain return failure status"
    assert num_errors == 0
    assert num_files_processed == len(l1b_file_list)
    assert num_skipped == 0
