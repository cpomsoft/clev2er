"""pytest of algorithm
   clev2er.algorithms.testchain.alg_template1.py
"""
import logging
import os

import pytest
from netCDF4 import Dataset  # pylint:disable=no-name-in-module

from clev2er.algorithms.testchain.alg_template1 import Algorithm
from clev2er.utils.config.load_config_settings import load_config_files

# each algorithm test shares some common class code, so pylint: disable=duplicate-code

log = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "l1b_file",
    [
        ("CS_OFFL_SIR_SIN_1B_20190504T122546_20190504T122726_D001.nc"),
        ("CS_OFFL_SIR_LRM_1B_20200930T231147_20200930T232634_D001.nc"),
    ],
)
def test_alg_template1(l1b_file) -> None:
    """test of clev2er.algorithms.testchain.alg_template1.py"""

    chain_name = "testchain"

    # ------------------------------------------------------------------------
    # Load chain config files
    # ------------------------------------------------------------------------

    base_dir = os.environ["CLEV2ER_BASE_DIR"]
    assert base_dir is not None

    # Load merged config file for chain
    config, _, _, _, _ = load_config_files(chain_name)

    # Enforce sequential processing mode for this test
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
    shared_dict: dict = {}

    # Run the Algorithm.process() function
    success, _ = thisalg.process(l1b, shared_dict)

    # Clean up algorithm
    thisalg.finalize()

    assert success, f"algorithm {__name__}should not fail"

    assert "twice_ocean_tide_01" in shared_dict, "twice_ocean_tide_01 not in shared_dict"

    # Test that the values produced by the algorithm are correct
    for index, tide_value in enumerate(l1b["ocean_tide_01"][:].data):
        assert shared_dict["twice_ocean_tide_01"][index] == (tide_value * 2)
