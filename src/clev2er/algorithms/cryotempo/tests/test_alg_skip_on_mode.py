"""pytest of algorithm
   clev2er.algorithms.cryotempo.alg_skip_on_mode.py
"""
import glob
import logging
import os

from netCDF4 import Dataset  # pylint: disable=E0611

from clev2er.algorithms.cryotempo.alg_skip_on_mode import Algorithm

# pylint: disable=R0801

log = logging.getLogger(__name__)


def test_alg_skip_on_mode() -> None:
    """test of Algorithm in clev2er.algorithms.cryotempo.alg_skip_on_mode.py
    Load a LRM, SIN, and SAR L1b file
    run Algorthm.process() on each
    test that it identifies the file as LRM, or SIN, and returns (True,'')
    or (False,'SKIP_OK..') for SAR
    """

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
    shared_dict["instr_mode"] = "LRM"
    success, error_str = thisalg.process(l1b, shared_dict, log, 0)

    assert success, f"Algorithm.process failed due to {error_str}"

    # -------------------------------------------------------------------------
    # Test with SIN file. Should return (True,'') and insert "SIN" in
    #                     shared_dict["instr_mode"]

    l1b_file = glob.glob(f"{base_dir}/testdata/cs2/l1bfiles/*SIN*.nc")[0]
    try:
        l1b = Dataset(l1b_file)
        log.info("Opened %s", l1b_file)
    except IOError:
        assert False, f"{l1b_file} could not be read"

    # Run  Algorithm.process()
    shared_dict = {}
    shared_dict["instr_mode"] = "SIN"

    success, error_str = thisalg.process(l1b, shared_dict, log, 0)

    assert success, f"Algorithm.process failed due to {error_str}"

    # -------------------------------------------------------------------------
    # Test with a SAR file. Should skip this file, returning False,'SKIP_OK ...'

    l1b_file = glob.glob(f"{base_dir}/testdata/cs2/l1bfiles/*SAR*.nc")[0]
    try:
        l1b = Dataset(l1b_file)
        log.info("Opened %s", l1b_file)
    except IOError:
        assert False, f"{l1b_file} could not be read"

    # Run  Algorithm.process()
    shared_dict = {}
    shared_dict["instr_mode"] = "SAR"

    success, error_str = thisalg.process(l1b, shared_dict, log, 0)
    assert "SKIP_OK" in error_str, "SKIP_OK should be included in error_str"
    assert success is False, f"Algorithm.process should fail {error_str}"
