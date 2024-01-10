""" clev2er.algorithms.templates.alg_filter_height"""

from typing import Tuple

import numpy as np
from codetiming import Timer  # used to time the Algorithm.process() function
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.algorithms.base.base_alg import BaseAlgorithm

# -------------------------------------------------

# pylint config
# Similar lines in 2 files, pylint: disable=R0801
# Too many return statements, pylint: disable=R0911
# pylint: disable=too-many-branches


class Algorithm(BaseAlgorithm):
    """filter on maximum diff to ref dem

    CLEV2ER Algorithm: inherits from BaseAlgorithm

    BaseAlgorithm __init__(config,thislog)
        Args:
            config: Dict[str, Any]: chain configuration dictionary
            thislog: logging.Logger | None: initial logger instance to use or
                                            None (use root logger)
    """

    # Note: __init__() is in BaseAlgorithm. See required parameters above
    # init() below is called by __init__() at a time dependent on whether
    # sequential or multi-processing mode is in operation

    def init(self) -> Tuple[bool, str]:
        """Algorithm initialization

        Add steps in this function that are run once at the beginning of the chain
        (for example loading a DEM or Mask)

        Returns:
            (bool,str) : success or failure, error string

        Raises:
            KeyError : keys not in config
            FileNotFoundError :
            OSError :

        Note: raise and Exception rather than just returning False
        """
        self.alg_name = __name__
        self.log.info("Algorithm %s initializing", self.alg_name)

        # Add initialization steps here

        return (True, "")

    @Timer(name=__name__, text="", logger=None)
    def process(self, l1b: Dataset, shared_dict: dict) -> Tuple[bool, str]:
        """Main algorithm processing function

        Args:
            l1b (Dataset): input l1b file dataset (constant)
            shared_dict (dict): shared_dict data passed between algorithms

        Returns:
            Tuple : (success (bool), failure_reason (str))
            ie
            (False,'error string'), or (True,'')

        **IMPORTANT NOTE:** when logging within the Algorithm.process() function you must use
        the self.log.info(),error(),debug() logger and NOT log.info(), log.error(), log.debug :

        `self.log.error("your message")`

        """

        # This is required to support logging during multi-processing
        success, error_str = self.process_setup(l1b)
        if not success:
            return (False, error_str)

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

        if (
            "max_diff_to_ref_dem_lrm" in self.config["height_filters"]
            and shared_dict["instr_mode"] == "LRM"
        ):
            max_diff = self.config["height_filters"]["max_diff_to_ref_dem_lrm"]
        elif (
            "max_diff_to_ref_dem_sin" in self.config["height_filters"]
            and shared_dict["instr_mode"] == "SIN"
        ):
            max_diff = self.config["height_filters"]["max_diff_to_ref_dem_sin"]
        elif "max_diff_to_ref_dem" in self.config["height_filters"]:
            max_diff = self.config["height_filters"]["max_diff_to_ref_dem"]
        else:
            self.log.error("max_diff_to_ref_dem[_lrm,sin] not in height_filters")
            raise ValueError("max_diff_to_ref_dem[_lrm,sin] not in height_filters")

        elevation_outliers = np.where(
            np.abs(shared_dict["height_20_ku"] - shared_dict["dem_elevation_values"]) > max_diff
        )[0]
        if elevation_outliers.size > 0:
            shared_dict["height_filt"][elevation_outliers] = np.nan
            self.log.info(
                "Number of elevation outliers > |%d m| from DEM : %d",
                max_diff,
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

    # Note no finalize() required for this algorithm
