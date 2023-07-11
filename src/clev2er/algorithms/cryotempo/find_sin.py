"""find_sin module
"""
import glob
import logging

log = logging.getLogger(__name__)


class FileFinder:
    """Class to find a list of SIN L1b files to process"""

    def __init__(self):
        self.months = []
        self.years = []
        self.base_path = "/raid6/cpdata/SATS/RA/CRY/L1B"
        self.l1b_type = "SIN"
        self.baselines = "DE"

    def add_month_specifier(self, month: int) -> None:
        """Add to list of month numbers to load

        Args:
            month (int): month number
        """
        self.months.append(month)

    def add_year_specifier(self, year: int) -> None:
        """Add to list of year numbers to load

        Args:
            year (int): year number in YYYY
        """
        if year < 1960:
            raise ValueError("year must be > 1960")
        self.years.append(year)

    def set_base_path(self, path: str):
        """Set base path for search

        Args:
            path (str): path of base path for search
        """
        self.base_path = path

    def find_files(self):
        """Search for L1b file according to pattern

        Returns:
            (str): list of files
        """
        file_list = []

        for year in self.years:
            for month in self.months:
                search_str = (
                    f"{self.base_path}/{self.l1b_type}/{year:4d}/{month:02d}"
                    f"/CS_*SIR_{self.l1b_type}_1B_{year:4d}{month:02d}*[{self.baselines}]???.nc"
                )
                log.info(search_str)
                files = glob.glob(search_str)
                if len(files) > 0:
                    file_list.extend(files)
        return file_list
