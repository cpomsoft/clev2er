""" pytests """


import importlib
import logging
import yaml
from netCDF4 import Dataset  # pylint: disable=E0611

log = logging.getLogger(__name__)


def test_with_l1bfile():
    """test running an algorithm chain with a single l1b file as
    input
    """
    config = {"project": "CLEV2ER"}  # config dict passed to every algorithm

    l1b_file = (
        "/cpdata/SATS/RA/CRY/L1B/SIN/2020/08/"
        "CS_OFFL_SIR_SIN_1B_20200831T200752_20200831T200913_D001.nc"
    )

    try:
        nc = Dataset(l1b_file)
    except IOError:
        assert False, f"Could not read netCDF file {l1b_file}"

    # ds = xr.open_dataset(l1b_file)

    # -------------------------------------------------------------------------------------------
    # Read the list of algorithms to use
    # -------------------------------------------------------------------------------------------
    with open("config/algorithm_list.yml", "r", encoding="utf-8") as file:
        yml = yaml.safe_load(file)
    algorithm_list = yml["algorithms"]

    # Load the dynamic algorithm modules from clev2er/algorithms/<algorithm_name>.py

    alg_object_list = []

    for alg in algorithm_list:
        try:
            module = importlib.import_module(f"clev2er.algorithms.{alg}")
            alg_obj = module.Algorithm(config)
            alg_object_list.append(alg_obj)

        except ImportError as exc:
            assert False, f"Could not import algorithm {alg}, {exc}"

    # Run the modules algorithms in order

    working_dict = {}

    for alg_obj in alg_object_list:
        reject, reason = alg_obj.process(nc, working_dict)
        if reject:
            log.warning("Chain stopped because %s", {reason})
            break

    # Run each Algorithm's finalize function

    for alg_obj in alg_object_list:
        alg_obj.finalize()

    # Show the contents of the working_dict
    print("working_dict=", working_dict)

    nc.close()
