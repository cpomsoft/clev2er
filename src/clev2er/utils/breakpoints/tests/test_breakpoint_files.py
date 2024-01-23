"""pytest tests of clev2er.utils.breakpoints
"""

import logging

import numpy as np

from clev2er.utils.breakpoints.breakpoint_files import write_breakpoint_file

log = logging.getLogger(__name__)


def test_breakpoint_files():
    """pytest function for write_breakpoint_file()"""
    config = {
        "breakpoint_files": {"default_dir": "/tmp/bp"},
    }  # to be used to pass def dir & filenames
    # when this feature implemented.

    # Create a dict that contains all possible data types
    # we expect to support, and include:
    # * multiple levels.
    # * variables with equal dimensions
    shared_dict = {
        "l1b_file_name": "/tnjkjl/myl1bfile.nc",
        "single_bool": True,
        "bool_list": [True, False],
        "single_int": 1,
        "single_float": -3.56743,
        "int_list": [1, 2, 3],
        "single_str": "test string",
        "np_list_int": np.array([1, 2, 3]),
        "np_list_int_2d": np.array([[1, 2, 3], [4, 5, 6]], np.int32),
        "level2": {
            "single_bool": False,
            "bool_list": [True, False],
            "single_int": 1,
            "int_list": [1, 2, 3],
            "single_str": "test string",
            "np_list_int": np.array([1, 2, 3]),
        },
    }

    write_breakpoint_file(config, shared_dict, log, "test")
