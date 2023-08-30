"""pytest of algorithm
   clev2er.algorithms.cryotempo.alg_filter_height.py
"""
import logging
import os
import string
from typing import Any, Dict

import numpy as np
import pytest
from envyaml import (  # for parsing YAML files which include environment variables
    EnvYAML,
)
from netCDF4 import Dataset  # pylint: disable=E0611

from clev2er.algorithms.cryotempo.alg_filter_height import Algorithm

# Similar lines in 2 files, pylint: disable=R0801

log = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "l1b_file",
    [
        ("CS_OFFL_SIR_SIN_1B_20190504T122546_20190504T122726_D001.nc"),  # SIN, over AIS
        ("CS_OFFL_SIR_SIN_1B_20190511T005631_20190511T005758_D001.nc"),  # SIN, over GIS
        ("CS_OFFL_SIR_LRM_1B_20200911T023800_20200911T024631_D001.nc"),  # LRM, over AIS
        ("CS_OFFL_SIR_LRM_1B_20200930T235609_20200930T235758_D001.nc"),  # LRM, over GRN
    ],
)
def test_alg_filter_height(l1b_file) -> None:
    """test of clev2er.algorithms.cryotempo.alg_filter_height.py"""

    base_dir = os.environ["CLEV2ER_BASE_DIR"]
    assert base_dir is not None

    config_file = f"{base_dir}/config/main_config.yml"
    assert os.path.exists(config_file), f"config file {config_file} does not exist"

    try:
        config = EnvYAML(config_file)  # read the YML and parse environment variables
    except ValueError as exc:
        assert (
            False
        ), f"ERROR: config file {config_file} has invalid or unset environment variables : {exc}"

    # Load cryotempo chain config file by finding latest baseline
    # ie baseline B before A
    reverse_alphabet_list = list(string.ascii_uppercase[::-1])
    baseline = None
    for _baseline in reverse_alphabet_list:
        config_file = f"{base_dir}/config/chain_configs/cryotempo_{_baseline}001.yml"
        if os.path.exists(config_file):
            baseline = _baseline
            break
    assert baseline, "No cryotempo baseline config file found"

    log.info("Using config file %s ", config_file)

    try:
        chain_config = EnvYAML(
            config_file
        )  # read the YML and parse environment variables
    except ValueError as exc:
        assert (
            False
        ), f"ERROR: config file {config_file} has invalid or unset environment variables : {exc}"

    # merge the two config files (with precedence to the chain_config)
    config = config.export() | chain_config.export()  # the export() converts to a dict

    # Set to Sequential Processing
    config["chain"]["use_multi_processing"] = False

    # Initialise any other Algorithms required by test

    # Initialise the Algorithm being tested
    try:
        thisalg = Algorithm(config, log)  # no config used for this alg
    except KeyError as exc:
        assert False, f"Could not initialize algorithm {exc}"

    # -------------------------------------------------------------------------
    # Test with L1b file

    l1b_file = f"{base_dir}/testdata/cs2/l1bfiles/{l1b_file}"
    try:
        l1b = Dataset(l1b_file)
        log.info("Opened %s", l1b_file)
    except IOError:
        assert False, f"{l1b_file} could not be read"

    # Run  Algorithm.process()
    shared_dict: Dict[str, Any] = {}

    # setup dummy shared_dict results from other algorithms
    if "SIR_SIN_1B" in l1b_file:
        shared_dict["instr_mode"] = "SIN"
    if "SIR_LRM_1B" in l1b_file:
        shared_dict["instr_mode"] = "LRM"
    shared_dict["hemisphere"] = "south"

    # Mock height_20_ku
    shared_dict["height_20_ku"] = np.full_like(
        l1b["lat_20_ku"][:].data, 4899.0, dtype="float"
    )
    shared_dict["height_20_ku"][0:5] = 6000.0
    shared_dict["height_20_ku"][6] = 4920.0

    # Mock dem_elevation_values
    shared_dict["dem_elevation_values"] = np.full_like(
        l1b["lat_20_ku"][:].data, 4899.0, dtype="float"
    )

    # Run other alg process required by test to fill in
    # required shared_dict parameters

    # Run the alg process
    success, _ = thisalg.process(l1b, shared_dict)
    assert success, "algorithm should not fail"

    # Test outputs of algorithm

    assert "height_filt" in shared_dict, "height_filt should be in shared_dict"
    num_invalid = np.count_nonzero(np.isnan(shared_dict["height_filt"]))
    assert num_invalid == 6
    num_invalid = np.count_nonzero(np.isnan(shared_dict["height_20_ku"]))
    assert num_invalid == 0
