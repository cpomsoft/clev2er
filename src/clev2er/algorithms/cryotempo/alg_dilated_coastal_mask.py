""" clev2er.algorithms.cryotempo.alg_dilated_coastal_mask """

# These imports required by Algorithm template
from typing import Tuple

from codetiming import Timer
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.algorithms.base.base_alg import BaseAlgorithm
from clev2er.utils.masks.masks import Mask  # CPOM Cryosphere area masks

# -------------------------------------------------

# Similar lines in 2 files, pylint: disable=R0801
# Too many return statements, pylint: disable=R0911


class Algorithm(BaseAlgorithm):
    """Algorithm to
    Form a mask array of points to include from a 10km dilated Ant or Grn coastal mask.
    Dilated coastal masks come from the Mask class :
    Mask('antarctica_iceandland_dilated_10km_grid_mask')
    Mask('greenland_iceandland_dilated_10km_grid_mask')

    CLEV2ER Algorithm: inherits from BaseAlgorithm

    BaseAlgorithm __init__(config,thislog)
        Args:
            config: Dict[str, Any]: chain configuration dictionary
            thislog: logging.Logger | None: initial logger instance to use or
                                            None (use root logger)
    # Contributions to shared_dict:
        shared_dict["dilated_surface_mask"] : (ndarray) of bool, True is inside dilated mask
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
        # Check for special case where we create a shared memory
        # version of the DEM's arrays. Note this _init_shared_mem config setting is set by
        # run_chain.py and should not be included in the config files
        init_shared_mem = "_init_shared_mem" in self.config

        # Greenland dilated coastal mask (ie includes Greenland + 10km out to ocean)
        try:
            mask_file = self.config["surface_type_masks"][
                "greenland_iceandland_dilated_10km_grid_mask"
            ]
        except KeyError as exc:
            self.log.error(
                "surface_type_masks:greenland_iceandland_dilated_10km_grid_mask "
                "not in config file, KeyError: %s",
                exc,
            )
            raise KeyError(exc) from None

        self.greenland_dilated_mask = Mask(
            "greenland_iceandland_dilated_10km_grid_mask",
            mask_path=mask_file,
            store_in_shared_memory=init_shared_mem,
            thislog=self.log,
        )
        # Antarctic dilated coastal mask (ie includes Antarctica (grounded+floating)
        # + 10km out to ocean
        try:
            mask_file = self.config["surface_type_masks"][
                "antarctica_iceandland_dilated_10km_grid_mask"
            ]
        except KeyError as exc:
            self.log.error(
                "surface_type_masks:antarctica_iceandland_dilated_10km_grid_mask "
                "not in config file: %s",
                exc,
            )
            raise KeyError(exc) from None

        # Don't initialize Antarctic mask if processing Greenland only
        if "grn_only" in self.config and self.config["grn_only"]:
            self.antarctic_dilated_mask = None
        else:
            self.antarctic_dilated_mask = Mask(
                "antarctica_iceandland_dilated_10km_grid_mask",
                mask_path=mask_file,
                store_in_shared_memory=init_shared_mem,
                thislog=self.log,
            )

        # Important Note :
        #     each Mask classes instance must run Mask.clean_up() in Algorithm.finalize()

        return (True, "")

    @Timer(name=__name__, text="", logger=None)
    def process(self, l1b: Dataset, shared_dict: dict) -> Tuple[bool, str]:
        """Main algorithm processing function

        Interpolate surface type data from Bedmachine for nadir locations of L1b
        Transpose surface type values from Bedmachine grid to CryoTEMPO values:
        0=ocean, 1=grounded_ice, 2=floating_ice, 3=ice_free_land,4=non-Greenland land

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
        # Perform the algorithm processing, store results that need to passed
        # down the chain in the 'shared_dict' dict
        # -------------------------------------------------------------------

        if "hemisphere" not in shared_dict:
            self.log.error("hemisphere not set in shared_dict")
            return (False, "hemisphere not set in shared_dict")

        # Select the appropriate mask, depending on hemisphere
        if shared_dict["hemisphere"] == "south":
            if self.antarctic_dilated_mask is not None:
                required_surface_mask, n_inside = self.antarctic_dilated_mask.points_inside(
                    shared_dict["lats_nadir"], shared_dict["lons_nadir"]
                )
            else:
                required_surface_mask = None
        else:
            required_surface_mask, n_inside = self.greenland_dilated_mask.points_inside(
                shared_dict["lats_nadir"], shared_dict["lons_nadir"]
            )

        if n_inside == 0:
            self.log.info(
                "skipping as no locations inside dilated mask",
            )
            return (False, "SKIP_OK, no locations inside dilated mask")

        num_records = shared_dict["num_20hz_records"]

        percent_inside = n_inside * 100.0 / num_records

        self.log.info(
            "%% inside dilated mask  = %.2f%%",
            percent_inside,
        )

        shared_dict["dilated_surface_mask"] = required_surface_mask

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
        # Must run Mask.clean_up() for each Mask instance so that any shared memory is
        # unlinked, closed.
        if self.greenland_dilated_mask is not None:
            self.greenland_dilated_mask.clean_up()
        if self.antarctic_dilated_mask is not None:
            self.antarctic_dilated_mask.clean_up()

        # --------------------------------------------------------
