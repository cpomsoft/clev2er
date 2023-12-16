"""pytest of algorithm
   clev2er.algorithms.cryotempo.alg_cats2008a_tide_correction.py
"""
import logging
import os

from netCDF4 import Dataset  # pylint: disable=E0611

from clev2er.algorithms.cryotempo.alg_cats2008a_tide_correction import Algorithm
from clev2er.algorithms.cryotempo.alg_surface_type import Algorithm as SurfaceType
from clev2er.utils.config.load_config_settings import load_config_files

# Similar lines in 2 files, pylint: disable=R0801

log = logging.getLogger(__name__)


def test_alg_cats2008a_tide_correction() -> None:
    """test of Algorithm in clev2er.algorithms.cryotempo.alg_cats2008a_tide_correction.py"""

    base_dir = os.environ["CLEV2ER_BASE_DIR"]
    assert base_dir is not None

    # Load merged config file for chain
    config, _, _, _, _ = load_config_files("cryotempo")

    # Set to Sequential Processing
    config["chain"]["use_multi_processing"] = False

    try:
        surface_type = SurfaceType(config, log)
    except KeyError as exc:
        assert False, f"Could not initialize SurfaceType algorithm {exc}"

    # Initialise the Algorithm
    try:
        thisalg = Algorithm(config, log)  # no config used for this alg
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

    success, _ = surface_type.process(l1b, shared_dict)
    assert success, "surface_type algorithm should not fail"

    success, _ = thisalg.process(l1b, shared_dict)

    assert success, "Should succeed as matching CATS2008a file available"
    assert "cats_tide" in shared_dict, "cats_tide should have been added"
    assert shared_dict[
        "cats_tide_required"
    ], "cats_tide_required should have been added and be True"
