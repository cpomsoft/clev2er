"""pytest of algorithm
   clev2er.algorithms.cryotempo.alg_basin_ids.py
"""
import logging
import os
from typing import Any, Dict

import numpy as np
import pytest
from netCDF4 import Dataset  # pylint: disable=E0611

from clev2er.algorithms.cryotempo.alg_basin_ids import Algorithm
from clev2er.algorithms.cryotempo.alg_skip_on_area_bounds import (
    Algorithm as SkipArea,
)
from clev2er.utils.config.load_config_settings import load_config_files

# Similar lines in 2 files, pylint: disable=R0801
# pylint: disable=too-many-statements
# pylint: disable=too-many-locals

log = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "l1b_file",
    [
        (
            "CS_OFFL_SIR_SIN_1B_20190504T122546_20190504T122726_D001.nc"
        ),  # SIN, over AIS margin
        (
            "CS_OFFL_SIR_SIN_1B_20190511T005631_20190511T005758_D001.nc"
        ),  # SIN, over GIS margin
        ("CS_OFFL_SIR_LRM_1B_20200911T023800_20200911T024631_D001.nc"),  # LRM, over AIS
        ("CS_LTA__SIR_LRM_1B_20200930T235609_20200930T235758_E001.nc"),  # LRM, over GRN
    ],
)
def test_alg_basin_ids(l1b_file) -> None:
    """test of clev2er.algorithms.cryotempo.alg_basin_ids.py"""

    base_dir = os.environ["CLEV2ER_BASE_DIR"]
    assert base_dir is not None

    # Load merged config file for chain
    config, _, _, _, _ = load_config_files("cryotempo")

    # Set to Sequential Processing
    config["chain"]["use_multi_processing"] = False

    # Initialise other Algorithms required by test
    try:
        skip_area = SkipArea(config, log)
    except KeyError as exc:
        assert False, f"Could not initialize SkipArea algorithm {exc}"

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
    shared_dict: Dict[str, Any] = {}

    # setup dummy shared_dict results from other algorithms
    if "SIR_SIN_1B" in l1b_file:
        shared_dict["instr_mode"] = "SIN"
    if "SIR_LRM_1B" in l1b_file:
        shared_dict["instr_mode"] = "LRM"

    # Dummy final lat,lon using nadir locs
    shared_dict["latitudes"] = l1b["lat_20_ku"][:].data
    shared_dict["longitudes"] = l1b["lon_20_ku"][:].data

    # Run other alg process required by test to fill in
    # required shared_dict parameters
    success, _ = skip_area.process(l1b, shared_dict)
    assert success, "skip_area algorithm should not fail"

    # Run the alg process
    success, _ = thisalg.process(l1b, shared_dict)
    assert success, "algorithm should not fail"

    assert "basin_mask_values_rignot" in shared_dict, "basin_mask_values_rignot missing"
    assert "basin_mask_values_zwally" in shared_dict, "basin_mask_values_zwally missing"

    # Test that the mask values arrays have the correct length

    assert len(shared_dict["basin_mask_values_rignot"]) == len(l1b["lat_20_ku"][:].data)
    assert len(shared_dict["basin_mask_values_zwally"]) == len(l1b["lat_20_ku"][:].data)

    # Test values returned are within expected ranges for Zwally
    if shared_dict["hemisphere"] == "south":
        # expected range 0..27 for Zwally basins
        assert np.logical_and(
            shared_dict["basin_mask_values_zwally"] >= 0,
            shared_dict["basin_mask_values_zwally"] <= 27,
        ).all()
        log.info(shared_dict["basin_mask_values_rignot"])
        # expected range 0..19 for Rignot basins
        assert np.logical_and(
            shared_dict["basin_mask_values_rignot"] >= 0,
            shared_dict["basin_mask_values_rignot"] <= 19,
        ).all()
