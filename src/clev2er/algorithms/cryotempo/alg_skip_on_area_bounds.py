""" clev2er.algorithms.cryotempo.alg_skip_on_area_bounds """
import logging

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

        # For multi-processing we do the init() in the Algorithm.process() function
        # This avoids pickling the init() data which is very slow
        if config["chain"]["use_multi_processing"]:
            return

        self.init(log, 0)

        # --------------------------------------------------------
        # \/ Add algorithm initialization here \/
        # --------------------------------------------------------

        # --------------------------------------------------------

    def init(self, mplog, filenum) -> None:
        """Algorithm initialization
        Args:
            mplog (logger.log) : log instance to use
            filenum (int): file number being processed
        Returns: None
        """

        try:
            # rectangular mask around Greenland for quick area filtering
            self.greenland_mask = Mask("greenland_area_xylimits_mask")
        except (ValueError, FileNotFoundError, KeyError) as exc:
            mplog.error("[f%d] %s", filenum, exc)

    @Timer(name=__name__, text="", logger=None)
    def process(
        self, l1b, shared_dict, mplog, filenum
    ):  # too-many-branches, pylint: disable=R0912
        """CLEV2ER Algorithm

        Args:
            l1b (Dataset): input l1b file dataset (constant)
            shared_dict (dict): shared_dict data passed between algorithms
            mplog: multi-processing safe logger to use
            filenum (int) : file number of list of L1b files

        Returns:
            Tuple : (success (bool), failure_reason (str))
            ie
            (False,'error string'), or (True,'')
        """

        # When using multi-processing it is faster to initialize the algorithm
        # within each Algorithm.process(), rather than once in the main process's
        # Algorithm.__init__().
        # This avoids having to pickle the initialized data arrays (which is extremely slow)
        if self.config["chain"]["use_multi_processing"]:
            self.init(mplog, filenum)

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
        # down the chain in the 'shared_dict' dict
        # -------------------------------------------------------------------

        try:
            first_record_lat = l1b.first_record_lat / 1e6
            last_record_lat = l1b.last_record_lat / 1e6
        except AttributeError:
            error_str = "Missing attribute .sir_op_mode in L1b file"
            mplog.error("[f%d] %s", filenum, error_str)
            return (
                False,
                error_str,
            )

        if "instr_mode" not in shared_dict:
            error_str = "instr_mode missing from shared dict"
            mplog.error("[f%d] %s", filenum, error_str)
            return (
                False,
                error_str,
            )

        # If it is LRM then there are are no passes over Ant or Grn that also
        # have first records between 62N and 69S
        if shared_dict["instr_mode"] == "LRM" and (62.0 > first_record_lat > -69.0):
            mplog.info(
                "[f%d] File %d: Skipping as LRM file outside cryosphere, [%.2fN -> %.2fN]",
                filenum,
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
            mplog.info(
                "[f%d] Skipping file %d as SIN file outside cryosphere",
                filenum,
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
            mplog.error("[f%d] %s", filenum, error_str)
            return (False, error_str)

        if "hemisphere" not in shared_dict:
            error_str = f"hemisphere of file {filenum} could not be determined"
            mplog.error("[f%d] %s", filenum, error_str)
            return (False, error_str)

        mplog.info(
            "[f%d] File %d is in %s hemisphere",
            filenum,
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
                mplog.info(
                    "[f%d] File %d: No locations within Greenland rectangular mask",
                    filenum,
                    filenum,
                )
                return (
                    False,
                    "SKIP_OK, No locations within Greenland rectangular mask ",
                )

            mplog.info(
                "[f%d] File %d: Locations found within Greenland rectangular mask",
                filenum,
                filenum,
            )

        # Return success (True,'')
        return (True, "")

    def finalize(self):
        """Perform final algorithm actions"""
        log.debug("Finalize algorithm %s", self.alg_name)

        # --------------------------------------------------------
        # \/ Add algorithm finalization here \/
        # --------------------------------------------------------

        # --------------------------------------------------------
