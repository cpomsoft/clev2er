""" clev2er.algorithms.cryotempo.alg_dilated_coastal_mask """

# These imports required by Algorithm template
import logging
from typing import Tuple

import numpy as np
from codetiming import Timer
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.utils.masks.masks import Mask  # CPOM Cryosphere area masks

# -------------------------------------------------


# Similar lines in 2 files, pylint: disable=R0801

log = logging.getLogger(__name__)


# Too many return statements, pylint: disable=R0911


class Algorithm:
    """Algorithm to
    Form a mask array of points to include from a 10km dilated Ant or Grn coastal mask.
    Dilated coastal masks come from the Mask class :
    Mask('antarctica_iceandland_dilated_10km_grid_mask')
    Mask('greenland_iceandland_dilated_10km_grid_mask')

    # Contributions to shared_dict:
        shared_dict["dilated_surface_mask"] : (ndarray) of bool, True is inside dilated mask

    """

    def __init__(self, config) -> None:
        """initializes the Algorithm

        Args:
            config (dict): configuration dictionary

        Returns: None
        """
        self.alg_name = __name__
        self.config = config

        log.debug(
            "Initializing algorithm %s",
            self.alg_name,
        )

        # --------------------------------------------------------
        # \/ Add algorithm initialization here \/
        # --------------------------------------------------------

        # For multi-processing we do the init() in the Algorithm.process() function
        # This avoids pickling the init() data which is very slow
        if config["chain"]["use_multi_processing"]:
            # only continue with initialization if setting up shared memory
            if not config["chain"]["use_shared_memory"]:
                return
            if "_init_shared_mem" not in config:
                return
        # Run the algorithm initialization function when doing sequential processing
        # or setting up shared memory resources
        _, _ = self.init(log, 0)

    def init(self, mplog, filenum) -> Tuple[bool, str]:
        """Algorithm initialization

         Loads Bedmachine surface type Masks

        Returns:
            (bool,str) : success or failure, error string

        Raises:
            KeyError : keys not in config
            FileNotFoundError :
            OSError :

        Note: raise and Exception rather than just returning False
        """

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
            mplog.error(
                "[f%d] surface_type_masks:greenland_iceandland_dilated_10km_grid_mask "
                "not in config file, KeyError: %s",
                filenum,
                exc,
            )
            raise KeyError(exc) from None

        self.greenland_dilated_mask = Mask(
            "greenland_iceandland_dilated_10km_grid_mask",
            mask_path=mask_file,
            store_in_shared_memory=init_shared_mem,
            thislog=mplog,
        )
        # Antarctic dilated coastal mask (ie includes Antarctica (grounded+floating)
        # + 10km out to ocean
        try:
            mask_file = self.config["surface_type_masks"][
                "antarctica_iceandland_dilated_10km_grid_mask"
            ]
        except KeyError as exc:
            mplog.error(
                "[f%d] surface_type_masks:antarctica_iceandland_dilated_10km_grid_mask "
                "not in config file: %s",
                filenum,
                exc,
            )
            raise KeyError(exc) from None

        self.antarctic_dilated_mask = Mask(
            "antarctica_iceandland_dilated_10km_grid_mask",
            mask_path=mask_file,
            store_in_shared_memory=init_shared_mem,
            thislog=mplog,
        )

        # Important Note :
        #     each Mask classes instance must run Mask.clean_up() in Algorithm.finalize()

        return (True, "")

    @Timer(name=__name__, text="", logger=None)
    def process(self, l1b, shared_dict, mplog, filenum):
        """CLEV2ER Algorithm

        Interpolate surface type data from Bedmachine for nadir locations of L1b
        Transpose surface type values from Bedmachine grid to CryoTEMPO values:
        0=ocean, 1=grounded_ice, 2=floating_ice, 3=ice_free_land,4=non-Greenland land

        Args:
            l1b (Dataset): input l1b file dataset (constant)
            shared_dict (dict): shared_dict data passed between algorithms
            mplog: multi-processing safe logger to use
            filenum (int) : file number of list of L1b files

        Returns:
            Tuple : (success (bool), failure_reason (str))
            ie
            (False,'error string'), or (True,'')

        IMPORTANT NOTE: when logging within this function you must use the mplog logger
        with a filenum as an argument as follows:
        mplog.debug,info,error("[f%d] your message",filenum)
        This is required to support logging during multi-processing
        """

        # When using multi-processing it is faster to initialize the algorithm
        # within each Algorithm.process(), rather than once in the main process's
        # Algorithm.__init__().
        # This avoids having to pickle the initialized data arrays (which is extremely slow)
        if self.config["chain"]["use_multi_processing"]:
            self.init(mplog, filenum)

        mplog.info(
            "[f%d] Processing algorithm %s",
            filenum,
            self.alg_name.rsplit(".", maxsplit=1)[-1],
        )

        # Test that input l1b is a Dataset type

        if not isinstance(l1b, Dataset):
            mplog.error("[f%d] l1b parameter is not a netCDF4 Dataset type", filenum)
            return (False, "l1b parameter is not a netCDF4 Dataset type")

        # -------------------------------------------------------------------
        # Perform the algorithm processing, store results that need to passed
        # down the chain in the 'shared_dict' dict
        # -------------------------------------------------------------------

        if "hemisphere" not in shared_dict:
            mplog.error("[f%d] hemisphere not set in shared_dict", filenum)
            return (False, "hemisphere not set in shared_dict")

        # Select the appropriate mask, depending on hemisphere
        if shared_dict["hemisphere"] == "south":
            required_surface_mask, _, _ = self.antarctic_dilated_mask.points_inside(
                shared_dict["lats_nadir"], shared_dict["lons_nadir"]
            )
        else:
            required_surface_mask, _, _ = self.greenland_dilated_mask.points_inside(
                shared_dict["lats_nadir"], shared_dict["lons_nadir"]
            )

        n_in_dilated_surface_mask = np.count_nonzero(required_surface_mask)
        if n_in_dilated_surface_mask == 0:
            mplog.info(
                "[f%d] skipping as no locations inside dilated mask",
                filenum,
            )
            return (False, "SKIP_OK, no locations inside dilated mask")

        num_records = shared_dict["num_20hz_records"]

        percent_inside = n_in_dilated_surface_mask * 100.0 / num_records

        mplog.info(
            "[f%d] %% inside dilated mask  = %.2f%%",
            filenum,
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

        log.debug("Finalize algorithm %s called at stage %d", self.alg_name, stage)

        # --------------------------------------------------------
        # \/ Add algorithm finalization here \/
        # --------------------------------------------------------
        # Must run Mask.clean_up() for each Mask instance so that any shared memory is
        # unlinked, closed.
        try:  # try is required as algorithm may not have been initialized
            if self.greenland_dilated_mask is not None:
                self.greenland_dilated_mask.clean_up()
            if self.antarctic_dilated_mask is not None:
                self.antarctic_dilated_mask.clean_up()
        except AttributeError as exc:
            log.debug("mask object %s : %s stage %d", exc, self.alg_name, stage)

        # --------------------------------------------------------
