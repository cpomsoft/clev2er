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

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Runs init() if not in multi-processing mode
        Args:
            config (dict): configuration dictionary

        Returns:
            None
        """
        self.alg_name = __name__
        self.config = config

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

        # For multi-processing we do the init() in the Algorithm.process() function
        # This avoids pickling the init() data which is very slow
        if config["chain"]["use_multi_processing"]:
            return

        _, _ = self.init(log, 0)

    def init(self, mplog: logging.Logger, filenum: int) -> Tuple[bool, str]:
        """Algorithm initialization template

        Args:
            mplog (logging.Logger): log instance to use
            filenum (int): file number being processed

        Returns:
            (bool,str) : success or failure, error string
        """
        mplog.debug(
            "[f%d] Initializing algorithm %s",
            filenum,
            self.alg_name,
        )

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
        self, l1b: Dataset, shared_dict: dict, mplog: logging.Logger, filenum: int
    ) -> Tuple[bool, str]:
        """CLEV2ER Algorithm

        Args:
            l1b (Dataset): input l1b file dataset (constant)
            shared_dict (dict): shared_dict data passed between algorithms
            mplog (logging.Logger): multi-processing safe logger to use
            filenum (int) : file number of list of L1b files

        Returns:
            Tuple : (success (bool), failure_reason (str))
            ie
            (False,'error string'), or (True,'')

        **IMPORTANT NOTE:** when logging within the Algorithm.process() function you must use
        the mplog logger with a filenum as an argument:

        `mplog.error("[f%d] your message",filenum)`

        This is required to support logging during multi-processing
        """

        # When using multi-processing it is faster to initialize the algorithm
        # within each Algorithm.process(), rather than once in the main process's
        # Algorithm.__init__().
        # This avoids having to pickle the initialized data arrays (which is extremely slow)
        if self.config["chain"]["use_multi_processing"]:
            rval, error_str = self.init(mplog, filenum)
            if not rval:
                return (rval, error_str)

        mplog.debug(
            "[f%d] Processing algorithm %s",
            filenum,
            self.alg_name,
        )

        # Test that input l1b is a Dataset type

        if not isinstance(l1b, Dataset):
            mplog.error("[f%d] l1b parameter is not a netCDF4 Dataset type", filenum)
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

    def finalize(self):
        """Perform final algorithm actions"""
        log.debug("Finalize algorithm %s", self.alg_name)

        # --------------------------------------------------------
        # \/ Add algorithm finalization here \/
        # --------------------------------------------------------

        # --------------------------------------------------------
