""" clev2er.algorithms.templates.alg_basin_ids"""

# These imports required by Algorithm template
import logging
from typing import Any, Dict, Tuple

import numpy as np
from codetiming import Timer  # used to time the Algorithm.process() function
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.utils.masks.masks import Mask

# -------------------------------------------------

# pylint config
# Similar lines in 2 files, pylint: disable=R0801
# Too many return statements, pylint: disable=R0911

log = logging.getLogger(__name__)


class Algorithm:
    """**Algorithm to do find ice sheet basin id for each location along track**

    ** Contribution to Shared Dictionary **

        - shared_dict["basin_mask_values_rignot"] : (np.ndarray), basin mask values from Rignot
        - shared_dict["basin_mask_values_zwally"] : (np.ndarray), basin mask values from Zwally

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

        # For multi-processing we do the init() in the Algorithm.process() function
        # This avoids pickling the init() data which is very slow
        if config["chain"]["use_multi_processing"]:
            # only continue with initialization if setting up shared memory
            if not config["chain"]["use_shared_memory"]:
                return
            if "_init_shared_mem" not in config:
                return

        _, _ = self.init(log, 0)

    def init(self, mplog: logging.Logger, filenum: int) -> Tuple[bool, str]:
        """Algorithm initialization template

        Args:
            mplog (logging.Logger): log instance to use
            filenum (int): file number being processed

        Returns:
            (bool,str) : success or failure, error string

        Raises:
            KeyError : keys not in config
            FileNotFoundError :
            OSError :

        Note: raise and Exception rather than just returning False
        """
        mplog.debug(
            "[f%d] Initializing algorithm %s",
            filenum,
            self.alg_name,
        )

        # Check for special case where we create a shared memory
        # version of the DEM's arrays. Note this _init_shared_mem config setting is set by
        # run_chain.py and should not be included in the config files
        init_shared_mem = "_init_shared_mem" in self.config

        # ---------------------------------------------------------------------------------
        # Load Basin Masks required to create 'basin_id' netCDF variable
        #  antarctic_grounded_and_floating_2km_grid_mask
        #  greenland_icesheet_2km_grid_mask
        #  antarctic_icesheet_2km_grid_mask_rignot2016
        # greenland_icesheet_2km_grid_mask_rignot2016
        # ---------------------------------------------------------------------------------

        required_masks = [
            "antarctic_grounded_and_floating_2km_grid_mask",
            "greenland_icesheet_2km_grid_mask",
            "antarctic_icesheet_2km_grid_mask_rignot2016",
            "greenland_icesheet_2km_grid_mask_rignot2016",
        ]

        # Check mask paths in config file
        mask_paths = {}
        for mask in required_masks:
            try:
                mask_file = self.config["basin_masks"][mask]
            except KeyError as exc:
                mplog.error(
                    "[f%d] surface_type_masks:%s not in config file, %s",
                    filenum,
                    mask,
                    exc,
                )
                raise KeyError(f"surface_type_masks:{mask} not in config file") from exc
            mask_paths[mask] = mask_file

        # Load : antarctic_grounded_and_floating_2km_grid_mask
        #      : source: Zwally 2012, ['unknown','1',..'27']
        self.zwally_basin_mask_ant = Mask(
            "antarctic_grounded_and_floating_2km_grid_mask",
            mask_path=mask_paths["antarctic_grounded_and_floating_2km_grid_mask"],
            store_in_shared_memory=init_shared_mem,
            thislog=mplog,
        )  # source: Zwally 2012, ['unknown','1',..'27']

        # Load: greenland_icesheet_2km_grid_mask
        # source: Zwally 2012, ['None', '1.1', '1.2', '1.3', '1.4', '2.1', '2.2', '3.1', '3.2',
        # '3.3', '4.1', '4.2', '4.3', '5.0', '6.1', '6.2', '7.1', '7.2', '8.1', '8.2']

        self.zwally_basin_mask_grn = Mask(
            "greenland_icesheet_2km_grid_mask",
            mask_path=mask_paths["greenland_icesheet_2km_grid_mask"],
            store_in_shared_memory=init_shared_mem,
            thislog=mplog,
        )

        # Load: antarctic_icesheet_2km_grid_mask_rignot2016
        # source: Rignot 2016, values: 0-18 ['Islands','West H-Hp','West F-G',
        # 'East E-Ep','East D-Dp',
        # 'East Cp-D','East B-C','East A-Ap','East Jpp-K','West G-H','East Dp-E','East Ap-B',
        # 'East C-Cp',
        # 'East K-A','West J-Jpp','Peninsula Ipp-J','Peninsula I-Ipp','Peninsula Hp-I','West Ep-F']
        self.rignot_basin_mask_ant = Mask(
            "antarctic_icesheet_2km_grid_mask_rignot2016",
            mask_path=mask_paths["antarctic_icesheet_2km_grid_mask_rignot2016"],
            store_in_shared_memory=init_shared_mem,
            thislog=mplog,
        )

        # Load: greenland_icesheet_2km_grid_mask_rignot2016
        # source: Rignot 2016, values: 0,1-56: 0 (unclassified), 1-50 (ice caps), 51 (NW), 52(CW),
        # 53(SW), 54(SE), 55(NE), 56(NO)
        self.rignot_basin_mask_grn = Mask(
            "greenland_icesheet_2km_grid_mask_rignot2016",
            mask_path=mask_paths["greenland_icesheet_2km_grid_mask_rignot2016"],
            store_in_shared_memory=init_shared_mem,
            thislog=mplog,
        )

        # Important Note :
        #     each Mask classes instance must run Mask.clean_up() in Algorithm.finalize()

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

        if shared_dict["hemisphere"] == "south":
            # 0..27 : ['unknown','1',..'27']
            mask_values_zwally = self.zwally_basin_mask_ant.grid_mask_values(
                shared_dict["latitudes"], shared_dict["longitudes"], unknown_value=0
            )

            # 0..18: ['Islands','West H-Hp','West F-G','East E-Ep','East D-Dp','East Cp-D',
            # 'East B-C','East A-Ap','East Jpp-K','West G-H','East Dp-E','East Ap-B','East C-Cp',
            # 'East K-A','West J-Jpp','Peninsula Ipp-J','Peninsula I-Ipp','Peninsula Hp-I',
            # 'West Ep-F']
            # 999 (unknown)
            mask_values_rignot = self.rignot_basin_mask_ant.grid_mask_values(
                shared_dict["latitudes"], shared_dict["longitudes"], unknown_value=999
            )

            # reset the number range so we have 0 (unclassified), 1 (islands)..19(West EP-F)
            for i, m in enumerate(mask_values_rignot):
                if 0 <= m <= 18:
                    mask_values_rignot[i] = m + 1
                else:
                    mask_values_rignot[i] = 0
        else:
            # 0..19 : ['None', '1.1', '1.2', '1.3', '1.4', '2.1', '2.2', '3.1', '3.2', '3.3', '4.1',
            # '4.2', '4.3', '5.0', '6.1', '6.2', '7.1', '7.2', '8.1', '8.2']
            mask_values_zwally = self.zwally_basin_mask_grn.grid_mask_values(
                shared_dict["latitudes"], shared_dict["longitudes"], unknown_value=0
            )

            mask_values_rignot = self.rignot_basin_mask_grn.grid_mask_values(
                shared_dict["latitudes"], shared_dict["longitudes"], unknown_value=0
            )  # 0..56 : (unclassified), 1-50 (ice caps), 51 (NW), 52(CW), 53(SW), 54(SE),
            #            55(NE), 56(NO)
            # reset the number range so we have 0 (unclassified),
            # 1 (ice caps), 2(NW), 3(CW), 4(SW), 5(SE), 6(NE), 7(NO)
            for i, m in enumerate(mask_values_rignot):
                if 1 <= m <= 50:
                    mask_values_rignot[i] = 1
                elif 51 <= m <= 56:
                    mask_values_rignot[i] = (m - 50) + 1
                else:
                    mask_values_rignot[i] = 0

        shared_dict["basin_mask_values_rignot"] = mask_values_rignot.astype(np.uint)
        shared_dict["basin_mask_values_zwally"] = mask_values_zwally.astype(np.uint)

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
            if self.zwally_basin_mask_ant is not None:
                self.zwally_basin_mask_ant.clean_up()
            if self.zwally_basin_mask_grn is not None:
                self.zwally_basin_mask_grn.clean_up()

            if self.rignot_basin_mask_ant is not None:
                self.rignot_basin_mask_ant.clean_up()
            if self.rignot_basin_mask_grn is not None:
                self.rignot_basin_mask_grn.clean_up()
        except AttributeError as exc:
            log.debug("mask object %s : %s stage %d", exc, self.alg_name, stage)

        # --------------------------------------------------------
