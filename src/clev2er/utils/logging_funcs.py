"""logging helper functions:

    get_logger() :  sets up logging system to write log.ERROR, INFO, DEBUG to separate
                    log files, and also output to stdout
"""

import logging

# pylint: disable=R0913


def get_logger(
    log_format="[%(levelname)-2s] : %(asctime)s : %(name)-12s :  %(message)s",
    log_name="",
    log_file_info="info.log",
    log_file_error="err.log",
    log_file_debug="debug.log",
    default_log_level=logging.INFO,
    silent=False,
):
    """
    Setup Logging handlers
    - direct log.ERROR messages -> separate log file
    - direct log.INFO (including log.ERROR, log.WARNING) -> separate log file
    - direct log.DEBUG (including log.ERROR, log.WARNING, log.INFO) -> separate log file
    - direct all allowed levels to stout
    - set maximum allowed log level (applies to all outputs, default is log.INFO,
    - ie no log.DEBUG messages will be included by default)

    Args:
        log_format (str) : formatting string for logger
        log_name (str) :
        log_file_info (str) : path of log file to use for INFO logs
        log_file_error (str) : path of log file to use for ERROR logs
        log_file_debug (str) : path of log file to use for DEBUG logs
        default_log_level () : default=logging.INFO
        silent (bool) : if True do not output to stdout, default=False
    Returns:
        log object
    """

    log = logging.getLogger(log_name)
    log.propagate = True
    log_formatter = logging.Formatter(log_format, datefmt="%d/%m/%Y %H:%M:%S")

    if not silent:
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

    # set the allowed log level
    #   - logging.DEBUG will allow all levels (DEBUG, INFO, WARNING, ERROR)
    #   - logging.INFO will allow all levels (INFO, WARNING, ERROR)
    #   - logging.WARNING will allow all levels (WARNING, ERROR)
    #   - logging.ERROR will allow all levels (ERROR)

    log.setLevel(default_log_level)

    return log
