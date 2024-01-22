"""pytest of algorithm
   clev2er.algorithms.cryotempo.alg_surface_type.py
"""
import logging
import os

from netCDF4 import Dataset  # pylint: disable=E0611

from clev2er.algorithms.cryotempo.alg_surface_type import Algorithm
from clev2er.utils.config.load_config_settings import load_config_files

# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
# pylint: disable=R0801 # warning for similar lines

log = logging.getLogger(__name__)


def test_alg_skip_on_area_bounds() -> None:
    """test of Algorithm in clev2er.algorithms.cryotempo.alg_surface_type.py"""

    base_dir = os.environ["CLEV2ER_BASE_DIR"]
    assert base_dir is not None

    # Load merged config file for chain
    config, _, _, _, _ = load_config_files("cryotempo")

    # Set to Sequential Processing
    config["chain"]["use_multi_processing"] = False

    # Initialise the Algorithm
    try:
        thisalg = Algorithm(config, log)  # no config used for this alg
    except KeyError as exc:
        assert False, f"Could not initialize algorithm {exc}"

    # -------------------------------------------------------------------------
    # Test with LRM file. Should return (True,'') and insert "LRM" in
    #                     shared_dict["instr_mode"]

    l1b_file = (
        f"{base_dir}/testdata/cs2/l1bfiles/"
        "CS_OFFL_SIR_LRM_1B_20200930T191158_20200930T191302_D001.nc"
    )
    try:
        l1b = Dataset(l1b_file)
        log.info("Opened %s", l1b_file)
    except IOError:
        assert False, f"{l1b_file} could not be read"

    # Run  Algorithm.process()
    shared_dict = {}

    shared_dict["l1b_file_name"] = l1b_file
    shared_dict["hemisphere"] = "north"
    shared_dict["num_20hz_records"] = l1b["lat_20_ku"].size

    shared_dict["lats_nadir"] = l1b["lat_20_ku"][:].data
    shared_dict["lons_nadir"] = l1b["lon_20_ku"][:].data % 360.0  # [-180,+180E] -> 0..360E

    # This should fail, as file is outside cryosphere
    success, error_str = thisalg.process(l1b, shared_dict)

    assert success is False, "Algorithm.process should fail as file is outside cryosphere"
    assert "SKIP_OK" in error_str, "Algorithm.process should fail with SKIP_OK"

    # Test with SIN file in Southern Hemisphere
    l1b_file = (
        f"{base_dir}/testdata/cs2/l1bfiles/"
        "CS_OFFL_SIR_SIN_1B_20190504T122546_20190504T122726_D001.nc"
    )
    try:
        l1b = Dataset(l1b_file)
        log.info("Opened %s", l1b_file)
    except IOError:
        assert False, f"{l1b_file} could not be read"

    shared_dict["l1b_file_name"] = l1b_file
    shared_dict["hemisphere"] = "south"

    shared_dict["lats_nadir"] = l1b["lat_20_ku"][:].data
    shared_dict["lons_nadir"] = l1b["lon_20_ku"][:].data % 360.0  # [-180,+180E] -> 0..360E

    # This should succeed,
    success, error_str = thisalg.process(l1b, shared_dict)

    assert success, "Algorithm.process should succeed"
