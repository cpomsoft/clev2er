""" clev2er.algorithms.templates.alg_ref_dem"""

from typing import Tuple

from codetiming import Timer  # used to time the Algorithm.process() function
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.algorithms.base.base_alg import BaseAlgorithm
from clev2er.utils.dems.dems import Dem

# -------------------------------------------------

# pylint config
# Similar lines in 2 files, pylint: disable=R0801
# Too many return statements, pylint: disable=R0911


class Algorithm(BaseAlgorithm):
    """**Algorithm to find reference DEM elevation values for each track location**

    CLEV2ER Algorithm: inherits from BaseAlgorithm

    BaseAlgorithm __init__(config,thislog)
        Args:
            config: Dict[str, Any]: chain configuration dictionary
            thislog: logging.Logger | None: initial logger instance to use or
                                            None (use root logger)

        **Contribution to shared dictionary**

        - shared_dict['dem_elevation_values'] : (ndarray), reference DEM elevation values (m) for
                                                           each track location

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

        # Load DEMs for Antarctica and Greenland
        # Check for special case where we create a shared memory
        # version of the DEM's arrays. Note this _init_shared_mem config setting is set by
        # run_chain.py and should not be included in the config files
        init_shared_mem = "_init_shared_mem" in self.config

        if "grn_only" in self.config and self.config["grn_only"]:
            self.dem_ant = None
        else:
            self.dem_ant = Dem(
                "rema_ant_1km",
                config=self.config,
                store_in_shared_memory=init_shared_mem,
                thislog=self.log,
            )

        self.dem_grn = Dem(
            "arcticdem_1km",
            config=self.config,
            store_in_shared_memory=init_shared_mem,
            thislog=self.log,
        )
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

        # -------------------------------------------------------------------
        # Find Dem values for each location in m
        # -------------------------------------------------------------------

        if shared_dict["hemisphere"] == "south":
            if self.dem_ant is not None:
                dem_elevation_values = self.dem_ant.interp_dem(
                    shared_dict["latitudes"],
                    shared_dict["longitudes"],
                    method="linear",
                    xy_is_latlon=True,
                )
            else:
                dem_elevation_values = None
        else:
            dem_elevation_values = self.dem_grn.interp_dem(
                shared_dict["latitudes"],
                shared_dict["longitudes"],
                method="linear",
                xy_is_latlon=True,
            )

        shared_dict["dem_elevation_values"] = dem_elevation_values

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
