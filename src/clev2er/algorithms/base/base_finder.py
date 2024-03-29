""" clev2er.algorithms.base.base_finder"""

import logging

module_log = logging.getLogger(__name__)


class BaseFinder:
    """Base class to find a list of L1b files

    Raises: FileNotFoundError : if base_path is not a valid directory
    """

    def __init__(self, log: logging.Logger | None = None, config: dict | None = None):
        """class initialization function"""
        self.months: list[int] = []
        self.years: list[int] = []
        self.baselines = ""
        if not config:
            self.config: dict = {}
        else:
            self.config = config

        if log is not None:
            self.log = log
        else:
            self.log = module_log

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

    def find_files(self, flat_search=False) -> list[str]:
        """Search for L1b file according to pattern

        Args:
            flat_search (bool) : if True only search in self.base_path, else use pattern
        Returns:
            (str): list of files

        """
        if flat_search:
            self.log.info("flat search being used")

        file_list: list[str] = []

        return file_list
