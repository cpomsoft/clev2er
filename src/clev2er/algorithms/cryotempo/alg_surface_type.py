""" clev2er.algorithms.cryotempo.alg_surface_type """

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
# Too many statements, pylint: disable=R0915
# Too many locals, pylint: disable=R0914
# Too many branches, pylint: disable=R0912


class Algorithm:
    """**Algorithm to find the surface type from Bedmachine v2 (ANT)/v3 (GRN)**

    Contributions to shared_dict:
        shared_dict["ocean_locations"] : (ndarray), ocean locations
        shared_dict["grounded_ice_locations"]  : (ndarray), grounded ice locations
        shared_dict["floating_ice_locations"]  : (ndarray), floating ice locations
        shared_dict["icefree_land_locations"]  : (ndarray), ice free land locations
        shared_dict["non_grn_land_locations"]  : (ndarray), locations of land locs not in Greenland
        shared_dict["cryotempo_surface_type"]  : (ndarray), values of surface type as specified
                                                 CT (0..4), as shown below

    corresponding to L1b records
     Uses:
     -  Bedmachine v2 for Antarctica : https://nsidc.org/data/nsidc-0756/versions/2
     -  Bedmachine v3 for Greenland : https://nsidc.org/data/idbmg4

    Antarctica mask values: 0,1,2,3,4 = ocean ice_free_land grounded_ice
                                        floating_ice lake_vostok
    Greenland mask values: 0,1,2,3,4 = ocean ice_free_land grounded_ice floating_ice
                                        non-Greenland land

    Remap to Cryo-TEMPO surface type values (from ATBD):

    Antarctica:
       CT --  surface (source value)
             0  --  ocean (0)
             1  --  grounded ice (2 (grounded Ice) and 4 (Lake Vostok))
             2  --  floating ice (3)
             3  --  ice free land (1)

     Greenland:
       CT --  surface (source value)
             0  --  ocean (0)
             1  --  grounded ice (2)
             2  --  floating ice (3)
             3  --  ice free land (1)
             4  --  non-Greenland land (4)

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

        # Antarctic surface type mask from BedMachine v2
        try:
            mask_file = self.config["surface_type_masks"][
                "antarctica_bedmachine_v2_grid_mask"
            ]
        except KeyError as exc:
            self.log.error(
                "surface_type_masks:antarctica_bedmachine_v2_grid_mask not in config file %s",
                exc,
            )
            raise KeyError(exc) from None

        self.antarctic_surface_mask = Mask(
            "antarctica_bedmachine_v2_grid_mask",
            mask_path=mask_file,
            store_in_shared_memory=init_shared_mem,
            thislog=self.log,
        )
        # Greenland surface type mask from BedMachine v3
        try:
            mask_file = self.config["surface_type_masks"][
                "greenland_bedmachine_v3_grid_mask"
            ]
        except KeyError as exc:
            self.log.error(
                "surface_type_masks:greenland_bedmachine_v3_grid_mask not in config file: %s",
                exc,
            )
            raise KeyError(exc) from None

        self.greenland_surface_mask = Mask(
            "greenland_bedmachine_v3_grid_mask",
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
            surface_mask = self.antarctic_surface_mask
        else:
            surface_mask = self.greenland_surface_mask

        # Get source surface types from mask
        #   AIS: 0,1,2,3,4 = ocean ice_free_land grounded_ice floating_ice lake_vostok
        #   GIS: 0,1,2,3,4 = ocean ice_free_land grounded_ice floating_ice non-Greenland land
        surface_type_20_ku = surface_mask.grid_mask_values(
            shared_dict["lats_nadir"], shared_dict["lons_nadir"], unknown_value=0
        )

        self.log.debug(
            "surface_type_20_ku of file %d %s",
            filenum,
            str(surface_type_20_ku),
        )

        ocean_locations = np.where(surface_type_20_ku == 0)[0]
        icefree_land_locations = np.where(surface_type_20_ku == 1)[0]
        grounded_ice_locations = np.where(surface_type_20_ku == 2)[0]
        floating_ice_locations = np.where(surface_type_20_ku == 3)[0]

        # Map source surface type values to Cryo-TEMPO values: 0=ocean, 1=grounded_ice,
        # 2=floating_ice, 3=ice_free_land,4=non-Greenland land
        # Ocean (0) and non-Greenland land (4) is already correctly mapped
        if icefree_land_locations.size > 0:
            surface_type_20_ku[icefree_land_locations] = 3
        if grounded_ice_locations.size > 0:
            surface_type_20_ku[grounded_ice_locations] = 1
        if floating_ice_locations.size > 0:
            surface_type_20_ku[floating_ice_locations] = 2

        if shared_dict["hemisphere"] == "south":
            # Replace surface type 4 (Lake Vostok) with surface type 2 (grounded ice)
            lake_vostok_surface_indices = np.where(surface_type_20_ku == 4)[0]
            if lake_vostok_surface_indices.size > 0:
                surface_type_20_ku[lake_vostok_surface_indices] = 1

        # --------------------------------------------------------------------------------
        # Check if the L1b file contains no locations over grounded or floating ice or
        # ice free land. If so skip the file
        # --------------------------------------------------------------------------------

        if (
            grounded_ice_locations.size
            + floating_ice_locations.size
            + icefree_land_locations.size
        ) == 0:
            self.log.info(
                "File %d Skipped: No grounded or floating ice or icefree_land in file %s",
                filenum,
                shared_dict["l1b_file_name"],
            )
            return (
                False,
                (
                    "SKIP_OK, No grounded or floating ice or icefree_land in file "
                    f'{shared_dict["l1b_file_name"]}'
                ),
            )

        # Save the CryoTEMPO adapted surface type
        shared_dict["cryotempo_surface_type"] = surface_type_20_ku

        # Calculate % of each surface type using CryoTEMPO values
        # 0=ocean, 1=grounded_ice, 2=floating_ice, 3=ice_free_land,4=non-Greenland land

        ocean_locations = np.where(surface_type_20_ku == 0)[0]
        grounded_ice_locations = np.where(surface_type_20_ku == 1)[0]
        floating_ice_locations = np.where(surface_type_20_ku == 2)[0]
        icefree_land_locations = np.where(surface_type_20_ku == 3)[0]
        non_grn_land_locations = np.where(surface_type_20_ku == 4)[0]

        shared_dict["ocean_locations"] = ocean_locations
        shared_dict["grounded_ice_locations"] = grounded_ice_locations
        shared_dict["floating_ice_locations"] = floating_ice_locations
        shared_dict["icefree_land_locations"] = icefree_land_locations
        shared_dict["non_grn_land_locations"] = non_grn_land_locations

        total_records = shared_dict["num_20hz_records"]
        n_ocean_locations = len(ocean_locations)
        n_icefree_land_locations = len(icefree_land_locations)
        n_grounded_ice_locations = len(grounded_ice_locations)
        n_floating_ice_locations = len(floating_ice_locations)
        n_non_grn_land_locations = len(non_grn_land_locations)

        self.log.info(
            "%% grounded_ice %.2f%%",
            n_grounded_ice_locations * 100.0 / total_records,
        )

        self.log.info(
            "%% floating_ice %.2f%%",
            n_floating_ice_locations * 100.0 / total_records,
        )

        self.log.info(
            "%% icefree_land %.2f%%",
            n_icefree_land_locations * 100.0 / total_records,
        )

        self.log.info(
            "%% non-Greenland land %.2f%%",
            n_non_grn_land_locations * 100.0 / total_records,
        )
        self.log.info("%% ocean %.2f%%", n_ocean_locations * 100.0 / total_records)

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
            if self.greenland_surface_mask is not None:
                self.greenland_surface_mask.clean_up()
            if self.antarctic_surface_mask is not None:
                self.antarctic_surface_mask.clean_up()
        except AttributeError as exc:
            self.log.debug("mask object %s : %s stage %d", exc, self.alg_name, stage)

        # --------------------------------------------------------
