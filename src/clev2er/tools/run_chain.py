""" Tool to run the CLEV2ER LI+IW chain

    Setup requires: PYTHONPATH to include $CLEV2ER_BASE_DIR/src

        export CLEV2ER_BASE_DIR=/Users/alanmuir/software/clev2er
        export PYTHONPATH=$PYTHONPATH:$CLEV2ER_BASE_DIR/src

"""

import argparse
import importlib
import logging
import os
import sys

from envyaml import (  # for parsing YAML files which include environment variables
    EnvYAML,
)
from netCDF4 import Dataset  # pylint: disable=E0611

from clev2er.utils.logging import get_logger

# too-many-locals, pylint: disable=R0914
# too-many-branches, pylint: disable=R0912
# too-many-statements, pylint: disable=R0915


def exception_hook(exc_type, exc_value, exc_traceback):
    """
    log Exception traceback output to the error log, instead of just to the console
    Without this, these error can get missed when the console is not checked
    """
    log = logging.getLogger("")
    log.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


def run_chain(
    l1b_file_list: list[str],
    config: dict,
    algorithm_list: list[str],
    log: logging.Logger,
) -> bool:
    """Run the algorithm chain on each L1b file in l1b_file_list

    Args:
        l1b_file_list (_type_): _description_
        config (_type_): _description_
        algorithm_list (_type_): _description_

    Returns:
        tuple(bool,str) : (chain_success, failure_msg)
    """

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
            return (False, f"Could not import algorithm {alg}, {exc}")

    for l1b_file in l1b_file_list:
        log.info("Processing %s", l1b_file)

        try:
            nc = Dataset(l1b_file)
        except IOError:
            log.error("Could not read netCDF file %s", l1b_file)
            continue

        # ------------------------------------------------------------------------
        # Run each algorithms .process() function in order
        # ------------------------------------------------------------------------

        working_dict = {}

        for alg_obj in alg_object_list:
            success, error_str = alg_obj.process(nc, working_dict)
            if not success:
                log.warning(
                    "Chain run for L1b file: %s stopped because %s", l1b_file, error_str
                )
                break

        nc.close()

    # -----------------------------------------------------------------------------
    # Run each algorithms .finalize() function in order
    # -----------------------------------------------------------------------------

    for alg_obj in alg_object_list:
        alg_obj.finalize()

    # Completed successfully, so return True with no error msg
    return (True, "")


def main():
    """main function for tool"""

    try:
        base_dir = os.environ["CLEV2ER_BASE_DIR"]
    except KeyError:
        sys.exit("Error: environment variable CLEV2ER_BASE_DIR not set")

    # ----------------------------------------------------------------------
    # Process Command Line Arguments
    # ----------------------------------------------------------------------

    # initiate the command line parser
    parser = argparse.ArgumentParser()

    # add each argument
    parser.add_argument(
        "--conf",
        "-c",
        help=(
            "[Optional] path of main YAML configuration file,"
            "default=$CLEV2ER_BASE_DIR/config/main_config.yml"
        ),
        default=f"{base_dir}/config/main_config.yml",
    )

    parser.add_argument(
        "--alglist",
        "-a",
        help=(
            "[Optional] path of algorithm list,"
            "default is defined in the main configuration file, and depends on "
        ),
    )

    parser.add_argument(
        "--landice",
        "-li",
        help=("[Optional] use default land ice algorithms"),
        action="store_const",
        const=1,
    )

    parser.add_argument(
        "--inlandwaters",
        "-iw",
        help=("[Optional] use default inlandwaters algorithms"),
        action="store_const",
        const=1,
    )

    parser.add_argument(
        "--quiet",
        "-q",
        help=("[Optional] do not output log messages to stdout"),
        action="store_const",
        const=1,
    )

    # read arguments from the command line
    args = parser.parse_args()

    config_file = args.conf
    if not os.path.exists(config_file):
        sys.exit(f"ERROR: config file {config_file} does not exist")

    # -------------------------------------------------------------------------
    # Load Project's main YAML configuration file
    #   - default is $CLEV2ER_BASE_DIR/config/main_config.yml
    #   - or set by --conf <filepath>.yml
    # -------------------------------------------------------------------------

    config_file = args.conf

    try:
        config = EnvYAML(config_file)  # read the YML and parse environment variables
    except ValueError as exc:
        sys.exit(
            f"ERROR: config file {config_file} has invalid or unset environment variables : {exc}"
        )
    # -------------------------------------------------------------------------
    # Set the Log Level for the tool
    # -------------------------------------------------------------------------

    log = get_logger(
        default_log_level=logging.INFO,
        log_file_error=config["log_files"]["errors"],
        log_file_info=config["log_files"]["info"],
        log_file_debug=config["log_files"]["debug"],
        silent=args.quiet,
    )

    # -------------------------------------------------------------------------------------------
    # Read the list of default algorithms to use for land ice, or inland waters
    #   - default alg list files are defined in the main config file
    #   - alternatively use a user provided list if --alglist <file.yml> is set
    # -------------------------------------------------------------------------------------------

    if args.alglist:
        algorithm_list_file = args.alglist
    else:
        if args.landice:
            algorithm_list_file = config["algorithm_lists"]["land_ice"]
        elif args.inlandwaters:
            algorithm_list_file = config["algorithm_lists"]["inland_waters"]

    log.info("Using algorithm list: %s", algorithm_list_file)

    if not os.path.exists(algorithm_list_file):
        log.error("ERROR: algorithm_lists file %s does not exist", algorithm_list_file)
        sys.exit(1)

    # Load and parse the algorithm list
    try:
        yml = EnvYAML(
            algorithm_list_file
        )  # read the YML and parse environment variables
    except ValueError as exc:
        log.error(
            "ERROR: algorithm list file %s has invalid"
            "or unset environment variables : %s",
            algorithm_list_file,
            exc,
        )
        sys.exit(1)

    try:
        algorithm_list = yml["algorithms"]
    except KeyError:
        log.error(
            "ERROR: algorithm list file %s has missing key: algorithms",
            algorithm_list_file,
        )
        sys.exit(1)

    l1b_file = (
        "/cpdata/SATS/RA/CRY/L1B/SIN/2020/08/"
        "CS_OFFL_SIR_SIN_1B_20200831T200752_20200831T200913_D001.nc"
    )

    run_chain([l1b_file], config, algorithm_list, log)


if __name__ == "__main__":
    main()
