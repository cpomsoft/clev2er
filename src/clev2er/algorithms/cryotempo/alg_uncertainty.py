""" clev2er.algorithms.templates.alg_uncertainty"""

import os
from typing import Tuple

import numpy as np
from codetiming import Timer  # used to time the Algorithm.process() function
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.algorithms.base.base_alg import BaseAlgorithm
from clev2er.utils.slopes.slopes import Slopes
from clev2er.utils.uncertainty.calc_uncertainty import calc_uncertainty

# -------------------------------------------------

# pylint config
# Similar lines in 2 files, pylint: disable=R0801
# Too many return statements, pylint: disable=R0911
# pylint: disable=too-many-instance-attributes


class Algorithm(BaseAlgorithm):
    """**Algorithm to retrieve elevation uncertainty from (CS2-IS2) derived uncertainty table and
    surface slope at each measurement**

    **Contribution to shared_dict**
        -shared_dict["uncertainty"] : (np.ndarray) uncertainty at each track location

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

        self.uncertainty_table_antarctica = ""
        self.uncertainty_table_greenland = ""
        self.ut_table_grn = None
        self.ut_min_slope_grn = 0.0
        self.ut_max_slope_grn = 10.0
        self.ut_number_of_bins_grn = None
        self.ut_table_ant = None
        self.ut_min_slope_ant = 0.0
        self.ut_max_slope_ant = 10.0
        self.ut_number_of_bins_ant = None

        # -------------------------------------------------------------------------
        # Load uncertainty tables
        # -------------------------------------------------------------------------

        # Get uncertainty table files
        if "uncertainty_tables" not in self.config:
            raise KeyError("uncertainty_tables not in config")
        if "base_dir" not in self.config["uncertainty_tables"]:
            raise KeyError("uncertainty_tables.base_dir not in config")

        self.uncertainty_table_antarctica = (
            f"{self.config['uncertainty_tables']['base_dir']}/"
            "antarctica_uncertainty_from_is2.npz"
        )
        self.uncertainty_table_greenland = (
            f"{str(self.config['uncertainty_tables']['base_dir'])}/"
            "greenland_uncertainty_from_is2.npz"
        )

        if not os.path.isfile(self.uncertainty_table_antarctica):
            raise FileNotFoundError(
                f"Antarctic uncertainty table {self.uncertainty_table_antarctica}" " not found"
            )
        if not os.path.isfile(self.uncertainty_table_greenland):
            raise FileNotFoundError(
                f"Greenland uncertainty table {self.uncertainty_table_greenland}" " not found"
            )

        ut_grn_data = np.load(self.uncertainty_table_greenland, allow_pickle=True)
        ut_ant_data = np.load(self.uncertainty_table_antarctica, allow_pickle=True)

        keys = ["uncertainty_table", "min_slope", "max_slope", "number_of_bins"]
        for key in keys:
            if key not in ut_grn_data:
                raise KeyError(
                    f"{key} key not in Greenland uncertainty table"
                    f" {self.uncertainty_table_greenland}"
                )
            if key not in ut_ant_data:
                raise KeyError(
                    f"{key} key not in Antarctic uncertainty table"
                    f" {self.uncertainty_table_greenland}"
                )

        self.ut_table_grn = ut_grn_data.get("uncertainty_table")
        self.ut_min_slope_grn = ut_grn_data.get("min_slope")
        self.ut_max_slope_grn = ut_grn_data.get("max_slope")
        self.ut_number_of_bins_grn = ut_grn_data.get("number_of_bins")

        self.ut_table_ant = ut_ant_data.get("uncertainty_table")
        self.ut_min_slope_ant = ut_ant_data.get("min_slope")
        self.ut_max_slope_ant = ut_ant_data.get("max_slope")
        self.ut_number_of_bins_ant = ut_ant_data.get("number_of_bins")

        self.slope_grn = Slopes("awi_grn_2013_1km_slopes")
        if "grn_only" in self.config and self.config["grn_only"]:
            self.slope_ant = None
        else:
            self.slope_ant = Slopes("cpom_ant_2018_1km_slopes")

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

        # Calculate uncertainty from POCA (or nadir if POCA failed) parameters:
        # shared_dict["latitudes"], shared_dict["longitudes"]

        if shared_dict["hemisphere"] == "south":
            if self.slope_ant is not None:
                slopes = self.slope_ant.interp_slope_from_lat_lon(
                    shared_dict["latitudes"], shared_dict["longitudes"]
                )
                uncertainty = calc_uncertainty(
                    slopes,
                    self.ut_table_ant,
                    self.ut_min_slope_ant,
                    self.ut_max_slope_ant,
                )
            else:
                uncertainty = None
        else:
            slopes = self.slope_grn.interp_slope_from_lat_lon(
                shared_dict["latitudes"], shared_dict["longitudes"]
            )
            uncertainty = calc_uncertainty(
                slopes, self.ut_table_grn, self.ut_min_slope_grn, self.ut_max_slope_grn
            )

        shared_dict["uncertainty"] = uncertainty

        # Return success (True,'')
        return (True, "")


# No finalize() required for this algorithm
