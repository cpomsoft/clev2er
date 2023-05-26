""" clev2er.algorithms.cryotempo.alg_surface_type """

# These imports required by Algorithm template
import logging

from codetiming import Timer
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.utils.masks.masks import Mask  # CPOM Cryosphere area masks

# -------------------------------------------------


# Similar lines in 2 files, pylint: disable=R0801

log = logging.getLogger(__name__)


# Too many return statements, pylint: disable=R0911


class Algorithm:
    """Algorithm to find the surface type from Bedmachine v2 (ANT)/v3 (GRN)
    corresponding to L1b records
     Uses
     Bedmachine v2 for Antarctica : https://nsidc.org/data/nsidc-0756/versions/2
                 cpom mask : antarctica_bedmachine_v2_grid_mask
     Bedmachine v3 for Greenland : https://nsidc.org/data/idbmg4
                 cpom mask: greenland_bedmachine_v3_grid_mask
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
     ------------------------------------------------------------------------

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

        # Antarctic surface type mask from BedMachine v2
        try:
            mask_file = config["surface_type_masks"][
                "antarctica_bedmachine_v2_grid_mask"
            ]
        except KeyError as exc:
            log.error(
                "surface_type_masks:antarctica_bedmachine_v2_grid_mask not in config file %s",
                exc,
            )
        self.antarctic_surface_mask = Mask(
            "antarctica_bedmachine_v2_grid_mask",
            mask_path=mask_file,
        )
        # Greenland surface type mask from BedMachine v3
        try:
            mask_file = config["surface_type_masks"][
                "greenland_bedmachine_v3_grid_mask"
            ]
        except KeyError as exc:
            log.error(
                "surface_type_masks:greenland_bedmachine_v3_grid_mask not in config file: %s",
                exc,
            )

        self.greenland_surface_mask = Mask(
            "greenland_bedmachine_v3_grid_mask",
            mask_path=config["surface_type_masks"]["greenland_bedmachine_v3_grid_mask"],
        )

        # --------------------------------------------------------

    @Timer(name=__name__, text="", logger=None)
    def process(self, l1b, working, mplog, filenum):
        """CLEV2ER Algorithm

        Args:
            l1b (Dataset): input l1b file dataset (constant)
            working (dict): working data passed between algorithms
            mplog: multi-processing safe logger to use
            filenum (int) : file number of list of L1b files

        Returns:
            Tuple : (success (bool), failure_reason (str))
            ie
            (False,'error string'), or (True,'')
        """

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
        # down the chain in the 'working' dict
        # -------------------------------------------------------------------

        working["test"] = 0

        # Return success (True,'')
        return (True, "")

    def finalize(self):
        """Perform final algorithm actions"""
        log.debug("Finalize algorithm %s", self.alg_name)

        # --------------------------------------------------------
        # \/ Add algorithm finalization here \/
        # --------------------------------------------------------

        # --------------------------------------------------------
