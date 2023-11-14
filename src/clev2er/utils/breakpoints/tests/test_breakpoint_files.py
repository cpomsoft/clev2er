"""pytest tests of clev2er.utils.breakpoints
"""

import numpy as np

from clev2er.utils.breakpoints.breakpoint_files import write_breakpoint_file


def test_breakpoint_files():
    """pytest function for write_breakpoint_file()"""
    config = {}  # to be used to pass def dir & filenames
    # when this feature implemented.

    # Create a dict that contains all possible data types
    # we expect to support, and include:
    # * multiple levels.
    # * variables with equal dimensions
    shared_dict = {
        "single_bool": True,
        "bool_list": [True, False],
        "single_int": 1,
        "int_list": [1, 2, 3],
        "single_str": "test string",
        "np_list_int": np.array([1, 2, 3]),
        "level2": {
            "single_bool": True,
            "bool_list": [True, False],
            "single_int": 1,
            "int_list": [1, 2, 3],
            "single_str": "test string",
            "np_list_int": np.array([1, 2, 3]),
        },
    }

    write_breakpoint_file(config, shared_dict)
