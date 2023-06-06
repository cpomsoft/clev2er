"""pytest of algorithm
   clev2er.algorithms.cryotempo.alg_fes2014b_tide_correction.py
"""
import logging
import os

from envyaml import (  # for parsing YAML files which include environment variables
    EnvYAML,
)
from netCDF4 import Dataset  # pylint: disable=E0611

from clev2er.algorithms.cryotempo.alg_fes2014b_tide_correction import Algorithm

# Similar lines in 2 files, pylint: disable=R0801

log = logging.getLogger(__name__)


def test_alg_fes2014b_tide_correction() -> None:
    """test of Algorithm in clev2er.algorithms.cryotempo.alg_fes2014b_tide_correction.py"""

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

    # Set to Sequential Processing
    config["chain"]["use_multi_processing"] = False

    # Initialise the Algorithm
    try:
        thisalg = Algorithm(config=config)  # no config used for this alg
    except KeyError as exc:
        assert False, f"Could not initialize algorithm {exc}"

    # -------------------------------------------------------------------------
    # Test with SIN L1b file

    l1b_file = (
        f"{base_dir}/testdata/cs2/l1bfiles/"
        "CS_OFFL_SIR_SIN_1B_20190504T122546_20190504T122726_D001.nc"
    )
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
    shared_dict["hemisphere"] = "south"
    shared_dict["instr_mode"] = "SIN"

    shared_dict["lats_nadir"] = l1b["lat_20_ku"][:].data
    shared_dict["lons_nadir"] = (
        l1b["lon_20_ku"][:].data % 360.0
    )  # [-180,+180E] -> 0..360E

    # This should fail, as no matching FES2014b
    success, _ = thisalg.process(l1b, shared_dict, log, 0)

    assert success, "Should succeed as matching FES2014b file available"
    assert (
        "fes2014b_corrections" in shared_dict
    ), "fes2014b_corrections should have been added"

    assert (
        "ocean_tide_20" in shared_dict["fes2014b_corrections"]
    ), "fes2014b_corrections.ocean_tide_20 should have been added to shared_dict"
