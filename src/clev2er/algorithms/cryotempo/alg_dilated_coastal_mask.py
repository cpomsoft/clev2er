""" clev2er.algorithms.cryotempo.alg_dilated_coastal_mask """

# These imports required by Algorithm template
import logging
from typing import Any, Dict, Tuple

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

        if "hemisphere" not in shared_dict:
            self.log.error("hemisphere not set in shared_dict")
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
            self.log.info(
                "skipping as no locations inside dilated mask",
            )
            return (False, "SKIP_OK, no locations inside dilated mask")

        num_records = shared_dict["num_20hz_records"]

        percent_inside = n_in_dilated_surface_mask * 100.0 / num_records

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
        try:  # try is required as algorithm may not have been initialized
            if self.greenland_dilated_mask is not None:
                self.greenland_dilated_mask.clean_up()
            if self.antarctic_dilated_mask is not None:
                self.antarctic_dilated_mask.clean_up()
        except AttributeError as exc:
            self.log.debug("mask object %s : %s stage %d", exc, self.alg_name, stage)

        # --------------------------------------------------------
