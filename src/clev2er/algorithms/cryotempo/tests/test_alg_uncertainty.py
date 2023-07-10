"""pytest of algorithm
   clev2er.algorithms.cryotempo.alg_uncertainty.py
"""
import logging
import os
import string

import numpy as np
import pytest
from envyaml import (  # for parsing YAML files which include environment variables
    EnvYAML,
)
from netCDF4 import Dataset  # pylint: disable=E0611

from clev2er.algorithms.cryotempo.alg_identify_file import (
    Algorithm as IdentifyFile,
)
from clev2er.algorithms.cryotempo.alg_skip_on_area_bounds import (
    Algorithm as SkipArea,
)
from clev2er.algorithms.cryotempo.alg_uncertainty import Algorithm

# Similar lines in 2 files, pylint: disable=R0801
# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements

log = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "l1b_file",
    [
        "CS_OFFL_SIR_SIN_1B_20190504T122546_20190504T122726_D001.nc",  # SIN L1B within AIS
        "CS_OFFL_SIR_LRM_1B_20200911T023800_20200911T024631_D001.nc",  # LRM L1B within AIS
    ],
)
def test_alg_uncertainty(l1b_file) -> None:
    """test of clev2er.algorithms.cryotempo.alg_uncertainty.py"""

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

    log.info("Using config file %s", config_file)

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

    # Initialise the Algorithms
    try:
        thisalg = Algorithm(config=config)  # no config used for this alg
    except KeyError as exc:
        assert False, f"Could not initialize algorithm {exc}"

    try:
        identify_file = IdentifyFile(config=config)
    except KeyError as exc:
        assert False, f"Could not initialize IdentifyFile algorithm {exc}"

    try:
        skip_area = SkipArea(config=config)
    except KeyError as exc:
        assert False, f"Could not initialize SkipArea algorithm {exc}"

    # -------------------------------------------------------------------------
    # Test with L1b file

    l1b_file = f"{base_dir}/testdata/cs2/l1bfiles/{l1b_file}"
    try:
        l1b = Dataset(l1b_file)
        log.info("Opened %s", l1b_file)
    except IOError:
        assert False, f"{l1b_file} could not be read"

    # Run  Algorithm.process()
    shared_dict = {}

    # ----------------------------------------------------------
    # setup dummy shared_dict results from other algorithms
    # ----------------------------------------------------------

    shared_dict["l1b_file_name"] = l1b_file  # set by run controller

    shared_dict["lat_poca_20_ku"] = l1b["lat_20_ku"][:].data
    shared_dict["lon_poca_20_ku"] = l1b["lon_20_ku"][:].data % 360.0

    # ----------------------------------------------------------

    # Run previous CryoTEMPO algorithms.process() to generate required parameters

    success, _ = identify_file.process(l1b, shared_dict, log, 0)
    assert success, "identify_file algorithm should not fail"

    success, _ = skip_area.process(l1b, shared_dict, log, 0)
    assert success, "skip_area algorithm should not fail"

    # Run this algorithm's  process() function
    success, _ = thisalg.process(l1b, shared_dict, log, 0)
    assert success, "algorithm should not fail"

    # Test outputs from algorithm

    assert "uncertainty" in shared_dict, "uncertainty not in shared_dict"

    min_uncertainty = np.nanmin(shared_dict["uncertainty"])
    max_uncertainty = np.nanmax(shared_dict["uncertainty"])

    assert 0.0 < min_uncertainty < 0.3
    assert 2.0 < max_uncertainty < 2.5

    log.info("min_uncertainty %f", min_uncertainty)
    log.info("max_uncertainty %f", max_uncertainty)

    num_invalid = np.count_nonzero(np.isnan(shared_dict["uncertainty"]))
    num_valid = np.count_nonzero(~np.isnan(shared_dict["uncertainty"]))
    log.info("num_valid %d", num_valid)
    log.info("num_invalid %d", num_invalid)
