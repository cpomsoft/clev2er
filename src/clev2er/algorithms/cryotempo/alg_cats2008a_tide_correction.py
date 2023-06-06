""" clev2er.algorithms.cryotempo.alg_cats2008a_tide_correction """

# These imports required by Algorithm template
import logging
import os
from glob import glob
from pathlib import Path  # for extracting file names from paths

import numpy as np
from codetiming import Timer
from netCDF4 import Dataset  # pylint:disable=E0611

# -------------------------------------------------


# Similar lines in 2 files, pylint: disable=R0801

log = logging.getLogger(__name__)


# Too many return statements, pylint: disable=R0911


class Algorithm:
    """Algorithm to"""

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

    def init(self, mplog: logging.Logger, filenum: int) -> tuple[bool, str]:
        """Algorithm initialization

        Args:
            mplog (logging.Logger): log instance to use
            filenum (int): file number being processed

        Returns: (bool,str) : success or failure, error string
        """
        # ------------------------------------------------------------------------------
        # Get the CATS2008a base directory from the config file: tides.cats2008a_base_dir
        # ------------------------------------------------------------------------------

        if "tides" in self.config and "cats2008a_base_dir" in self.config["tides"]:
            self.cats2008a_base_dir = self.config["tides"]["cats2008a_base_dir"]
        else:
            mplog.error(
                "[f%d] tides.cats2008a_base_dir missing from config file", filenum
            )
            return (False, "tides.cats2008a_base_dir missing from config file")

        # Check that cats2008a_base_dir exists

        if not os.path.isdir(self.cats2008a_base_dir):
            mplog.error("[f%d] %s does not exist", filenum, self.cats2008a_base_dir)
            return (
                False,
                f"tides.cats2008a_base_dir {self.cats2008a_base_dir} not found",
            )

        return (True, "")

    @Timer(name=__name__, text="", logger=None)
    def process(
        self, l1b: Dataset, shared_dict: dict, mplog: logging.Logger, filenum: int
    ) -> tuple[bool, str]:
        """Algorithm to retrieve the CATS2008a Antarctic tide correction for l1b file

        Args:
            l1b (Dataset): input l1b file dataset (constant)
            shared_dict (dict): shared_dict data passed between algorithms
            mplog (logging.Logger): multi-processing safe logger to use
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
            rval, error_str = self.init(mplog, filenum)
            if not rval:
                return (rval, error_str)

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
        if shared_dict["hemisphere"] == "north":
            mplog.debug(
                "[f%d] no CATS tide correction required for northern hemisphere",
                filenum,
            )
            return (
                True,  # we don't want to skip file
                "no CATS tide correction required for northern hemisphere",
            )

        if shared_dict["instr_mode"] != "SIN":
            mplog.debug(
                "[f%d] no CATS tide correction required for %s mode",
                filenum,
                shared_dict["instr_mode"],
            )
            return (
                True,  # we don't want to skip file
                f'No CATS tide correction required for {shared_dict["instr_mode"]} mode',
            )

        mplog.info("[f%d] Getting CATS2008a tide correction file...", filenum)

        # -------------------------------------------------------------------
        # Find year and month from L1b file
        # -------------------------------------------------------------------

        time_string = Path(shared_dict["l1b_file_name"]).name[19:-8]
        year = int(time_string[:4])
        month = int(time_string[4:6])

        if (month < 1) or (month > 12) or (year < 2010):
            mplog.error(
                (
                    "[f%d] Could not determine correct month  or year from L1b file name"
                    "Month found is %d, Year is %d"
                ),
                filenum,
                month,
                year,
            )
            return (False, "Could not determine correct month from L1b file name")

        cats_file = glob(
            f"{self.cats2008a_base_dir}/{year}/{month:02d}/*{time_string}*.nc"
        )
        if len(cats_file) != 1:
            mplog.error(
                "[f%d] Missing CATS2008a file for timestring %s in %s",
                filenum,
                time_string,
                self.cats2008a_base_dir,
            )
            return (False, "Missing CATS2008a tide correction file")

        # Open the CATS2008a file
        try:
            nc_cat = Dataset(cats_file[0])
            cats_tide = nc_cat.variables["cats_tide"][:].data
            nc_cat.close()
        except (IOError, KeyError) as exc:
            mplog.error(
                "[f%d] Error reading Dataset %s : %s", filenum, cats_file[0], exc
            )
            return (False, "Error reading Dataset")

        # Check that the CATS2008a has the same number of 20hz records as the L1b file
        if cats_tide.size != shared_dict["num_20hz_records"]:
            mplog.error(
                "[f%d] CATS2008a tide array length %d should equal"
                "num L1b 20Hz records %d",
                filenum,
                cats_tide.size,
                shared_dict["num_20hz_records"],
            )
            return (False, "CATS2008a tide array length mismatch to L1b record size")

        # The CATS2008a file has np.Nan values where there is no tide correction
        # Replace Nan values in the CATS tide with zero : Do we want to do this??
        np.nan_to_num(cats_tide, copy=False)

        shared_dict["cats_tide"] = cats_tide

        # Return success (True,'')
        return (True, "")

    def finalize(self):
        """Perform final algorithm actions"""
        log.debug("Finalize algorithm %s", self.alg_name)

        # --------------------------------------------------------
        # \/ Add algorithm finalization here \/
        # --------------------------------------------------------

        # --------------------------------------------------------
