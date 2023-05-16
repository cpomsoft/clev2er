""" Tool to run the CLEV2ER LI+IW chain
"""

import importlib
import logging
from os import environ

import yaml
from netCDF4 import Dataset  # pylint: disable=E0611

# too-many-locals, pylint: disable=R0914
# too-many-arguments, pylint:  disable=R0913


def get_logger(
    log_format="[%(levelname)-2s] : %(asctime)s : %(name)-12s :  %(message)s",
    log_name="",
    log_file_info="info.log",
    log_file_error="err.log",
    log_file_debug="debug.log",
    default_log_level=logging.INFO,
):
    """
    Setup Logging handlers
    - direct log.ERROR messages -> separate log file
    - direct log.INFO (including log.ERROR, log.WARNING) -> separate log file
    - direct log.DEBUG (including log.ERROR, log.WARNING, log.INFO) -> separate log file
    - direct all allowed levels to stout
    - set maximum allowed log level (applies to all outputs, default is log.INFO,
    - ie no log.DEBUG messages will be included by default)
    """

    log = logging.getLogger(log_name)
    log_formatter = logging.Formatter(log_format, datefmt="%d/%m/%Y %H:%M:%S")

    # log messages -> stdout (include all depending on log.setLevel(), at end of function)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)
    stream_handler.setLevel(logging.DEBUG)
    log.addHandler(stream_handler)

    # include all allowed log levels up to INFO (ie ERROR, WARNING, INFO, not DEBUG)
    file_handler_info = logging.FileHandler(log_file_info, mode="w")
    file_handler_info.setFormatter(log_formatter)
    file_handler_info.setLevel(logging.INFO)
    log.addHandler(file_handler_info)

    # only includes ERROR level messages
    file_handler_error = logging.FileHandler(log_file_error, mode="w")
    file_handler_error.setFormatter(log_formatter)
    file_handler_error.setLevel(logging.ERROR)
    log.addHandler(file_handler_error)

    # include all allowed log levels up to DEBUG
    file_handler_debug = logging.FileHandler(log_file_debug, mode="w")
    file_handler_debug.setFormatter(log_formatter)
    file_handler_debug.setLevel(logging.DEBUG)
    log.addHandler(file_handler_debug)
    print("log file (DEBUG):", log_file_debug)

    # set the allowed log level
    #   - logging.DEBUG will allow all levels (DEBUG, INFO, WARNING, ERROR)
    #   - logging.INFO will allow all levels (INFO, WARNING, ERROR)
    #   - logging.WARNING will allow all levels (WARNING, ERROR)
    #   - logging.ERROR will allow all levels (ERROR)

    log.setLevel(default_log_level)

    print("log file (INFO) :", log_file_info)
    print("log file (ERROR):", log_file_error)

    return log


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
    log = get_logger(default_log_level=logging.INFO)

    # -------------------------------------------------------------------------
    # Load Project Environment Variables
    #     -  export CLEV2ER_config_dir=/Users/alanmuir/software/clev2er/config
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
        success, error_str = alg_obj.process(nc, working_dict)
        if not success:
            log.warning("Chain stopped because %s", {error_str})
            break

    # Run each Algorithm's finalize function

    for alg_obj in alg_object_list:
        alg_obj.finalize()

    # Show the contents of the working_dict
    print("working_dict=", working_dict)

    nc.close()


if __name__ == "__main__":
    main()
