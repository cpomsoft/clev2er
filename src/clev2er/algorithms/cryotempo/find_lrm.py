"""find_lrm module
"""
import glob
import logging
import os
import sys
from typing import List

log = logging.getLogger(__name__)

# pylint: disable=R0801
# pylint: disable=too-many-instance-attributes


class FileFinder:
    """Class to find a list of LRM L1b files to process in one or more
       specified months, from

    <base_path>/LRM/<YYYY>/<MM>/CS_*SIR_*.nc

    #Usage if using the default base_path: /raid6/cpdata/SATS/RA/CRY/L1B

    finder=FileFinder()
    finder.add_month(1)
    finder.add_month(2)
    finder.add_year(2020)
    files=finder.find_files()

    ##Options

    finder.set_base_path(path)

    Raises: FileNotFoundError : if base_path is not a valid directory
    """

    def __init__(self, thislog: logging.Logger | None = None):
        """class initialization function"""
        self.months: List[int] = []
        self.years: List[int] = []
        self.base_path = "/raid6/cpdata/SATS/RA/CRY/L1B"
        self.l1b_type = "LRM"
        self.baselines = "E"
        self.sin_only = False
        self.lrm_only = False
        if thislog is not None:
            self.log = thislog
        else:
            self.log = log

    def set_option(self, option_str: str):
        """set options

        Args:
            option_str (str): an option str w
        """
        if option_str == "sin_only":
            self.sin_only = True
        if option_str == "lrm_only":
            self.lrm_only = True

    def add_month(self, month: int) -> None:
        """Add to list of month numbers to load

        Args:
            month (int): month number
        """
        self.months.append(month)

    def add_year(self, year: int) -> None:
        """Add to list of year numbers to load

        Args:
            year (int): year number in YYYY
        """
        if year < 1960:
            raise ValueError("year must be > 1960")
        self.years.append(year)

    def set_base_path(self, path: str) -> None:
        """Set base path for search

        Args:
            path (str): path of base path for search
        """
        self.base_path = path

        if not os.path.isdir(path):
            raise FileNotFoundError(f"{path} is not a valid directory")

    def set_baselines(self, baselines: str) -> None:
        """Set the allowed L1b baselines

        Args:
            baselines (str): string containing one or more baseline chars. ie 'D' or 'DE'
        """
        if not baselines.isupper():
            raise ValueError("baseline chars must be uppercase. ie D, or DE")
        self.baselines = baselines

    def find_files(self, flat_search=False) -> list[str]:
        """Search for L1b file according to pattern

        Args:
            flat_search (bool) : if True only search in self.base_path, else use pattern
        Returns:
            (str): list of files

        """
        file_list: List[str] = []

        if self.sin_only:
            return file_list

        if len(self.years) < 1:
            sys.exit("usage error: --year must be specified on command line")

        if len(self.months) == 0:
            self.months = list(range(1, 13))

        for year in self.years:
            self.log.info("Finding files for year: %d", year)
            for month in self.months:
                self.log.info("Finding files for month: %d", month)
                if flat_search:
                    search_str = (
                        f"{self.base_path}"
                        f"/CS_*SIR_{self.l1b_type}_1B_{year:4d}{month:02d}*[{self.baselines}]???.nc"
                    )
                else:
                    search_str = (
                        f"{self.base_path}/{self.l1b_type}/{year:4d}/{month:02d}"
                        f"/CS_*SIR_{self.l1b_type}_1B_{year:4d}{month:02d}*[{self.baselines}]???.nc"
                    )
                self.log.info("search string=%s", search_str)
                files = glob.glob(search_str)
                nfiles = len(files)
                if nfiles:
                    file_list.extend(files)
                self.log.info(
                    "Number of files found for %.02d/%d: %d", month, year, nfiles
                )
        self.log.info(
            "Total number of %s files found: %d", self.l1b_type, len(file_list)
        )
        return file_list
