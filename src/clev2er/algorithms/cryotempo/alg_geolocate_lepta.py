"""clev2er.algorithms.cryotempo.alg_geolocate_lepta"""

from typing import Tuple

import numpy as np
from codetiming import Timer  # used to time the Algorithm.process() function
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.algorithms.base.base_alg import BaseAlgorithm
from clev2er.utils.cs2.geolocate.geolocate_lepta import geolocate_lepta
from clev2er.utils.dems.dems import Dem
from clev2er.utils.dhdt_data.dhdt import Dhdt

# -------------------------------------------------

# pylint config
# Similar lines in 2 files, pylint: disable=R0801
# Too many return statements, pylint: disable=R0911


class Algorithm(BaseAlgorithm):
    """**Algorithm to perform LRM geolocation using an adpated Roemer/LEPTA method**.

    CLEV2ER Algorithm: inherits from BaseAlgorithm

    Relocation using 100m or 200m DEMS, using

    antarctic_dem: rema_ant_200m
    greenland_dem: arcticdem_100m_greenland

    BaseAlgorithm __init__(config,thislog)
        Args:
            config: Dict[str, Any]: chain configuration dictionary
            thislog: logging.Logger | None: initial logger instance to use or
                                            None (use root logger)

    **Contribution to shared dictionary**

        - shared_dict["lat_poca_20_ku"] : np.ndarray (POCA latitudes)
        - shared_dict["lon_poca_20_ku"] : np.ndarray (POCA longitudes)
        - shared_dict["height_20_ku"]   : np.ndarray (elevations)
        - shared_dict["latitudes"]   : np.ndarray (final latitudes == POCA or nadir if failed)
        - shared_dict["longitudes"]   : np.ndarray (final lons == POCA or nadir if failed)

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
        # -----------------------------------------------------------------
        #  \/ Place Algorithm initialization steps here \/
        # -----------------------------------------------------------------

        # Check for special case where we create a shared memory
        # version of the DEM's arrays. Note this _init_shared_mem config setting is set by
        # run_chain.py and should not be included in the config files
        init_shared_mem = "_init_shared_mem" in self.config

        # Load DEMs required by this algorithm
        if "grn_only" in self.config and self.config["grn_only"]:
            self.dem_ant = None
        else:
            self.dem_ant = Dem(
                self.config["lrm_lepta_geolocation"]["antarctic_dem"],
                config=self.config,
                store_in_shared_memory=init_shared_mem,
                thislog=self.log,
            )

        self.dem_grn = Dem(
            self.config["lrm_lepta_geolocation"]["greenland_dem"],
            config=self.config,
            store_in_shared_memory=init_shared_mem,
            thislog=self.log,
        )

        if self.config["lrm_lepta_geolocation"]["include_dhdt_correction"]:
            self.log.info("LEPTA dhdt correction enabled")
            self.dhdt_grn: Dhdt | None = Dhdt(
                self.config["lrm_lepta_geolocation"]["dhdt_grn_name"],
                config=self.config,
            )
            self.dhdt_ant = None  # Not implemented yet!
        else:
            self.dhdt_grn = None
            self.dhdt_ant = None

        # Important Note :
        #     each Dem classes instance must run Dem.clean_up() in Algorithm.finalize()

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

        if shared_dict["hemisphere"] == "south":
            thisdem = self.dem_ant
            thisdhdt = self.dhdt_ant
        else:
            thisdem = self.dem_grn
            thisdhdt = self.dhdt_grn

        height_20_ku, lat_poca_20_ku, lon_poca_20_ku, slope_ok = geolocate_lepta(
            l1b,
            thisdem,
            thisdhdt,
            self.config,
            shared_dict["cryotempo_surface_type"],
            shared_dict["geo_corrected_tracker_range"],
            shared_dict["retracker_correction"],
            # shared_dict["leading_edge_start"],
            # shared_dict["leading_edge_stop"],
            shared_dict["waveforms_to_include"],
        )

        self.log.info("LRM geolocation completed")

        shared_dict["lat_poca_20_ku"] = lat_poca_20_ku
        np.seterr(under="ignore")  # otherwise next line can fail
        shared_dict["lon_poca_20_ku"] = lon_poca_20_ku % 360.0
        shared_dict["height_20_ku"] = height_20_ku
        shared_dict["lepta_slope_ok"] = slope_ok

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
