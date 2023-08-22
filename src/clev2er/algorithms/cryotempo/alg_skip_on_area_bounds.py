""" clev2er.algorithms.cryotempo.alg_skip_on_area_bounds """
import logging
from typing import Any, Dict, Tuple

import numpy as np
from codetiming import Timer
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.utils.masks.masks import Mask  # CPOM Cryosphere area masks

# Similar lines in 2 files, pylint: disable=R0801

log = logging.getLogger(__name__)


# Too many return statements, pylint: disable=R0911


class Algorithm:
    """Algorithm to do a fast check on whether the l1b file
       is within area bounds of Antarctica and Greenland.
    Depending on the mode (LRM, SIN) we can reject files that are in
    certain lat or lon ranges, as we know they do not pass over
    Greenland or Antarctica

    **Contribution to shared dictionary**

    - shared_dict["lats_nadir"]
    - shared_dict["lons_nadir"]
    - shared_dict["hemisphere"]

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

        try:
            # rectangular mask around Greenland for quick area filtering
            self.greenland_mask = Mask("greenland_area_xylimits_mask")
        except (ValueError, FileNotFoundError, KeyError) as exc:
            self.log.error("%s", exc)

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
                "File %d: Skipping as LRM file outside cryosphere, [%.2fN -> %.2fN]",
                filenum,
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
            self.log.info(
                "Skipping file %d as SIN file outside cryosphere",
                filenum,
            )
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
            error_str = f"File {filenum} is in both northern and southern polar areas"
            self.log.error("%s", error_str)
            return (False, error_str)

        if "hemisphere" not in shared_dict:
            error_str = f"hemisphere of file {filenum} could not be determined"
            self.log.error("%s", error_str)
            return (False, error_str)

        self.log.info(
            "File %d is in %s hemisphere",
            filenum,
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
                    "File %d: No locations within Greenland rectangular mask",
                    filenum,
                )
                return (
                    False,
                    "SKIP_OK, No locations within Greenland rectangular mask ",
                )

            self.log.info(
                "File %d: Locations found within Greenland rectangular mask",
                filenum,
            )

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

        # --------------------------------------------------------
