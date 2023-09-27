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

    # log messages -> stdout
    if not silent:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(log_formatter)
        stream_handler.setLevel(default_log_level)
        log.addHandler(stream_handler)

    # Add a handler to send messages down to INFO level
    # to the log file path : log_file_info
    # will include messages to: INFO, WARNING, ERROR, and CRITICAL
    file_handler_info = logging.FileHandler(log_file_info, mode="w")
    file_handler_info.setFormatter(log_formatter)
    file_handler_info.setLevel(logging.INFO)
    log.addHandler(file_handler_info)

    # Add a handler to send messages down to ERROR level
    # to the log file path : log_file_error
    # will include messages for levels: ERROR, and CRITICAL
    file_handler_error = logging.FileHandler(log_file_error, mode="w")
    file_handler_error.setFormatter(log_formatter)
    file_handler_error.setLevel(logging.ERROR)
    log.addHandler(file_handler_error)

    if default_log_level == logging.DEBUG:
        # Add a handler to send messages down to DEBUG level
        # to the log file path : log_file_error
        # will include messages for levels: DEBUG, INFO, WARNING, ERROR, and CRITICAL
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
