"""pytest of algorithm
   clev2er.algorithms.cryotempo.alg_skip_on_area_bounds.py
"""
import logging
import os
from typing import Any, Dict

from envyaml import (  # for parsing YAML files which include environment variables
    EnvYAML,
)
from netCDF4 import Dataset  # pylint: disable=E0611

from clev2er.algorithms.cryotempo.alg_skip_on_area_bounds import Algorithm

# similar lines in two files, pylint: disable=R0801


log = logging.getLogger(__name__)


def test_alg_skip_on_area_bounds() -> None:
    """test of Algorithm in clev2er.algorithms.cryotempo.alg_skip_on_area_bounds.py"""

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
    shared_dict: Dict[str, Any] = {}
    # This should fail, as algorithm expects shared_dict['instr_mode'] to be present
    success, _ = thisalg.process(l1b, shared_dict)

    assert (
        success is False
    ), "Algorithm.process should fail as no shared_dict['instr_mode']"

    shared_dict["instr_mode"] = "LRM"

    # This should fail, as L1b file is located outside cryosphere
    success, _ = thisalg.process(l1b, shared_dict)

    assert success is False, "should fail as L1b file is outside cryosphere"

    l1b_file = (
        f"{base_dir}/testdata/cs2/l1bfiles/"
        "CS_OFFL_SIR_LRM_1B_20200930T235609_20200930T235758_D001.nc"
    )
    try:
        l1b = Dataset(l1b_file)
        log.info("Opened %s", l1b_file)
    except IOError:
        assert False, f"{l1b_file} could not be read"

    # This should fail, as L1b file is located outside cryosphere
    success, _ = thisalg.process(l1b, shared_dict)

    assert success, f"should pass as L1b file {l1b_file} passes over Greenland"
