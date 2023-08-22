""" clev2er.algorithms.templates.alg_filter_height"""

import logging
from typing import Any, Dict, Tuple

import numpy as np
from codetiming import Timer  # used to time the Algorithm.process() function
from netCDF4 import Dataset  # pylint:disable=E0611

# -------------------------------------------------

# pylint config
# Similar lines in 2 files, pylint: disable=R0801
# Too many return statements, pylint: disable=R0911

log = logging.getLogger(__name__)


class Algorithm:
    """**Algorithm to filter height**.

    - filter on maximum diff to ref dem

    **Contribution to shared dictionary**

        - shared_dict['height_filt'] : (type), filtered height
    """

    def __init__(
        self, config: Dict[str, Any], process_number: int, alg_log: logging.Logger
    ) -> None:
        """
        Args:
            config (dict): configuration dictionary
            process_number (int): process number used for this algorithm (0..max_processes)
                                  similar but not the same as the os pid (process id)
                                  for sequential processing this would be 0 (default)
            alg_log (logging.Logger) : log instance to use for logging within algorithm

        Returns:
            None
        """
        self.alg_name = __name__
        self.config = config
        self.procnum = process_number
        self.log = alg_log

        _, _ = self.init()

    def init(self) -> Tuple[bool, str]:
        """Algorithm initialization template

        Returns:
            (bool,str) : success or failure, error string

        Raises:
            KeyError : keys not in config
            FileNotFoundError :
            OSError :

        Note: raise and Exception rather than just returning False
        Logging: use self.log.info,error,debug(your_message)
        """
        self.log.debug("Initializing algorithm %s", self.alg_name)

        # -----------------------------------------------------------------
        #  \/ Place Algorithm initialization steps here \/
        # -----------------------------------------------------------------

        return (True, "")

    @Timer(name=__name__, text="", logger=None)
    def process(
        self, l1b: Dataset, shared_dict: dict, filenum: int
    ) -> Tuple[bool, str]:
        """Algorithm main processing function

        Args:
            l1b (Dataset): input l1b file dataset (constant)
            shared_dict (dict): shared_dict data passed between algorithms
            filenum (int) : file number of list of L1b files

        Returns:
            Tuple : (success (bool), failure_reason (str))
            ie
            (False,'error string'), or (True,'')

        **IMPORTANT NOTE:**

        Logging within this function must use on of:
            self.log.info(your_message)
            self.log.debug(your_message)
            self.log.error(your_message)
        """

        self.log.info(
            "Processing algorithm %s for file %d",
            self.alg_name.rsplit(".", maxsplit=1)[-1],
            filenum,
        )

        # Test that input l1b is a Dataset type

        if not isinstance(l1b, Dataset):
            self.log.error("l1b parameter is not a netCDF4 Dataset type")
            return (False, "l1b parameter is not a netCDF4 Dataset type")

        # -------------------------------------------------------------------
        # Perform the algorithm processing, store results that need to be passed
        # \/    down the chain in the 'shared_dict' dict     \/
        # -------------------------------------------------------------------

        if "height_20_ku" not in shared_dict:
            self.log.error("height_20_ku is not in shared_dict")
            return (False, "height_20_ku is not in shared_dict")

        if "dem_elevation_values" not in shared_dict:
            self.log.error("dem_elevation_values is not in shared_dict")
            return (False, "dem_elevation_values is not in shared_dict")

        if "height_filters" not in self.config:
            self.log.error("height_filters not in config")
            return (False, "height_filters not in config")

        # Test if config contains required height filters
        height_filters = [
            "max_diff_to_ref_dem",
            "min_elevation_antarctica",
            "max_elevation_antarctica",
            "min_elevation_greenland",
            "max_elevation_greenland",
        ]
        for height_filter in height_filters:
            if height_filter not in self.config["height_filters"]:
                self.log.error("height_filters.%s not in config", height_filter)
                return (False, f"height_filters.{height_filter} not in config")

        shared_dict["height_filt"] = shared_dict["height_20_ku"].copy()

        # -------------------------------------------------------------------------
        # Set elevation to nan where it differs from reference DEM by more than Nm
        # --------------------------------------------------------------------------

        max_diff = self.config["height_filters"]["max_diff_to_ref_dem"]

        elevation_outliers = np.where(
            np.abs(shared_dict["height_20_ku"] - shared_dict["dem_elevation_values"])
            > max_diff
        )[0]
        if elevation_outliers.size > 0:
            shared_dict["height_filt"][elevation_outliers] = np.nan
            self.log.info(
                "Number of elevation outliers > |50m| from DEM : %d",
                elevation_outliers.size,
            )

        # ----------------------------------------------------------------------------
        # Set elevation to nan where it < or > min/max allowed elevation
        # ----------------------------------------------------------------------------

        if shared_dict["hemisphere"] == "south":
            max_elevation = self.config["height_filters"]["max_elevation_antarctica"]
            min_elevation = self.config["height_filters"]["min_elevation_antarctica"]
        else:
            max_elevation = self.config["height_filters"]["max_elevation_greenland"]
            min_elevation = self.config["height_filters"]["min_elevation_greenland"]

        elevation_outliers = np.where(
            (shared_dict["height_20_ku"] > max_elevation)
            | (shared_dict["height_20_ku"] < min_elevation)
        )[0]
        if elevation_outliers.size > 0:
            shared_dict["height_filt"][elevation_outliers] = np.nan
            self.log.info(
                "Number of elevation values outside allowed range %.2f %.2f: %d",
                min_elevation,
                max_elevation,
                elevation_outliers.size,
            )

        # Return success (True,'')
        return (True, "")

    def finalize(self, stage: int = 0):
        """Perform final clean up actions for algorithm

        Args:
            stage (int, optional): Can be set to track at what stage the
            finalize() function was called
        """

        self.log.debug("Finalize algorithm %s called at stage %d", self.alg_name, stage)

        # --------------------------------------------------------
        # \/ Add algorithm finalization here \/
        # --------------------------------------------------------

        # --------------------------------------------------------
