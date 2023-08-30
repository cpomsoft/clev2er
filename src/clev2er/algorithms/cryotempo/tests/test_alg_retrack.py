"""pytest of algorithm
   clev2er.algorithms.cryotempo.alg_retrack.py
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

from clev2er.algorithms.cryotempo.alg_retrack import Algorithm

# Similar lines in 2 files, pylint: disable=R0801
# pylint: disable=too-many-statements

log = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "l1b_file",
    [
        ("CS_OFFL_SIR_SIN_1B_20190504T122546_20190504T122726_D001.nc"),
        ("CS_OFFL_SIR_LRM_1B_20200930T231147_20200930T232634_D001.nc"),
    ],
)
def test_alg_retrack(l1b_file) -> None:
    """test of clev2er.algorithms.cryotempo.alg_retrack.py

    runs retracker algorithm on an LRM and SIN L1b file
    """

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

    # Initialise the Algorithm
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
    shared_dict = {}

    # setup dummy shared_dict results from other algorithms
    shared_dict["l1b_file_name"] = l1b_file
    shared_dict["num_20hz_records"] = l1b["lat_20_ku"].size
    if "SIR_SIN_1B" in l1b_file:
        shared_dict["instr_mode"] = "SIN"
    if "SIR_LRM_1B" in l1b_file:
        shared_dict["instr_mode"] = "LRM"
    shared_dict["waveforms_to_include"] = np.full_like(l1b["lat_20_ku"][:].data, True)
    ind_meas_1hz_20_ku = l1b.variables["ind_meas_1hz_20_ku"][:].data
    mod_dry_tropo_cor_20 = l1b.variables["mod_dry_tropo_cor_01"][:].data[
        ind_meas_1hz_20_ku
    ]  # DRY
    # Dummy some geo corrections with just dry tropo
    shared_dict["sum_cor_20_ku"] = mod_dry_tropo_cor_20

    # Can set these to show waveforms in the retrackers (note blocks)
    config["tcog_retracker"]["show_plots"] = False
    config["mc_retracker"]["show_plots"] = False

    # Run the alg process
    success, _ = thisalg.process(l1b, shared_dict)
    assert success, "algorithm should not fail"

    assert "range_cor_20_ku" in shared_dict, "range_cor_20_ku not in shared_dict"
    assert (
        shared_dict["percent_retracker_failure"] < 5
    ), "more than 5% retracker failure"
    assert (
        shared_dict["percent_retracker_failure"] >= 0
        and shared_dict["percent_retracker_failure"] <= 100
    ), f'% retracker failure ({shared_dict["percent_retracker_failure"]}) not in range 0..100%'
