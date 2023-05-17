""" Tool to run the CLEV2ER LI+IW chain
"""

import importlib
import logging
from os import environ

import yaml
from netCDF4 import Dataset  # pylint: disable=E0611

from clev2er.utils.logging import get_logger

# too-many-locals, pylint: disable=R0914


def exception_hook(exc_type, exc_value, exc_traceback):
    """
    log Exception traceback output to the error log, instead of just to the console
    Without this, these error can get missed when the console is not checked
    """
    log = logging.getLogger("")
    log.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


def main():
    """main function for tool"""

    # -------------------------------------------------------------------------
    # Set the Log Level for the tool
    # -------------------------------------------------------------------------
    log = get_logger(
        default_log_level=logging.INFO,
        log_file_error="/tmp/error.log",
        log_file_info="/tmp/info.log",
        log_file_debug="/tmp/debug.log",
    )

    # -------------------------------------------------------------------------
    # Load Project Environment Variables
    #     -  export CLEV2ER_CONFIG_DIR=/Users/alanmuir/software/clev2er/config
    # -------------------------------------------------------------------------

    config_dir = environ["CLEV2ER_CONFIG_DIR"]

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
    with open(f"{config_dir}/algorithm_list.yml", "r", encoding="utf-8") as file:
        yml = yaml.safe_load(file)
    algorithm_list = yml["algorithms"]

    # -------------------------------------------------------------------------------------------
    # Load the dynamic algorithm modules from clev2er/algorithms/<algorithm_name>.py
    #   - runs each algorithm object's __init__() function
    # -------------------------------------------------------------------------------------------
    alg_object_list = []

    for alg in algorithm_list:
        try:
            module = importlib.import_module(f"clev2er.algorithms.{alg}")
            alg_obj = module.Algorithm(config)
            alg_object_list.append(alg_obj)

        except ImportError as exc:
            assert False, f"Could not import algorithm {alg}, {exc}"

    # -------------------------------------------------------------------------------------------
    # Run each algorithms .process() function in order
    # ------------------------------------------------------------------------------------------

    working_dict = {}

    for alg_obj in alg_object_list:
        success, error_str = alg_obj.process(nc, working_dict)
        if not success:
            log.warning("Chain stopped because %s", {error_str})
            break

    # -------------------------------------------------------------------------------------------
    # Run each algorithms .finalize() function in order
    # ------------------------------------------------------------------------------------------

    for alg_obj in alg_object_list:
        alg_obj.finalize()

    # Show the contents of the working_dict
    print("working_dict=", working_dict)

    nc.close()


if __name__ == "__main__":
    main()
