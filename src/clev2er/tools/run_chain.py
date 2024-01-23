#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" Main command line run control tool for CLEV2ER algorithm framework chains

    Setup requires:
        
        Set CLEV2ER_BASE_DIR to point to the base directory of the CLEV2ER framework
            export CLEV2ER_BASE_DIR=/Users/alanmuir/software/clev2er

        PYTHONPATH to include $CLEV2ER_BASE_DIR/src
            export PYTHONPATH=$PYTHONPATH:$CLEV2ER_BASE_DIR/src

    Example usage:
        To list all command line options:

        `python run_chain.py -h`

        b) Run the cryotempo land ice chain on a single L2b file:

        `python run_chain.py --name cryotempo -f \
        $CLEV2ER_BASE_DIR/testdata/cs2/l1bfiles/\
            CS_OFFL_SIR_LRM_1B_20200930T235609_20200930T235758_D001.nc`

        a) Run the cryotempo land ice chain on all l1b files in 
           $CLEV2ER_BASE_DIR/testdata/cs2/l1bfiles

        `python run_chain.py --name cryotempo --dir $CLEV2ER_BASE_DIR/testdata/cs2/l1bfiles`

         Run with multi-processing and shared memory enabled (also can set these in main config):

        `python run_chain.py --name cryotempo -d $CLEV2ER_BASE_DIR/testdata/cs2/l1bfiles -sm -mp`
        
"""

import argparse
import glob
import importlib
import logging
import multiprocessing as mp
import os
import re
import sys
import time
import traceback
import types
from logging.handlers import QueueHandler
from math import ceil
from multiprocessing import Process, Queue, current_process
from typing import Any, List, Optional, Type

import numpy as np
from codetiming import Timer
from netCDF4 import Dataset  # pylint: disable=E0611

from clev2er.utils.breakpoints.breakpoint_files import write_breakpoint_file
from clev2er.utils.config.load_config_settings import (
    load_algorithm_list,
    load_config_files,
)
from clev2er.utils.logging_funcs import get_logger

# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements
# pylint: disable=too-many-arguments
# pylint: disable=too-many-nested-blocks
# pylint: disable=too-many-lines
# pylint: disable=R0801


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


def custom_key(line):
    """search function to find N in line containing [fN]

    Args:
        line (str): string containing [fN], where N is an int which may be large

    Returns:
        N or 0 if not matched
    """
    match = re.search(r"\[f(\d+)\]", line)
    if match:
        return int(match.group(1))
    return 0


def sort_file_by_number(filename: str) -> None:
    """sort log file by N , where log lines contain the string [fN]

    Args:
        filename (str): log file path
    """
    with open(filename, "r", encoding="utf8") as file:
        lines = file.readlines()

    sorted_lines = sorted(lines, key=custom_key)

    with open(filename, "w", encoding="utf8") as file:
        file.writelines(sorted_lines)


def insert_txtfile1_in_txtfile2_after_line_containing_string(
    file1: str, file2: str, target_string: str
) -> None:
    """Inserts txtfile1 in txtfile2 after line containing target_string

    Args:
        file1 (str): path of txt file1
        file2 (str): path of txt file2
        target_string (str): string to search for in file2 and insert contents of file1 after
    """
    with open(file1, "r", encoding="utf-8") as fd1:
        content1 = fd1.read()

    with open(file2, "r", encoding="utf-8") as fd2:
        lines = fd2.readlines()

    new_lines = []
    for line in lines:
        new_lines.append(line)
        if target_string in line:
            new_lines.append(content1)

    with open(file2, "w", encoding="utf-8") as fd2:
        fd2.writelines(new_lines)


def append_file(file1_path: str, file2_path: str) -> None:
    """appends contents of file1_path to end of  file2_path

    Args:
        file1_path (str): txt file to append
        file2_path (str): txt file to append to end of
    """
    with open(file1_path, "r", encoding="utf-8") as file1:
        with open(file2_path, "a", encoding="utf-8") as file2:
            file2.write(file1.read())


def remove_strings_from_file(filename: str) -> None:
    """removes any string [fN] from the txt file

        where N is any integer

    Args:
        filename (str): file name
    """
    # Open the input file in read mode
    with open(filename, "r", encoding="utf-8") as file:
        # Read all the lines from the file
        lines = file.readlines()

    # Create a regular expression pattern to match strings of the form '[fN]'
    pattern = r"\[f\d+\]"

    # Remove the matched strings from each line
    modified_lines = [re.sub(pattern, "", line) for line in lines]

    # Open the modified file in write mode
    with open(filename, "w", encoding="utf-8") as file:
        # Write the modified lines to the file
        file.writelines(modified_lines)


def run_chain_on_single_file(
    l1b_file: str,
    alg_object_list: list[Any],
    config: dict,
    log: logging.Logger,
    log_queue: Optional[Queue],
    rval_queue: Optional[Queue],
    filenum: int,
    breakpoint_alg_name: str = "",
) -> tuple[bool, str, str]:
    """Runs the algorithm chain on a single L1b file.

       This function is run in a separate process if multi-processing is enabled.

    Args:
        l1b_file (str): path of L1b file to process
        alg_object_list (list[Algorithm]): list of Algorithm objects
        log (logging.Logger): logging instance to use
        log_queue (Queue): Queue for multi-processing logging
        rval_queue (Queue) : Queue for multi-processing results
        filenum (int) : file number being processed
        breakpoint_alg_name (str) : if not '', name of algorithm to break after.

    Returns:
        Tuple(bool,str,str):
        : algorithms success (True) or Failure (False),
        : '' or error string
        : path of breakpoint file or ''
        for multi-processing return values are instead queued -> rval_queue for this process
    """

    bp_filename = ""  # break point file path

    # Setup logging either for multi-processing or standard (single process)
    if config["chain"]["use_multi_processing"]:
        # create a logger
        logger = logging.getLogger("mp")
        # add a handler that uses the shared queue
        if log_queue is not None:
            handler = QueueHandler(log_queue)
            handler.setFormatter(logging.Formatter(f"[f{filenum}] %(message)s"))
            logger.addHandler(handler)
        # log all messages, debug and up
        logger.setLevel(logging.DEBUG)
        # get the current process
        process = current_process()
        # report initial message
        logger.debug("[f%d] Child %s starting.", filenum, process.name)
        thislog = logger
    else:
        thislog = log

    thislog.info("_%s", "_" * 79)  # add a divider line in the log

    thislog.info("Processing file %d: %s", filenum, l1b_file)

    try:  # and open the NetCDF file
        with Dataset(l1b_file) as nc:
            # ------------------------------------------------------------------------
            # Run each algorithms .process() function in order
            # ------------------------------------------------------------------------

            shared_dict = {"l1b_file_name": l1b_file}

            for alg_obj in alg_object_list:
                alg_obj.set_filenum(filenum)
                alg_obj.set_log(thislog)
                # Run the Algorithm's process() function. Note that for multi-processing
                # the process() function also calls the init() function first

                success, error_str = alg_obj.process(nc, shared_dict)
                if not success:
                    if "SKIP_OK" in error_str:
                        thislog.debug(
                            "Processing of L1b file %d : %s SKIPPED because %s",
                            filenum,
                            l1b_file,
                            error_str,
                        )
                    else:
                        thislog.error(
                            "Processing of L1b file %d : %s stopped because %s",
                            filenum,
                            l1b_file,
                            error_str,
                        )

                    if config["chain"]["use_multi_processing"]:
                        if rval_queue is not None:
                            rval_queue.put((False, error_str, Timer.timers))
                        # Free up resources by running the Algorithm.finalize() on each
                        # algorithm instance
                        for alg_obj in alg_object_list:
                            if alg_obj.initialized:
                                alg_obj.finalize(stage=5)
                    return (False, error_str, bp_filename)

                if alg_obj.alg_name.rsplit(".", maxsplit=1)[-1] == breakpoint_alg_name:
                    thislog.debug("breakpoint reached at algorithm %s", alg_obj.alg_name)
                    bp_filename = write_breakpoint_file(
                        config, shared_dict, thislog, breakpoint_alg_name
                    )
                    break

            if config["chain"]["use_multi_processing"]:
                # Free up resources by running the Algorithm.finalize() on each
                # algorithm instance
                for alg_obj in alg_object_list:
                    if alg_obj.initialized:
                        alg_obj.finalize(stage=6)

    except (IOError, ValueError, KeyError):
        error_str = f"Error processing {l1b_file}: {traceback.format_exc()}"
        thislog.error(error_str)
        if config["chain"]["use_multi_processing"]:
            if rval_queue is not None:
                rval_queue.put((False, error_str, Timer.timers))  # pass the function return values
                # back to the parent process
                # via a queue
        return (False, error_str, bp_filename)

    if config["chain"]["use_multi_processing"]:
        if rval_queue is not None:
            rval_queue.put((True, "", Timer.timers))
    return (True, "", bp_filename)


def mp_logger_process(queue, config) -> None:
    """executed in a separate process that performs logging
       used for when multi-processing only

    Args:
        queue (Queue): object created by multiprocessing.Queue()
        config (dict): main config dictionary for log file paths
    """
    # create a logger
    logger = logging.getLogger("mp")
    if config["log_files"]["debug_mode"]:
        log_format = "[%(levelname)-2s] : %(asctime)s : %(name)-12s :  %(message)s"
    else:
        log_format = "[%(levelname)-2s] : %(asctime)s :  %(message)s"

    log_formatter = logging.Formatter(log_format, datefmt="%d/%m/%Y %H:%M:%S")

    # only includes ERROR level messages
    file_handler_error = logging.FileHandler(config["log_files"]["errors"] + ".mp", mode="w")
    file_handler_error.setFormatter(log_formatter)
    file_handler_error.setLevel(logging.ERROR)
    logger.addHandler(file_handler_error)

    # include all allowed log levels up to INFO (ie ERROR, WARNING, INFO, not DEBUG)
    file_handler_info = logging.FileHandler(config["log_files"]["info"] + ".mp", mode="w")
    file_handler_info.setFormatter(log_formatter)
    file_handler_info.setLevel(logging.INFO)
    logger.addHandler(file_handler_info)

    # include all allowed log levels up to DEBUG
    if config["log_files"]["debug_mode"]:
        file_handler_debug = logging.FileHandler(config["log_files"]["debug"] + ".mp", mode="w")
        file_handler_debug.setFormatter(log_formatter)
        file_handler_debug.setLevel(logging.DEBUG)
        logger.addHandler(file_handler_debug)

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
    breakpoint_alg_name: str = "",
) -> tuple[bool, int, int, int, str]:
    """Run the algorithm chain in algorithm_list on each L1b file in l1b_file_list
       using the configuration settings in config

    Args:
        l1b_file_list (list[str]): list of l1b files paths to process
        config (dict): configuration dictionary. This is the named chain config and the
                                                 main config merged
        algorithm_list (list[str]): list of algorithm names
        log (logging.Logger): log instance to use
        breakpoint_alg_name (str): name of algorithm to set break point after.
                                   Default='' (no breakpoint set here)

    Returns:
        tuple(bool,int,int, int,str) : (chain success or failure, number_of_errors,
                                  number of files processed, number of files skipped
                                  (for valid reasons), breakpoint filename)
    """

    n_files = len(l1b_file_list)
    breakpoint_filename = ""

    # -------------------------------------------------------------------------------------------
    # Load the dynamic algorithm modules from clev2er/algorithms/<algorithm_name>.py
    #   - runs each algorithm object's __init__() function
    # -------------------------------------------------------------------------------------------
    alg_object_list = []
    shared_mem_alg_object_list: List[Any] = []
    # duplicate list used to call initialization
    # of shared memory resources where used.

    log.info("Dynamically importing and initializing algorithms from list...")

    for alg in algorithm_list:
        # --------------------------------------------------------------------
        # Dynamically import each Algorithm from the list
        # --------------------------------------------------------------------
        try:
            module = importlib.import_module(
                f"clev2er.algorithms.{config['chain']['chain_name']}.{alg}"
            )
        except ImportError as exc:
            log.error("Could not import algorithm %s, %s", alg, exc)
            return (False, 1, 0, 0, breakpoint_filename)

        # --------------------------------------------------------------------
        # Create an instance of each Algorithm,
        #   - runs its __init__(config) function
        # --------------------------------------------------------------------

        # Load/Initialize algorithm
        try:
            alg_obj = module.Algorithm(config, log)
        except (FileNotFoundError, IOError, KeyError, ValueError):
            log.error("Could not initialize algorithm %s, %s", alg, traceback.format_exc())
            return (False, 1, 0, 0, breakpoint_filename)

        alg_object_list.append(alg_obj)

        # --------------------------------------------------------------------
        # Create a second instance of each Algorithm for multi-processing
        # shared memory buffer allocations,
        #   - runs its __init__(config) function
        # Note that the .process() function is never run for this instance
        # We merge  {"_init_shared_mem": True} to the config so that the
        # Algorithm knows to run any shared memory initialization
        # --------------------------------------------------------------------

        if config["chain"]["use_multi_processing"] and config["chain"]["use_shared_memory"]:
            # Load/Initialize algorithm
            try:
                alg_obj_shm = module.Algorithm(config | {"_init_shared_mem": True}, log)
            except (FileNotFoundError, IOError, KeyError, ValueError):
                log.error(
                    "Could not initialize algorithm for shared_memory %s, %s",
                    alg,
                    traceback.format_exc(),
                )
                # If there is a failure we must clean up any shared memory already allocated
                for alg_obj_shm in shared_mem_alg_object_list:
                    if alg_obj_shm.initialized:
                        alg_obj_shm.finalize(stage=4)

                return (False, 1, 0, 0, breakpoint_filename)

            shared_mem_alg_object_list.append(alg_obj_shm)

        # If a breakpoint after this alg is set we don't need to initialize any more algorithms
        if alg == breakpoint_alg_name:
            log.debug("breakpoint reached in import for %s", alg)
            break
    # -------------------------------------------------------------------------------------------
    #  Run algorithm chain's Algorthim.process() on each L1b file in l1b_file_list
    #    - a different method required for multi-processing or standard sequential processing
    #    - Note that choice of MP method is due to logging reliability constraints, which
    #      caused problems with simpler more modern pool.starmap methods
    # -------------------------------------------------------------------------------------------
    num_errors = 0
    num_files_processed = 0
    num_skipped = 0

    # --------------------------------------------------------------------------------------------
    # Parallel Processing (optional)
    # --------------------------------------------------------------------------------------------
    if config["chain"]["use_multi_processing"]:  # pylint: disable=R1702
        # With multi-processing we need to redirect logging to a stream

        # create a shared logging queue for multiple processes to use
        log_queue: Queue = Queue()

        # create a logger
        new_logger = logging.getLogger("mp")
        # add a handler that uses the shared queue
        new_logger.addHandler(QueueHandler(log_queue))
        # log all messages, debug and up
        new_logger.setLevel(log.level)
        # start the logger process
        logger_p = Process(target=mp_logger_process, args=(log_queue, config))
        logger_p.start()

        # Divide up the input files in to chunks equal to maximum number of processes
        # allowed == config["chain"]["max_processes_for_multiprocessing"]

        log.info(
            "Using multi-processing with max %d processes",
            config["chain"]["max_processes_for_multiprocessing"],
        )

        num_chunks = ceil(n_files / config["chain"]["max_processes_for_multiprocessing"])

        file_indices_chunks = np.array_split(list(range(n_files)), num_chunks)

        for chunk_num, file_indices in enumerate(file_indices_chunks):
            chunked_l1b_file_list = np.array(l1b_file_list)[file_indices]
            log.debug(f"mp chunk_num {chunk_num}: chunked_l1b_file_list={chunked_l1b_file_list}")

            num_procs = len(chunked_l1b_file_list)

            log.info(
                "Running process set %d of %d (containing %d processes)",
                chunk_num + 1,
                num_chunks,
                num_procs,
            )

            # Create separate queue for each new process to handle function return values
            rval_queues: List[Queue] = [Queue() for _ in range(num_procs)]

            # configure child processes
            processes = [
                Process(
                    target=run_chain_on_single_file,
                    args=(
                        chunked_l1b_file_list[i],
                        alg_object_list,
                        config,
                        None,
                        log_queue,
                        rval_queues[i],
                        file_indices[i],
                        breakpoint_alg_name,
                    ),
                )
                for i in range(num_procs)
            ]
            # start child processes
            for process in processes:
                process.start()

            # wait for child processes to finish
            for i, process in enumerate(processes):
                process.join()
                # retrieve return values of each process function from queue
                # rval=(bool, str, Timer.timers)
                while not rval_queues[i].empty():
                    rval = rval_queues[i].get()
                    if not rval[0] and "SKIP_OK" not in rval[1]:
                        num_errors += 1
                    if "SKIP_OK" in rval[1]:
                        num_skipped += 1
                    num_files_processed += 1
                    # rval[2] returns the Timer.timers dict for algorithms process() function
                    # ie a dict containing timers['alg_name']= the number of seconds elapsed
                    for key, value in rval[2].items():
                        if key in Timer.timers:
                            Timer.timers.add(key, value)
                        else:
                            Timer.timers.add(key, value)

        # shutdown the queue correctly
        log_queue.put(None)

        log.info("MP processing completed with outputs logged:")
    # --------------------------------------------------------------------------------------------
    # Sequential Processing
    # --------------------------------------------------------------------------------------------
    else:  # Normal sequential processing (when multi-processing is disabled)
        try:
            for fnum, l1b_file in enumerate(l1b_file_list):
                log.info("\n%sProcessing file %d of %d%s", "-" * 20, fnum, n_files, "-" * 20)
                success, error_str, breakpoint_filename = run_chain_on_single_file(
                    l1b_file,
                    alg_object_list,
                    config,
                    log,
                    None,
                    None,
                    fnum,
                    breakpoint_alg_name,
                )
                num_files_processed += 1
                if not success and "SKIP_OK" in error_str:
                    log.debug("Skipping file")
                    num_skipped += 1
                    continue
                if not success:
                    num_errors += 1

                    if config["chain"]["stop_on_error"]:
                        log.error(
                            "Chain stopped because of error processing L1b file %s",
                            l1b_file,
                        )
                        break

                    log.error(
                        "Error processing L1b file %s, skipping file",
                        l1b_file,
                    )
                    continue
        except KeyboardInterrupt as exc:
            log.error("KeyboardInterrupt detected", exc)

    # -----------------------------------------------------------------------------
    # Run each algorithms .finalize() function in order
    # -----------------------------------------------------------------------------

    log.debug("_" * 79)  # add a divider line in the log

    for alg_obj_shm in shared_mem_alg_object_list:
        if alg_obj_shm.initialized:
            alg_obj_shm.finalize(stage=2)

    for alg_obj in alg_object_list:
        if alg_obj.initialized:
            alg_obj.finalize(stage=3)

    # Elapsed time for each algorithm.
    # Note if multi-processing, process times are added for each algorithm
    # (so total time processing will be less)
    #  - ie for processes p1 and p2,
    #  -    alg1.time =(p1.alg1.time +p2.alg1.time +,..)
    #  -    alg2.time =(p1.alg2.time +p2.alg2.time +,..)

    log.info("\n%sAlgorithm Cumulative Processing Time%s", "-" * 20, "-" * 20)

    for algname, cumulative_time in Timer.timers.items():
        log.info("%s %.3f s", algname, cumulative_time)

    if num_errors > 0:
        return (False, num_errors, num_files_processed, num_skipped, breakpoint_filename)

    # Completed successfully, so return True with no error msg
    return (True, num_errors, num_files_processed, num_skipped, breakpoint_filename)


def main() -> None:
    """main function for tool"""

    # ----------------------------------------------------------------------
    # Process Command Line Arguments for tool
    # ----------------------------------------------------------------------

    # initiate the command line parser
    parser = argparse.ArgumentParser()

    # add each argument

    parser.add_argument(
        "--name",
        "-n",
        help=(
            "name (str) : chain name. Should contain no spaces or special chars other than _. "
            "Algorithm modules for this chain are located in "
            "${CLEV2ER_BASE_DIR}/src/algorithms/<name>.\n"
            "Actual algorithms used for the chain and their order are chosen in "
            "a separate algorithm list (see --alglist)"
        ),
        required=True,
    )

    parser.add_argument(
        "--alglist",
        "-a",
        help=(
            "[Optional] path of algorithm list YML file,"
            "default is an empty str which will result in a search for highest version list "
            "files in ${CLEV2ER_BASE_DIR}/config/algorithm_lists/<chain_name>_<B><VVV>.[yml,xml] "
            "where <B> is the uppercase baseline character A..Z, and <VVV> is the zero padded "
            "version number, ie 001"
        ),
        default="",
    )

    parser.add_argument(
        "--mconf",
        "-mc",
        help=(
            "[Optional] path of main controller configuration file (XML format),"
            "default=$CLEV2ER_BASE_DIR/config/main_config.xml"
        ),
        default="",  # empty string results in use of $CLEV2ER_BASE_DIR/config/main_config.xml
    )

    parser.add_argument(
        "--conf",
        "-c",
        help=(
            "[Optional] path of chain controller configuration file (XML format),"
            "default=$CLEV2ER_BASE_DIR/config/chain_configs/<chain_name>_<BVVV>.yml"
        ),
        default="",  # empty string results in use of highest available chain <BVVV>
    )

    parser.add_argument(
        "--conf_opts",
        "-co",
        help=(
            "[Optional] Comma separated list of config options to add/modify the  "
            "configuration dictionary passed to algorithms and finder classes. "
            "Each option can include a value. The value is appended to the option key after a : "
            "Use key:true, or key:false, or key:value. If no value is included with a single level "
            "key, it indicates a boolean true. "
            "For multi-level keys, use another colon, ie key1:key2:value. "
            "Example: -co sin_only:true  or -co sin_only are both the same to only select SIN L1b "
            "files. "
            "These are chain specific and may have different meanings for other chains. "
            "Note that these options override any identical key:values in chain configuration files"
        ),
        type=str,
    )

    parser.add_argument(
        "--baseline",
        "-b",
        help=(
            "[Optional] baseline of chain. Single uppercase char. ie A-Z "
            "Used to partly specify the chain config file and algorithm list to use, "
            "along with version and chain name. These files are named <chain_name>_<B><VVVV>.yml, "
            "where <B> is the baseline character. "
            "If not specified on the command line, the controller will search for the highest "
            "baseline config file available (ie if config files for baseline A and B "
            "exist, baseline B config file will be selected)"
        ),
        type=str,
        default="",  # when an empty str is used, the highest baseline found is used
    )
    parser.add_argument(
        "--version",
        "-v",
        help=(
            "[Optional] version of chain. integer 1-100, (do not zero pad), default=1 . "
            "Used to partly specify the chain config file and algorithm list to use, "
            "along with version and chain name. These files are named <chain_name>_<B><VVVV>.yml, "
            "where <VVV> is the automatically zero padded version number. "
        ),
        type=int,
        default=0,  # when 0 is used, the highest version number found for the baseline is used
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
        "--cs2testdir",
        "-ct",
        help=(
            "[Optional] for quick CS2 tests, uses default CS2 L1b directory: "
            "$CLEV2ER_BASE_DIR/testdata/cs2/l1bfiles"
        ),
        action="store_const",
        const=1,
    )

    parser.add_argument(
        "--month",
        "-m",
        help=(
            "[Optional] month number (1,12) to use to select L1b files. "
            "The month number is used by the chain's finder algorithms if "
            "they support month selections"
        ),
        type=int,
    )
    parser.add_argument(
        "--year",
        "-y",
        help=(
            "[Optional] year number (YYYY) to use to select L1b files. "
            "The year number is used by the chain's finder algorithms if "
            "they support year selections"
        ),
        type=int,
    )

    parser.add_argument(
        "--max_files",
        "-mf",
        help=("[Optional] limit number of input files to this number"),
        type=int,
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
        help=(
            "[Optional] debug mode. log.DEBUG messages are output to the debug log file, "
            "configured in the main config file. By default log.DEBUG messages are not output."
        ),
        action="store_const",
        const=1,
    )

    parser.add_argument(
        "--multiprocessing",
        "-mp",
        help=(
            "[Optional] use multi-processing, overrides main config file use_multi_processing "
            "setting to true"
        ),
        action="store_const",
        const=1,
    )

    parser.add_argument(
        "--nprocs",
        "-np",
        help=(
            "[Optional] maximum number of cores to split multi-processing on. "
            "Overrides setting in main config file"
        ),
        type=int,
    )

    parser.add_argument(
        "--sequentialprocessing",
        "-sp",
        help=(
            "[Optional] use sequential (standard) processing, overrides main config file "
            "use_multi_processing setting to false"
        ),
        action="store_const",
        const=1,
    )

    parser.add_argument(
        "--sharedmem",
        "-sm",
        help=("[Optional] use shared memory when multi-processing is enabled"),
        action="store_const",
        const=1,
    )

    parser.add_argument(
        "--stop_on_error",
        "-st",
        help=("[Optional] stop chain on first error. Default is set in main config file"),
        action="store_const",
        const=1,
    )

    parser.add_argument(
        "--logstring",
        "-ls",
        help=(
            "[Optional] append this string to log file names for this run, as "
            "<logfilename>_<this_string>.log"
        ),
        type=str,
    )

    parser.add_argument(
        "--breakpoint_after",
        "-bp",
        help=("[Optional, str] algorithm_name : set a breakpoint after the named algorithm "),
        type=str,
    )

    # read arguments from the command line
    args = parser.parse_args()

    if not args.name:
        sys.exit("ERROR: missing command line argument --name <chain_name>")

    if args.baseline:
        if len(args.baseline) != 1 or not args.baseline.isalpha():
            sys.exit("ERROR: --baseline <BASELINE>, must be a single char A..Z")

    if args.version:
        if args.version > 100:
            sys.exit("ERROR: --version <version>, must be an integer 1..100")

    # -------------------------------------------------------------------------
    # Load main XML controller configuration file
    #   - default is $CLEV2ER_BASE_DIR/config/main_config.xml
    #   - or set by --conf <filepath>.xml
    # -------------------------------------------------------------------------

    try:
        config, baseline, version, config_file, chain_config_file = load_config_files(
            args.name,
            baseline=args.baseline,
            version=args.version,
            main_config_file=args.mconf,
            chain_config_file=args.conf,
        )
    except (KeyError, OSError, ValueError):
        sys.exit(f"Loading config file error: {traceback.format_exc()}")

    if args.baseline:
        if config["baseline"] != args.baseline:
            sys.exit(
                f"Error: baseline key:value parameter in chain config file {chain_config_file} "
                f"is {config['baseline']} which does not match --baseline {args.baseline}"
            )

    if args.version:
        if config["version"] != args.version:
            sys.exit(
                f"Error: version key:value parameter in chain config file {chain_config_file} "
                f"is {config['version']} which does not match --version {args.version}"
            )

    # -------------------------------------------------------------------------
    # Modify  config settings from command line args and store modifications
    # to report later
    # -------------------------------------------------------------------------

    modified_args = []

    if args.baseline:
        modified_args.append(f"baseline={args.baseline}")
    if args.version > 0:
        modified_args.append(f"version={args.version}")
        version = args.version
    if args.breakpoint_after:
        modified_args.append(f"breakpoint_after={args.breakpoint_after}")
    if args.quiet:
        modified_args.append("quiet=True")
    if args.debug:
        modified_args.append("debug=True")
        config["log_files"]["debug_mode"] = True
    else:
        config["log_files"]["debug_mode"] = False
    if args.max_files:
        modified_args.append(f"max_files={args.max_files}")
    if args.alglist:
        modified_args.append(f"alglist={args.alglist}")
    if args.conf:
        modified_args.append(f"conf={args.conf}")
    if args.logstring:
        modified_args.append(f"logstring={args.logstring}")
    if args.multiprocessing:
        config["chain"]["use_multi_processing"] = True
        modified_args.append("use_multi_processing=True")
    if args.sequentialprocessing:
        config["chain"]["use_multi_processing"] = False
        modified_args.append("use_multi_processing=False")
    if args.sharedmem:
        if config["chain"]["use_multi_processing"]:
            config["chain"]["use_shared_memory"] = True
            modified_args.append("use_shared_memory=True")
        else:
            sys.exit(
                "ERROR: --sharedmem option must be used  with multi-processing enabled"
                "\nEither through the --multiprocessing command line option, or"
                "\nthrough the chain:use_multi_processing setting in the main config file"
            )
    if args.nprocs:
        config["chain"]["max_processes_for_multiprocessing"] = args.nprocs
        modified_args.append(f"max_processes_for_multiprocessing={args.nprocs}")

    config["chain"]["chain_name"] = args.name

    if args.stop_on_error:
        config["chain"]["stop_on_error"] = True
        modified_args.append("stop_on_error=True")

    # Process command line arg 'conf_opts' to modify config dict
    # these a comma separated with : to separate levels
    #
    if args.conf_opts:
        keyvals = args.conf_opts.split(",")
        for keyval in keyvals:
            if ":" not in keyval:  # single level, without value == True
                config[keyval] = True
                modified_args.append(f"{keyval}=True")
            else:
                mkeyvals = keyval.split(":")
                val = mkeyvals[-1]
                if val == "false":
                    val = False
                elif val == "true":
                    val = True
                elif val.isdigit():
                    val = int(val)
                else:
                    try:
                        val = float(val)
                    except ValueError:
                        pass
                if len(mkeyvals) == 2:
                    config[mkeyvals[0]] = val
                    modified_args.append(f"{mkeyvals[0]}={val}")
                elif len(mkeyvals) == 3:
                    if mkeyvals[0] not in config:
                        config[mkeyvals[0]] = {}
                    config[mkeyvals[0]][mkeyvals[1]] = val
                    modified_args.append(f"{mkeyvals[0]}:{mkeyvals[1]}={val}")

    # -------------------------------------------------------------------------
    # Check we have enough input command line args
    # -------------------------------------------------------------------------

    if not args.cs2testdir and not args.file and not args.dir and not args.year and not args.month:
        sys.exit(
            f"usage error: No inputs specified for the {args.name} chain. Must have either "
            "\n--cs2testdir (-ct),"
            "\n--file (-f) <single L1b file as input>,"
            "\n--dir (-d) <input all L1b files in this directory>, or "
            "\n--year (-y) <YYYY> and --month (-m) <M> : search for files for "
            "specified year and month."
            "\nThe options --year, --month are used as inputs to l1b_file_selectors modules "
            f"\nspecified in the {args.name} chain algorithms list and l1b_base_dir "
            f"\nfrom the {args.name } config file."
        )

    # -------------------------------------------------------------------------
    # Setup logging
    #   - default log level is INFO unless --debug command line argument is set
    #   - default log files paths for error, info, and debug are defined in the
    #     main config file
    # -------------------------------------------------------------------------

    # Test that log file settings are in the config dict

    if "log_files" not in config:
        sys.exit(f"log_files section missing from chain configuration file {chain_config_file}")

    if "errors" not in config["log_files"]:
        sys.exit(f"log_files:errors section missing from chain config file {chain_config_file}")
    if "info" not in config["log_files"]:
        sys.exit(f"log_files:info section missing from chain config file {chain_config_file}")
    if "debug" not in config["log_files"]:
        sys.exit(f"log_files:debug section missing from chain config file {chain_config_file}")
    if "append_year_month_to_logname" not in config["log_files"]:
        sys.exit(
            "log_files:append_year_month_to_logname section missing from chain config file "
            f"{chain_config_file}"
        )

    log_file_error_name = config["log_files"]["errors"]
    log_file_info_name = config["log_files"]["info"]
    log_file_debug_name = config["log_files"]["debug"]

    # Add a string before .log if args.logstring is set
    if args.logstring:
        log_file_error_name = log_file_error_name.replace(".log", f"_{args.logstring}.log")
        log_file_info_name = log_file_info_name.replace(".log", f"_{args.logstring}.log")
        log_file_debug_name = log_file_debug_name.replace(".log", f"_{args.logstring}.log")

    # Add _YYYY or _MMYYYY before .log if config["log_files"]["append_year_month_to_logname"]
    # is set
    if config["log_files"]["append_year_month_to_logname"]:
        if args.year and not args.month:
            log_file_error_name = log_file_error_name.replace(".log", f"_{args.year}.log")
            log_file_info_name = log_file_info_name.replace(".log", f"_{args.year}.log")
            log_file_debug_name = log_file_debug_name.replace(".log", f"_{args.year}.log")
        if args.year and args.month:
            log_file_error_name = log_file_error_name.replace(
                ".log", f"_{args.month:02d}{args.year}.log"
            )
            log_file_info_name = log_file_info_name.replace(
                ".log", f"_{args.month:02d}{args.year}.log"
            )
            log_file_debug_name = log_file_debug_name.replace(
                ".log", f"_{args.month:02d}{args.year}.log"
            )

    config["log_files"]["errors"] = log_file_error_name
    config["log_files"]["info"] = log_file_info_name
    config["log_files"]["debug"] = log_file_debug_name

    log = get_logger(
        default_log_level=logging.DEBUG if args.debug else logging.INFO,
        log_file_error=log_file_error_name,
        log_file_info=log_file_info_name,
        log_file_debug=log_file_debug_name,
        log_name="run_chain",
        silent=args.quiet,
    )

    log.info("error log: %s", log_file_error_name)
    log.info("info log: %s", log_file_info_name)
    if args.debug:
        log.info("debug log: %s", log_file_debug_name)

    log.info(
        "Chain name: %s : baseline %s, version %03d",
        args.name,
        baseline,
        version,
    )

    # -------------------------------------------------------------------------------------------
    # Read the list of algorithms to use for this chain
    # -------------------------------------------------------------------------------------------

    log.info("chain config used: %s", chain_config_file)

    try:
        (
            algorithm_list,
            finder_list,
            alg_list_file,
            breakpoint_alg_name,
        ) = load_algorithm_list(
            args.name,
            baseline=baseline,
            version=version,
            alg_list_file=args.alglist,
            log=log,
        )
    except (KeyError, OSError, ValueError):
        log.error("Loading algorithm list file failed : %s", traceback.format_exc())
        sys.exit(1)

    if args.breakpoint_after:
        breakpoint_alg_name = args.breakpoint_after

    if breakpoint_alg_name:
        log.info("breakpoint set after algorithm %s", breakpoint_alg_name)

    if config["chain"]["use_multi_processing"]:
        # change the default method of multi-processing for Linux from
        # fork to spawn
        mp.set_start_method("spawn")

    # -------------------------------------------------------------------------------------------
    #  Select input L1b files
    #   - single file : args.file
    #   - multiple files : args.dir
    # -------------------------------------------------------------------------------------------

    if args.cs2testdir:
        l1b_file_list = glob.glob(f"{os.environ['CLEV2ER_BASE_DIR']}/testdata/cs2/l1bfiles/*")
    elif args.file:
        l1b_file_list = [args.file]
    elif args.dir:
        l1b_file_list = glob.glob(args.dir + "/*.nc")
    else:
        # Extract the optional file choosers
        l1b_file_list = []

        l1b_file_selector_modules = finder_list

        if len(l1b_file_selector_modules) > 0:
            for file_selector_module in l1b_file_selector_modules:
                # Import module
                try:
                    module = importlib.import_module(
                        f"clev2er.algorithms.{config['chain']['chain_name']}.{file_selector_module}"
                    )
                except ImportError as exc:
                    log.error("Could not import module %s, %s", file_selector_module, exc)
                    sys.exit(1)

                try:
                    finder = module.FileFinder(log=log, config=config)
                    if args.month and args.year:
                        finder.add_month(args.month)
                        finder.add_year(args.year)
                    if args.year and args.month is None:
                        finder.add_year(args.year)
                        for month in range(1, 13):
                            finder.add_month(month)

                    files = finder.find_files()
                    if len(files) > 0:
                        l1b_file_list.extend(files)
                except (KeyError, ValueError, FileNotFoundError) as exc:
                    log.error("file finder error: %s", exc)
                    sys.exit(1)

    if args.max_files:
        if len(l1b_file_list) > args.max_files:
            l1b_file_list = l1b_file_list[: args.max_files]

    n_l1b_files = len(l1b_file_list)

    # ----------------------------------------------------------------------------------------
    # Check that the L1b file list contains at least 1 readable file
    # ----------------------------------------------------------------------------------------

    num_files_readable = 0
    for l1b_file in l1b_file_list:
        if os.path.isfile(l1b_file):
            num_files_readable += 1
            break
    if num_files_readable == 0:
        log.error("No input files in list exist, please check L1b input directories and files")
        sys.exit(1)

    log.info("Total number of L1b file found:  %d", n_l1b_files)
    if args.conf_opts:
        log.info("additional config options from command line are: %s", args.conf_opts)

    # Check if we have any L1b files to process
    if n_l1b_files < 1:
        log.error("No L1b files selected..")
        sys.exit(1)

    # --------------------------------------------------------------------
    # Run the chain on the file list
    # --------------------------------------------------------------------

    if config["chain"]["stop_on_error"]:
        log.warning("**Chain configured to stop on first error**")

    start_time = time.time()

    if args.breakpoint_after:
        if args.breakpoint_after not in algorithm_list:
            log.error(
                "breakpoint algorithm %s not in algorithm list (check the name is correct)",
                args.breakpoint_after,
            )
            sys.exit(1)

    _, number_errors, num_files_processed, num_skipped, breakpoint_filename = run_chain(
        l1b_file_list, config, algorithm_list, log, args.breakpoint_after
    )

    elapsed_time = time.time() - start_time

    # --------------------------------------------------------------------
    # Log chain summary stats
    # --------------------------------------------------------------------

    log.info("\n%sChain Run Summary          %s", "-" * 20, "-" * 20)

    log.info(
        "%s chain completed in %.2f seconds := (%.2f mins := %.2f hours)",
        args.name,
        elapsed_time,
        elapsed_time / 60.0,
        (elapsed_time / 60.0) / 60.0,
    )
    log.info(
        "%s chain processed %d L1b files of %d. %d files skipped, %d errors",
        args.name,
        num_files_processed,
        len(l1b_file_list),
        num_skipped,
        number_errors,
    )

    log.info("\n%sLog Files          %s", "-" * 20, "-" * 20)

    log.info("log file (INFO): %s", config["log_files"]["info"])
    log.info("log file (ERRORS): %s", config["log_files"]["errors"])
    if args.debug:
        log.info("log file (DEBUG): %s", config["log_files"]["debug"])

    if config["chain"]["use_multi_processing"]:
        # sort .mp log files by filenum processed (as they will be jumbled)
        log.info("Sorting multi-processing error log file...")
        sort_file_by_number(config["log_files"]["errors"] + ".mp")
        log.info("Sorting multi-processing info log file...")
        sort_file_by_number(config["log_files"]["info"] + ".mp")
        if args.debug:
            log.info("Sorting multi-processing debug log file...")
            sort_file_by_number(config["log_files"]["debug"] + ".mp")

        log.info("merging log files...")
        # put .mp log contents into main log file
        insert_txtfile1_in_txtfile2_after_line_containing_string(
            config["log_files"]["info"] + ".mp",
            config["log_files"]["info"],
            "MP processing completed with outputs logged:",
        )
        if args.debug:
            insert_txtfile1_in_txtfile2_after_line_containing_string(
                config["log_files"]["debug"] + ".mp",
                config["log_files"]["debug"],
                "MP processing completed with outputs logged:",
            )
        append_file(config["log_files"]["errors"] + ".mp", config["log_files"]["errors"])

        # remove all the .mp temporary log files
        for file_path in [
            config["log_files"]["errors"] + ".mp",
            config["log_files"]["info"] + ".mp",
            config["log_files"]["debug"] + ".mp",
        ]:
            try:
                # Check if the file exists
                if os.path.exists(file_path):
                    # Delete the file
                    os.remove(file_path)
            except OSError as exc:
                log.error("Error occurred while deleting the file %s : %s", file_path, exc)
    else:
        # remove the multi-processing marker string '[fN]' from log files
        remove_strings_from_file(config["log_files"]["info"])
        remove_strings_from_file(config["log_files"]["errors"])
        if args.debug:
            remove_strings_from_file(config["log_files"]["debug"])

    log.info("\n%sConfig Files          %s", "-" * 20, "-" * 20)
    log.info("Run config: %s", config_file)
    log.info("Chain config: %s", chain_config_file)
    log.info("Algorithm list file: %s", alg_list_file)

    if len(modified_args) > 0:
        for mod_args in modified_args:
            log.info("cmdline overide: %s", mod_args)
    if len(breakpoint_filename) > 0:
        log.info("breakpoint file name: %s", breakpoint_filename)


if __name__ == "__main__":
    main()
