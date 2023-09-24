"""pytest of algorithm
   clev2er.algorithms.cryotempo.alg_surface_type.py
"""
import logging
import os
import string

import xmltodict  # for parsing xml to python dict
from envyaml import (  # for parsing YAML files which include environment variables
    EnvYAML,
)
from netCDF4 import Dataset  # pylint: disable=E0611

from clev2er.algorithms.cryotempo.alg_surface_type import Algorithm
from clev2er.utils.xml.xml_funcs import set_xml_dict_types

# pylint: disable=too-many-locals
# pylint: disable=too-many-statements

log = logging.getLogger(__name__)


def test_alg_skip_on_area_bounds() -> None:
    """test of Algorithm in clev2er.algorithms.cryotempo.alg_surface_type.py"""

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

    # Load cryotempo chain config file by finding latest baseline
    # ie baseline B before A
    reverse_alphabet_list = list(string.ascii_uppercase[::-1])
    baseline = None
    for _baseline in reverse_alphabet_list:
        config_file = f"{base_dir}/config/chain_configs/cryotempo_{_baseline}001.yml"
        if os.path.exists(config_file):
            baseline = _baseline
            break
    assert baseline, "No cryotempo baseline config file found"

    log.info("Using config file %s", config_file)

    try:
        chain_config = EnvYAML(
            config_file
        )  # read the YML and parse environment variables
    except ValueError as exc:
        assert (
            False
        ), f"ERROR: config file {config_file} has invalid or unset environment variables : {exc}"

    # merge the two config files (with precedence to the chain_config)
    config = config | chain_config.export()  # the export() converts to a dict

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
    shared_dict["lons_nadir"] = (
        l1b["lon_20_ku"][:].data % 360.0
    )  # [-180,+180E] -> 0..360E

    # This should fail, as file is outside cryosphere
    success, error_str = thisalg.process(l1b, shared_dict)

    assert (
        success is False
    ), "Algorithm.process should fail as file is outside cryosphere"
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
    shared_dict["lons_nadir"] = (
        l1b["lon_20_ku"][:].data % 360.0
    )  # [-180,+180E] -> 0..360E

    # This should succeed,
    success, error_str = thisalg.process(l1b, shared_dict)

    assert success, "Algorithm.process should succeed"
