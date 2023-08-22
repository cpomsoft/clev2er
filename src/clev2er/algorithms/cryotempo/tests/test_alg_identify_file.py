"""pytest of algorithm
   clev2er.algorithms.cryotempo.alg_identify_file.py
"""
import glob
import logging
import os
from typing import Any, Dict

from envyaml import (  # for parsing YAML files which include environment variables
    EnvYAML,
)
from netCDF4 import Dataset  # pylint: disable=E0611

from clev2er.algorithms.cryotempo.alg_identify_file import Algorithm

log = logging.getLogger(__name__)


def test_alg_identify_file() -> None:
    """test of Algorithm in clev2er.algorithms.cryotempo.alg_identify_file.py
    Load a LRM, SIN, and SAR L1b file
    run Algorthm.process() on each
    test that it identifies the file as LRM, or SIN, and returns (True,'')
    or (False,'SKIP_OK..') for SAR
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

    # Set to Sequential Processing
    config["chain"]["use_multi_processing"] = False

    # Initialise the Algorithm
    try:
        thisalg = Algorithm(
            config=config, process_number=0, alg_log=log
        )  # no config used for this alg
    except KeyError as exc:
        assert False, f"Could not initialize algorithm {exc}"

    # -------------------------------------------------------------------------
    # Test with LRM file. Should return (True,'')

    l1b_file = glob.glob(f"{base_dir}/testdata/cs2/l1bfiles/*LRM*.nc")[0]
    try:
        l1b = Dataset(l1b_file)
        log.info("Opened %s", l1b_file)
    except IOError:
        assert False, f"{l1b_file} could not be read"

    # Run  Algorithm.process()
    shared_dict: Dict[str, Any] = {}
    success, error_str = thisalg.process(l1b, shared_dict, 0)

    assert success, f"Algorithm.process failed due to {error_str}"
    assert "num_20hz_records" in shared_dict, "num_20hz_records not in shared_dict"
    assert "instr_mode" in shared_dict, "instr_mode not in shared_dict"
    assert shared_dict["instr_mode"] == "LRM"
