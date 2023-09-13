"""find_sin module
"""
import glob
import logging
import os
from typing import List

from clev2er.algorithms.base.base_finder import BaseFinder

# pylint: disable=R0801
# pylint: disable=too-many-instance-attributes

log = logging.getLogger(__name__)


class FileFinder(BaseFinder):
    """class to find a list of SIN L1b files to process in one or more
       specified months, from

    <base_path>/SIN/<YYYY>/<MM>/CS_*SIR_*.nc

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

    # The base class is initialized with:
    # def __init__(self, log: logging.Logger | None = None, config: dict = {}):

    def find_files(self, flat_search=False) -> list[str]:
        """Search for L1b file according to pattern

        Args:
            flat_search (bool) : if True only search in l1b_base_dir, else use pattern
        Returns:
            (str): list of files

        """
        file_list: List[str] = []

        self.log.info("flat_search: %d", flat_search)

        if "lrm_only" in self.config:
            return file_list

        if "l1b_baselines" not in self.config:
            raise KeyError("l1b_baselines missing from config")
        l1b_baselines = self.config[
            "l1b_baselines"
        ]  # comma separated list of l1b baseline chars, ie D,E

        if "l1b_base_dir" not in self.config:
            raise KeyError("l1b_base_dir missing from config")
        l1b_base_dir = self.config["l1b_base_dir"]

        if not os.path.isdir(l1b_base_dir):
            raise FileNotFoundError(f"{l1b_base_dir} directory not found")

        if len(self.years) < 1:
            raise ValueError("Empty year list in find_files(). Use .add_year() first")

        if len(self.months) == 0:
            self.months = list(range(1, 13))

        for year in self.years:
            self.log.info("Finding files for year: %d", year)
            for month in self.months:
                self.log.info("Finding files for month: %d", month)
                if flat_search:
                    search_str = (
                        f"{l1b_base_dir}"
                        f"/CS_*SIR_SIN_1B_{year:4d}{month:02d}*[{l1b_baselines}]???.nc"
                    )
                else:
                    search_str = (
                        f"{l1b_base_dir}/SIN/{year:4d}/{month:02d}"
                        f"/CS_*SIR_SIN_1B_{year:4d}{month:02d}*[{l1b_baselines}]???.nc"
                    )
                self.log.info("search string=%s", search_str)
                files = glob.glob(search_str)
                nfiles = len(files)
                if nfiles:
                    file_list.extend(files)
                self.log.info(
                    "Number of files found for %.02d/%d: %d", month, year, nfiles
                )
        self.log.info("Total number of SIN files found: %d", len(file_list))
        return file_list
