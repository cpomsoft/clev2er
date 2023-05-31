"""pytest of algorithm
   clev2er.algorithms.cryotempo.alg_skip_on_area_bounds.py
"""
import glob
import logging
import os

from netCDF4 import Dataset  # pylint: disable=E0611

from clev2er.algorithms.cryotempo.alg_skip_on_area_bounds import Algorithm

log = logging.getLogger(__name__)


def test_alg_skip_on_area_bounds() -> None:
    """test of Algorithm in clev2er.algorithms.cryotempo.alg_skip_on_area_bounds.py"""

    base_dir = os.environ["CLEV2ER_BASE_DIR"]
    assert base_dir is not None

    # Initialise the Algorithm
    thisalg = Algorithm(config=None)  # no config used for this alg

    # -------------------------------------------------------------------------
    # Test with LRM file. Should return (True,'') and insert "LRM" in
    #                     shared_dict["instr_mode"]

    l1b_file = glob.glob(f"{base_dir}/testdata/cs2/l1bfiles/*LRM*.nc")[0]
    try:
        l1b = Dataset(l1b_file)
        log.info("Opened %s", l1b_file)
    except IOError:
        assert False, f"{l1b_file} could not be read"

    # Run  Algorithm.process()
    shared_dict = {}
    # This should fail, as algorithm expects shared_dict['instr_mode'] to be present
    success, _ = thisalg.process(l1b, shared_dict, log, 0)

    assert (
        success is False
    ), "Algorithm.process should fail as no shared_dict['instr_mode']"

    shared_dict["instr_mode"] = "LRM"

    # This should fail, as L1b file is located outside cryosphere
    success, _ = thisalg.process(l1b, shared_dict, log, 0)

    assert success is False, "should fail as L1b file is outside cryosphere"

    l1b_file = glob.glob(f"{base_dir}/testdata/cs2/l1bfiles/*LRM*.nc")[2]
    try:
        l1b = Dataset(l1b_file)
        log.info("Opened %s", l1b_file)
    except IOError:
        assert False, f"{l1b_file} could not be read"

    # This should fail, as L1b file is located outside cryosphere
    success, _ = thisalg.process(l1b, shared_dict, log, 0)

    assert success, f"should pass as L1b file {l1b_file} passes over Greenland"
