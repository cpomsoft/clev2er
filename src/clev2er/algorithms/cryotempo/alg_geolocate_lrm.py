""" clev2er.algorithms.cryotempo.alg_geolocate_lrm"""

# These imports required by Algorithm template
import os
from typing import Tuple

import numpy as np
from codetiming import Timer  # used to time the Algorithm.process() function
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.algorithms.base.base_alg import BaseAlgorithm
from clev2er.utils.cs2.geolocate.geolocate_lrm import geolocate_lrm

# -------------------------------------------------

# pylint config
# Similar lines in 2 files, pylint: disable=R0801
# Too many return statements, pylint: disable=R0911


class Algorithm(BaseAlgorithm):
    """**Algorithm to geolocate measurements to the POCA (point of closest approach) for LRM**

    Also to calculate height_20_ku

    CLEV2ER Algorithm: inherits from BaseAlgorithm

    BaseAlgorithm __init__(config,thislog)
        Args:
            config: Dict[str, Any]: chain configuration dictionary
            thislog: logging.Logger | None: initial logger instance to use or
                                            None (use root logger)

    ** Contribution to Shared Dictionary **

        - shared_dict["lat_poca_20_ku"] : np.ndarray (POCA latitudes)
        - shared_dict["lon_poca_20_ku"] : np.ndarray (POCA longitudes)
        - shared_dict["height_20_ku"]   : np.ndarray (elevations)
        - shared_dict["latitudes"]   : np.ndarray (final latitudes == POCA or nadir if failed)
        - shared_dict["longitudes"]   : np.ndarray (final lons == POCA or nadir if failed)

    """

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

        # Check slope models file
        if not os.path.isfile(self.config["slope_models"]["model_file"]):
            self.log.error(
                "slope model file: %s not found",
                self.config["slope_models"]["model_file"],
            )
            return (
                False,
                f'slope model file: {self.config["slope_models"]["model_file"]} not found',
            )

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

        # --------------------------------------------------------------------
        # Geo-location (slope correction)
        # --------------------------------------------------------------------

        if shared_dict["instr_mode"] != "LRM":
            self.log.info("algorithm skipped as not LRM file")
            return (True, "algorithm skipped as not LRM file")

        self.log.info("Calling LRM geolocation")

        height_20_ku, lat_poca_20_ku, lon_poca_20_ku = geolocate_lrm(
            l1b,
            self.config,
            shared_dict["cryotempo_surface_type"],
            shared_dict["range_cor_20_ku"],
        )
        self.log.info("LRM geolocation completed")

        shared_dict["lat_poca_20_ku"] = lat_poca_20_ku
        np.seterr(under="ignore")  # otherwise next line can fail
        shared_dict["lon_poca_20_ku"] = lon_poca_20_ku % 360.0
        shared_dict["height_20_ku"] = height_20_ku

        # Calculate final product latitudes, longitudes from POCA, set to
        # nadir where no POCA available

        poca_failed = np.where(np.isnan(lat_poca_20_ku))[0]

        latitudes = lat_poca_20_ku
        longitudes = lon_poca_20_ku

        if poca_failed.size > 0:
            self.log.info(
                "POCA replaced by nadir in %d of %d measurements ",
                poca_failed.size,
                latitudes.size,
            )
            latitudes[poca_failed] = l1b["lat_20_ku"][:].data[poca_failed]
            longitudes[poca_failed] = l1b["lon_20_ku"][:].data[poca_failed]

        shared_dict["latitudes"] = latitudes
        shared_dict["longitudes"] = longitudes

        # Return success (True,'')
        return (True, "")

    # No finalize() required for this algorithm
