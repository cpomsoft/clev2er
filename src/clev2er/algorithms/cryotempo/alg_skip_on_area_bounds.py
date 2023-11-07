""" clev2er.algorithms.cryotempo.alg_skip_on_area_bounds """
from typing import Tuple

import numpy as np
from codetiming import Timer
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.algorithms.base.base_alg import BaseAlgorithm
from clev2er.utils.masks.masks import Mask  # CPOM Cryosphere area masks

# Similar lines in 2 files, pylint: disable=R0801

# Too many return statements, pylint: disable=R0911
# pylint: disable=too-many-branches


class Algorithm(BaseAlgorithm):
    """Algorithm to do a fast check on whether the l1b file
       is within area bounds of Antarctica and Greenland.
    Depending on the mode (LRM, SIN) we can reject files that are in
    certain lat or lon ranges, as we know they do not pass over
    Greenland or Antarctica

    Also if config['grn_only'] is True and track is in southern
    hemisphere Skip.

    CLEV2ER Algorithm: inherits from BaseAlgorithm

    BaseAlgorithm __init__(config,thislog)
        Args:
            config: Dict[str, Any]: chain configuration dictionary
            thislog: logging.Logger | None: initial logger instance to use or
                                            None (use root logger)
    **Contribution to shared dictionary**

    - shared_dict["lats_nadir"]
    - shared_dict["lons_nadir"]
    - shared_dict["hemisphere"]

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

        try:
            # rectangular mask around Greenland for quick area filtering
            self.greenland_mask = Mask("greenland_area_xylimits_mask")
        except (ValueError, FileNotFoundError, KeyError) as exc:
            self.log.error("%s", exc)

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

        try:
            first_record_lat = l1b.first_record_lat / 1e6
            last_record_lat = l1b.last_record_lat / 1e6
        except AttributeError:
            error_str = "Missing attribute .sir_op_mode in L1b file"
            self.log.error("%s", error_str)
            return (
                False,
                error_str,
            )

        if "instr_mode" not in shared_dict:
            error_str = "instr_mode missing from shared dict"
            self.log.error("%s", error_str)
            return (
                False,
                error_str,
            )

        # If it is LRM then there are are no passes over Ant or Grn that also
        # have first records between 62N and 69S
        if shared_dict["instr_mode"] == "LRM" and (62.0 > first_record_lat > -69.0):
            self.log.info(
                "File Skipping as LRM file outside cryosphere, [%.2fN -> %.2fN]",
                first_record_lat,
                last_record_lat,
            )
            return (
                False,
                (
                    "SKIP_OK, file outside cryosphere, "
                    f"[{first_record_lat:.2f}N -> {last_record_lat:.2f}N]"
                ),
            )

        # If it is SIN then there are are no passes over Ant or Grn that also have first
        # records between 58N and 59S
        if shared_dict["instr_mode"] == "SIN" and (58.0 > first_record_lat > -59.0):
            self.log.info("Skipping file as SIN file outside cryosphere")
            return (
                False,
                (
                    "SKIP_OK, file outside cryosphere, "
                    f"[{first_record_lat:.2f}N -> {last_record_lat:.2f}N]"
                ),
            )

        # Get nadir latitude and longitude from L1b file
        lat_20_ku = l1b["lat_20_ku"][:].data
        lon_20_ku = l1b["lon_20_ku"][:].data % 360.0  # [-180,+180E] -> 0..360E

        southern_hemisphere = False
        northern_hemisphere = False
        for lat in lat_20_ku:
            if lat < -55.0:
                southern_hemisphere = True
                shared_dict["hemisphere"] = "south"
                break
            if lat > 55.0:
                northern_hemisphere = True
                shared_dict["hemisphere"] = "north"
                break

        if northern_hemisphere and southern_hemisphere:
            error_str = "File is in both northern and southern polar areas"
            self.log.error("%s", error_str)
            return (False, error_str)

        if "hemisphere" not in shared_dict:
            error_str = "hemisphere of file could not be determined"
            self.log.error("%s", error_str)
            return (False, error_str)

        self.log.info(
            "File is in %s hemisphere",
            shared_dict["hemisphere"],
        )

        shared_dict["lats_nadir"] = lat_20_ku
        shared_dict["lons_nadir"] = lon_20_ku

        # --------------------------------------------------------------------------------------
        # For northern hemisphere only, we only need passes that go over Greenland, so can skip
        # files not in Mask('greenland_area_xylimits_mask'). This is a rectangular mask for
        # fast masking.
        # --------------------------------------------------------------------------------------

        if northern_hemisphere:
            inmask, _, _ = self.greenland_mask.points_inside(lat_20_ku, lon_20_ku)
            if not np.any(inmask):
                self.log.info(
                    "No locations within Greenland rectangular mask",
                )
                return (
                    False,
                    "SKIP_OK, No locations within Greenland rectangular mask ",
                )

            self.log.info(
                "Locations found within Greenland rectangular mask",
            )

        if "grn_only" in self.config:
            if self.config["grn_only"]:
                if southern_hemisphere:
                    self.log.info(
                        "config:grn_only specified so skipping as not over Greenland",
                    )
                    return (False, "SKIP_OK, grn_only specificed ")

        # Return success (True,'')
        return (True, "")


# No finalize() required by this algorithm
