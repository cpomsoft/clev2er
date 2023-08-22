""" clev2er.algorithms.cryotempo.alg_geolocate_sin"""

# These imports required by Algorithm template
import logging
from typing import Any, Dict, Tuple

import numpy as np
from codetiming import Timer  # used to time the Algorithm.process() function
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.utils.cs2.geolocate.geolocate_sin import geolocate_sin
from clev2er.utils.dems.dems import Dem

# -------------------------------------------------

# pylint config
# Similar lines in 2 files, pylint: disable=R0801
# Too many return statements, pylint: disable=R0911

log = logging.getLogger(__name__)


class Algorithm:
    """**Algorithm to geolocate measurements to the POCA (point of closest approach) for SIN**

    Also to calculate height_20_ku

    ** Contribution to Shared Dictionary **

        - shared_dict["lat_poca_20_ku"] : np.ndarray (POCA latitudes)
        - shared_dict["lon_poca_20_ku"] : np.ndarray (POCA longitudes)
        - shared_dict["height_20_ku"]   : np.ndarray (elevations)
        - shared_dict["latitudes"]   : np.ndarray (final latitudes == POCA or nadir if failed)
        - shared_dict["longitudes"]   : np.ndarray (final lons == POCA or nadir if failed)

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

        self.dem_ant: Any = None
        self.dem_grn: Any = None

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

        # Get the DEMs required for SIN slope correction
        # DEM file locations are stored in config

        # Check for special case where we create a shared memory
        # version of the DEM's arrays. Note this _init_shared_mem config setting is set by
        # run_chain.py and should not be included in the config files
        init_shared_mem = "_init_shared_mem" in self.config

        self.dem_ant = Dem(
            "rema_ant_1km",
            config=self.config,
            store_in_shared_memory=init_shared_mem,
        )

        self.dem_grn = Dem(
            "arcticdem_1km", config=self.config, store_in_shared_memory=init_shared_mem
        )
        # Important Note :
        #     each Dem classes instance must run Dem.clean_up() in Algorithm.finalize()

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

        # --------------------------------------------------------------------
        # Geo-location (slope correction)
        # --------------------------------------------------------------------

        if shared_dict["instr_mode"] != "SIN":
            self.log.info("algorithm skipped as not SIN file")
            return (True, "algorithm skipped as not SIN file")

        self.log.info("Calling SIN geolocation")

        height_20_ku, lat_poca_20_ku, lon_poca_20_ku = geolocate_sin(
            l1b,
            self.config,
            self.dem_ant,
            self.dem_grn,
            shared_dict["range_cor_20_ku"],
            shared_dict["ind_wfm_retrack_20_ku"],
        )
        self.log.info("SIN geolocation completed")

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

        # Must run Dem.clean_up() for each Dem instance so that any shared memory is
        # unlinked, closed.
        if self.dem_ant is not None:
            self.dem_ant.clean_up()
        if self.dem_grn is not None:
            self.dem_grn.clean_up()

        # --------------------------------------------------------
