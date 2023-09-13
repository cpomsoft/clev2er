""" test_finders.py"""

import sys
from typing import List

from clev2er.algorithms.base.base_finder import BaseFinder


class FileFinder(BaseFinder):
    """class to return a list of L1b files

    Args:
        BaseFinder (BaseFinder): base finder class

    In order to find files you can optionally use the following
    which are optionally set by the run_chain.py command line parameters

    Set by command line options:
        self.months  # list of months to find
        self.years   # list of years to find
    Set by config file settings:
        config["l1b_base_dir"]

    """

    # def __init__(self, log: logging.Logger | None = None, config: dict = {}):
    #     super().__init__(log, config)

    def find_files(self, flat_search=False) -> list[str]:
        """find list of L1b files

        Args:
            flat_search (bool, optional): _description_. Defaults to False.

        Raises:
            KeyError: _description_

        Returns:
            list[str]: _description_
        """
        if "l1b_base_dir" not in self.config:
            raise KeyError("l1b_base_dir missing from config")

        l1b_base_dir = self.config["l1b_base_dir"]
        file_list: List[str] = []
        for month in self.months:
            file_list.append(f"{l1b_base_dir}/test_{month}.txt")
        return file_list


config = {}
config["l1b_base_dir"] = "/tmp"

try:
    finder = FileFinder(config=config)

    finder.add_month(7)
    finder.add_month(3)

    files = finder.find_files()
except (FileNotFoundError, ValueError, KeyError) as exc:
    print(f"error {exc}")
    sys.exit(1)

print(files)
