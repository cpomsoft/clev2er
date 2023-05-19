""" Tool to run the CLEV2ER LI+IW chain

    Setup requires: PYTHONPATH to include $CLEV2ER_BASE_DIR/src

        export CLEV2ER_BASE_DIR=/Users/alanmuir/software/clev2er
        export PYTHONPATH=$PYTHONPATH:$CLEV2ER_BASE_DIR/src

"""

import argparse
import glob
import importlib
import logging
import os
import sys
import time
import types
from logging.handlers import QueueHandler
from multiprocessing import Process, Queue, current_process
from typing import Optional, Type

from envyaml import (  # for parsing YAML files which include environment variables
    EnvYAML,
)
from netCDF4 import Dataset  # pylint: disable=E0611

from clev2er.utils.logging import get_logger

# too-many-locals, pylint: disable=R0914
# too-many-branches, pylint: disable=R0912
# too-many-statements, pylint: disable=R0915
# too-many-arguments, pylint: disable=R0913


def exception_hook(
    exc_type: Type[BaseException],
    exc_value: BaseException,
    exc_traceback: Optional[types.TracebackType],
) -> None:
    """
    log Exception traceback output to the error log, instead of just to the console
    Without this, these error can get missed when the console is not checked
    """
    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


# Set the excepthook to our custom function that logs exceptions to the error log
sys.excepthook = exception_hook


def run_chain_on_single_file(
    l1b_file: str,
    alg_object_list,
    config: dict,
    log: logging.Logger,
    log_queue: Queue,
    rval_queue: Queue,
) -> tuple[bool, str]:
    """Runs the algorithm chain on a single L1b file

    Args:
        l1b_file (str): path of L1b file to process
        alg_object_list (_type_): list of Algorithm objects
        log (logging.Logger): logging instance to use
        log_queue (Queue): Queue for multi-processing logging
        rval_queue (Queue) : Queue for multi-processing results

    Returns:
        Tuple(bool,str): algorithms success (True) or Failure (False), '' or error string
        for multi-processing return values are instead queued -> rval_queue for this process
    """

    # Setup logging either for multi-processing or standard (single process)
    if config["chain"]["use_multi-processing"]:
        # create a logger
        logger = logging.getLogger("mp")
        # add a handler that uses the shared queue
        logger.addHandler(QueueHandler(log_queue))
        # log all messages, debug and up
        logger.setLevel(logging.DEBUG)
        # get the current process
        process = current_process()
        # report initial message
        logger.debug("Child %s starting.", process.name)
        thislog = logger
    else:
        thislog = log

    thislog.debug("_" * 79)  # add a divider line in the log

    thislog.info("Processing %s", l1b_file)

    try:
        nc = Dataset(l1b_file)
    except IOError:
        error_str = f"Could not read netCDF file {l1b_file}"
        thislog.error(error_str)
        if config["chain"]["use_multi-processing"]:
            rval_queue.put((False, error_str))
        return (False, error_str)

    # ------------------------------------------------------------------------
    # Run each algorithms .process() function in order
    # ------------------------------------------------------------------------

    working_dict = {}

    for alg_obj in alg_object_list:
        success, error_str = alg_obj.process(nc, working_dict)
        if not success:
            thislog.error(
                "Processing of L1b file: %s stopped because %s", l1b_file, error_str
            )
            if config["chain"]["use_multi-processing"]:
                rval_queue.put((False, error_str))
            return (False, error_str)
    nc.close()

    if config["chain"]["use_multi-processing"]:
        rval_queue.put((True, ""))
    return (True, "")


def mp_logger_process(queue, config) -> None:
    """executed in a separate process that performs logging
       used for when multi-processing only

    Args:
        queue (Queue): object created by multiprocessing.Queue()
        config (dict): main config dictionary for log file paths
    """
    # create a logger
    logger = logging.getLogger("mp")
    log_format = "[%(levelname)-2s] : %(asctime)s : %(name)-12s :  %(message)s"
    log_formatter = logging.Formatter(log_format, datefmt="%d/%m/%Y %H:%M:%S")

    # only includes ERROR level messages
    file_handler_error = logging.FileHandler(
        config["log_files"]["errors"] + ".mp", mode="w"
    )
    file_handler_error.setFormatter(log_formatter)
    file_handler_error.setLevel(logging.ERROR)
    logger.addHandler(file_handler_error)

    # include all allowed log levels up to INFO (ie ERROR, WARNING, INFO, not DEBUG)
    file_handler_info = logging.FileHandler(
        config["log_files"]["info"] + ".mp", mode="w"
    )
    file_handler_info.setFormatter(log_formatter)
    file_handler_info.setLevel(logging.INFO)
    logger.addHandler(file_handler_info)

    # include all allowed log levels up to DEBUG
    file_handler_debug = logging.FileHandler(
        config["log_files"]["debug"] + ".mp", mode="w"
    )
    file_handler_debug.setFormatter(log_formatter)
    file_handler_debug.setLevel(logging.DEBUG)
    logger.addHandler(file_handler_debug)

    # Stream handler disabled for multi-processing as it causes intermixed log messages
    # configure a stream handler
    # logger.addHandler(logging.StreamHandler())
    # log all messages, debug and up
    # logger.setLevel(logging.DEBUG)

    # run forever
    while True:
        # consume a log message, block until one arrives
        message = queue.get()
        # check for shutdown
        if message is None:
            break
        # log the message
        logger.handle(message)


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
        tuple(bool,int,int) : (chain success or failure, number_of_errors,
                                  number of files processed)
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
            log.error("Could not import algorithm %s, %s", alg, exc)
            return (False, 1, 0)

    # -------------------------------------------------------------------------------------------
    #  Run algorithm chain's Algorthim.process() on each L1b file in l1b_file_list
    #    - a different method required for multi-processing or standard sequential processing
    #    - Note that choice of MP method is due to logging reliability constraints, which
    #      caused problems with simpler more modern pool.starmap methods
    # -------------------------------------------------------------------------------------------
    num_errors = 0
    num_files_processed = 0

    if config["chain"]["use_multi-processing"]:
        # With multi-processing we need to redirect logging to a stream

        # create the shared queue
        log_queue = Queue()

        # create a logger
        new_logger = logging.getLogger("mp")
        # add a handler that uses the shared queue
        new_logger.addHandler(QueueHandler(log_queue))
        # log all messages, debug and up
        new_logger.setLevel(logging.DEBUG)
        # start the logger process
        logger_p = Process(target=mp_logger_process, args=(log_queue, config))
        logger_p.start()

        # report initial message
        new_logger.info("Main process started.")

        rval_queues = [Queue() for l1b_file in l1b_file_list]

        # configure child processes
        num_procs = len(l1b_file_list)
        processes = [
            Process(
                target=run_chain_on_single_file,
                args=(
                    l1b_file_list[i],
                    alg_object_list,
                    config,
                    None,
                    log_queue,
                    rval_queues[i],
                ),
            )
            for i in range(num_procs)
        ]
        # start child processes
        for process in processes:
            process.start()
        # wait for child processes to finish

        rvals = []
        for i in range(num_procs):
            rval = rval_queues[i].get()
            rvals.append(rval)
            if not rval[0]:
                num_errors += 1
            num_files_processed += 1

        for process in processes:
            process.join()

        # shutdown the queue correctly
        log_queue.put(None)

    else:  # Normal sequential processing (when multi-processing is disabled)
        for l1b_file in l1b_file_list:
            success, _ = run_chain_on_single_file(
                l1b_file, alg_object_list, config, log, None, None
            )
            num_files_processed += 1
            if not success:
                num_errors += 1

                if config["chain"]["stop_on_error"]:
                    log.error(
                        "Chain stopped because of error processing L1b file %s",
                        l1b_file,
                    )
                    break

    # -----------------------------------------------------------------------------
    # Run each algorithms .finalize() function in order
    # -----------------------------------------------------------------------------

    log.debug("_" * 79)  # add a divider line in the log

    for alg_obj in alg_object_list:
        alg_obj.finalize()

    log.info("run_chain() completed successfully")

    # Completed successfully, so return True with no error msg
    if num_errors > 0:
        return (False, num_errors, num_files_processed)

    return (True, num_errors, num_files_processed)


def main() -> None:
    """main function for tool"""

    # ----------------------------------------------------------------------
    # Setup by getting essential package environment variables
    # ----------------------------------------------------------------------

    try:
        base_dir = os.environ["CLEV2ER_BASE_DIR"]
    except KeyError:
        sys.exit("Error: environment variable CLEV2ER_BASE_DIR not set")

    # ----------------------------------------------------------------------
    # Process Command Line Arguments for tool
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
        "--file",
        "-f",
        help=("[Optional] path of a single input L1b file"),
    )

    parser.add_argument(
        "--dir",
        "-d",
        help=("[Optional] path of a directory containing input L1b files"),
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

    parser.add_argument(
        "--debug",
        "-de",
        help=("[Optional] debug mode"),
        action="store_const",
        const=1,
    )

    # read arguments from the command line
    args = parser.parse_args()

    # -------------------------------------------------------------------------
    # Load Project's main YAML configuration file
    #   - default is $CLEV2ER_BASE_DIR/config/main_config.yml
    #   - or set by --conf <filepath>.yml
    # -------------------------------------------------------------------------

    config_file = args.conf
    if not os.path.exists(config_file):
        sys.exit(f"ERROR: config file {config_file} does not exist")

    try:
        config = EnvYAML(config_file)  # read the YML and parse environment variables
    except ValueError as exc:
        sys.exit(
            f"ERROR: config file {config_file} has invalid or unset environment variables : {exc}"
        )

    # -------------------------------------------------------------------------
    # Setup logging
    #   - default log level is INFO unless --debug command line argument is set
    #   - default log files paths for error, info, and debug are defined in the
    #     main config file
    # -------------------------------------------------------------------------

    log = get_logger(
        default_log_level=logging.DEBUG if args.debug else logging.INFO,
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
        if args.inlandwaters:
            algorithm_list_file = config["algorithm_lists"]["inland_waters"]
        else:
            algorithm_list_file = config["algorithm_lists"]["land_ice"]

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

    # Extract the algorithms list from the dictionary read from the YAML file
    try:
        algorithm_list = yml["algorithms"]
    except KeyError:
        log.error(
            "ERROR: algorithm list file %s has missing key: algorithms",
            algorithm_list_file,
        )
        sys.exit(1)

    # --------------------------------------------------------------------
    # Choose the input L1b file list
    # --------------------------------------------------------------------

    if args.file:
        l1b_file_list = [args.file]
    elif args.dir:
        l1b_file_list = glob.glob(args.dir + "/*.nc")
    else:  # use a test file in the list
        l1b_test_file = (
            "/cpdata/SATS/RA/CRY/L1B/SIN/2020/08/"
            "CS_OFFL_SIR_SIN_1B_20200831T200752_20200831T200913_D001.nc"
        )

        l1b_file_list = [l1b_test_file]

    # --------------------------------------------------------------------
    # Run the chain on the file list
    # --------------------------------------------------------------------

    if config["chain"]["stop_on_error"]:
        log.warning("**Chain configured to stop on first error**")

    start_time = time.time()

    success, number_errors, num_files_processed = run_chain(
        l1b_file_list, config, algorithm_list, log
    )

    elapsed_time = time.time() - start_time

    if success:
        log.info(
            "Chain successfully completed processing %d files of %d input files in %f seconds",
            num_files_processed,
            len(l1b_file_list),
            elapsed_time,
        )
    else:
        log.info(
            "Chain completed with %d errors processing %d files of %d input files in %f seconds",
            number_errors,
            num_files_processed,
            len(l1b_file_list),
            elapsed_time,
        )


if __name__ == "__main__":
    main()
