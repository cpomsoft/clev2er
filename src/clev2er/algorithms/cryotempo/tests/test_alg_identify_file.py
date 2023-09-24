"""pytest of algorithm
   clev2er.algorithms.cryotempo.alg_identify_file.py
"""
import glob
import logging
import os
from typing import Any, Dict

import xmltodict  # for parsing xml to python dict
from netCDF4 import Dataset  # pylint: disable=E0611

from clev2er.algorithms.cryotempo.alg_identify_file import Algorithm
from clev2er.utils.xml.xml_funcs import set_xml_dict_types

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

    config_file = f"{base_dir}/config/main_config.xml"
    assert os.path.exists(config_file), f"config file {config_file} does not exist"

    with open(config_file, "r", encoding="utf-8") as file:
        config_xml = file.read()

    # Use xmltodict to parse and convert
    # the XML document
    try:
        config = dict(xmltodict.parse(config_xml))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        assert False, f"ERROR: config file {config_file} xml format error : {exc}"

    # Convert all str values to correct types: bool, int, float, str
    set_xml_dict_types(config)

    # Set to Sequential Processing
    config["chain"]["use_multi_processing"] = False

    # Initialise the Algorithm
    try:
        thisalg = Algorithm(config, log)  # no config used for this alg
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
    success, error_str = thisalg.process(l1b, shared_dict)

    assert success, f"Algorithm.process failed due to {error_str}"
    assert "num_20hz_records" in shared_dict, "num_20hz_records not in shared_dict"
    assert "instr_mode" in shared_dict, "instr_mode not in shared_dict"
    assert shared_dict["instr_mode"] == "LRM"
