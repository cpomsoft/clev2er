"""pytest functions to test
        src/clev2er/tools/run_chain.py: runc_chain()
"""

import glob
import logging
import os

import pytest
from envyaml import (  # for parsing YAML files which include environment variables
    EnvYAML,
)

from clev2er.tools.run_chain import run_chain

log = logging.getLogger(__name__)


@pytest.mark.parametrize("mp_enabled", [(False), (True)])
def test_run_chain(mp_enabled):
    """pytest functions to test src/clev2er/tools/run_chain.py: runc_chain()"""
    chain_name = "testchain"
    base_dir = os.environ["CLEV2ER_BASE_DIR"]
    assert base_dir is not None

    l1b_file_list = glob.glob(f"{base_dir}/testdata/cs2/l1bfiles/*.nc")

    assert len(l1b_file_list) > 0, "No L1b test files found"

    # -------------------------------------------------------------------------
    # Load Project's main YAML configuration file
    #   - default is $CLEV2ER_BASE_DIR/config/main_config.yml
    #   - or set by --conf <filepath>.yml
    # -------------------------------------------------------------------------

    config_file = f"{base_dir}/config/main_config.yml"
    assert os.path.exists(config_file)

    try:
        config = EnvYAML(config_file)  # read the YML and parse environment variables
    except ValueError as exc:
        assert False, f"Can not read {config_file}: {exc}"

    config["chain"]["chain_name"] = chain_name
    config["chain"]["use_multi_processing"] = mp_enabled

    algorithm_list_file = f"{base_dir}/config/algorithm_lists/{chain_name}.yml"

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

    success, num_errors, num_files_processed = run_chain(
        l1b_file_list=l1b_file_list,
        config=config,
        algorithm_list=algorithm_list,
        log=log,
    )

    assert success, "run_chain return failure status"
    assert num_errors == 0
    assert num_files_processed == len(l1b_file_list)
