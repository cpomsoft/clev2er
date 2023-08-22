""" clev2er.algorithms.templates.alg_uncertainty"""

import logging
import os
from typing import Any, Dict, Tuple

import numpy as np
from codetiming import Timer  # used to time the Algorithm.process() function
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.utils.slopes.slopes import Slopes
from clev2er.utils.uncertainty.calc_uncertainty import calc_uncertainty

# -------------------------------------------------

# pylint config
# Similar lines in 2 files, pylint: disable=R0801
# Too many return statements, pylint: disable=R0911

log = logging.getLogger(__name__)

# pylint: disable=too-many-instance-attributes


class Algorithm:
    """**Algorithm to retrieve elevation uncertainty from (CS2-IS2) derived uncertainty table and
    surface slope at each measurement**

    **Contribution to shared_dict**
        -shared_dict["uncertainty"] : (np.ndarray) uncertainty at each track location
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
                f"Antarctic uncertainty table {self.uncertainty_table_antarctica}"
                " not found"
            )
        if not os.path.isfile(self.uncertainty_table_greenland):
            raise FileNotFoundError(
                f"Greenland uncertainty table {self.uncertainty_table_greenland}"
                " not found"
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
        self.slope_ant = Slopes("cpom_ant_2018_1km_slopes")

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
        # Perform the algorithm processing, store results that need to passed
        # down the chain in the 'shared_dict' dict
        # -------------------------------------------------------------------

        # Calculate uncertainty from POCA (or nadir if POCA failed) parameters:
        # shared_dict["latitudes"], shared_dict["longitudes"]

        if shared_dict["hemisphere"] == "south":
            slopes = self.slope_ant.interp_slope_from_lat_lon(
                shared_dict["latitudes"], shared_dict["longitudes"]
            )
            uncertainty = calc_uncertainty(
                slopes, self.ut_table_ant, self.ut_min_slope_ant, self.ut_max_slope_ant
            )
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
