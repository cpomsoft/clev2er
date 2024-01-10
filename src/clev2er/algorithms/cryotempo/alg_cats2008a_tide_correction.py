""" clev2er.algorithms.cryotempo.alg_cats2008a_tide_correction """

# These imports required by Algorithm template
import os
from glob import glob
from pathlib import Path  # for extracting file names from paths
from typing import Tuple

import numpy as np
from codetiming import Timer
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.algorithms.base.base_alg import BaseAlgorithm

# -------------------------------------------------

# Similar lines in 2 files, pylint: disable=R0801
# Too many return statements, pylint: disable=R0911


class Algorithm(BaseAlgorithm):
    """Algorithm to load the corresponding CATS2008a tide correction file
    and extract the tide corrections.

    CLEV2ER Algorithm: inherits from BaseAlgorithm

    BaseAlgorithm __init__(config,thislog)
        Args:
            config: Dict[str, Any]: chain configuration dictionary
            thislog: logging.Logger | None: initial logger instance to use or
                                            None (use root logger)

    **Requires from shared dictionary**:

    - `shared_dict["l1b_file_name"]` : str
    - `shared_dict["hemisphere"]` : str
    - `shared_dict["instr_mode"]` : str
    - `shared_dict["num_20hz_records"]` : int
    - `shared_dict["floating_ice_locations"]` : list[int]
    - `shared_dict["ocean_locations"]` : list[int]

    **Outputs to shared dictionary**:

    - `shared_dict["cats_tide"]` : np.ndarray
    - `shared_dict["cats_tide_required"]` : bool, True if CATS tide has been calculated
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

        """

        self.alg_name = __name__
        self.log.info("Algorithm %s initializing", self.alg_name)

        # Add initialization steps here
        # ------------------------------------------------------------------------------
        # Get the CATS2008a base directory from the config file: tides.cats2008a_base_dir
        # ------------------------------------------------------------------------------

        if "tides" in self.config and "cats2008a_base_dir" in self.config["tides"]:
            self.cats2008a_base_dir = self.config["tides"]["cats2008a_base_dir"]
        else:
            self.log.error("tides.cats2008a_base_dir missing from config file")
            return (False, "tides.cats2008a_base_dir missing from config file")

        # Check that cats2008a_base_dir exists

        if not os.path.isdir(self.cats2008a_base_dir):
            self.log.error("%s does not exist", self.cats2008a_base_dir)
            return (
                False,
                f"tides.cats2008a_base_dir {self.cats2008a_base_dir} not found",
            )

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
        # Perform the algorithm processing, store results that need to passed
        # down the chain in the 'shared_dict' dict
        # -------------------------------------------------------------------

        shared_dict["cats_tide_required"] = False

        if shared_dict["hemisphere"] == "north":
            self.log.info("no CATS tide correction required for northern hemisphere")
            return (
                True,  # we don't want to skip file
                "no CATS tide correction required for northern hemisphere",
            )

        if shared_dict["instr_mode"] != "SIN":
            self.log.debug(
                "no CATS tide correction required for %s mode",
                shared_dict["instr_mode"],
            )
            return (
                True,  # we don't want to skip file
                f'No CATS tide correction required for {shared_dict["instr_mode"]} mode',
            )

        if len(shared_dict["floating_ice_locations"]) == 0:
            if len(shared_dict["ocean_locations"]) == 0:
                self.log.info(
                    "no CATS tide correction required as no floating or ocean measurements",
                )
                return (
                    True,  # we don't want to skip file
                    "no CATS tide correction required as not over ocean or floating ice",
                )

        self.log.info("Getting CATS2008a tide correction file...")

        # -------------------------------------------------------------------
        # Find year and month from L1b file
        # -------------------------------------------------------------------

        # extract the time string and baseline/version: ie 20200101T073130_20200101T073254_E001
        time_string = Path(shared_dict["l1b_file_name"]).name[19:-3]
        year = int(time_string[:4])  # start year
        month = int(time_string[4:6])  # start month

        if (month < 1) or (month > 12) or (year < 2010):
            self.log.error(
                (
                    "Could not determine correct month  or year from L1b file name"
                    "Month found is %d, Year is %d"
                ),
                month,
                year,
            )
            return (False, "Could not determine correct month from L1b file name")

        # Search in <cats2008a_base_dir>/YYYY/MM/*<timestring>*.nc
        # <cats2008a_base_dir> can be either set for
        # L2I: /cpdata/SATS/RA/CRY/L2I/SIN/CATS_tides
        # L1B: /cpdata/SATS/RA/CRY/L1B/CATS2008/SIN
        cats_file = glob(f"{self.cats2008a_base_dir}/{year}/{month:02d}/*{time_string}*.nc")
        if len(cats_file) != 1:
            self.log.error(
                "Missing CATS2008a file for timestring %s in %s",
                time_string,
                f"{self.cats2008a_base_dir}/{year}/{month:02d}",
            )
            return (False, "Missing CATS2008a tide correction file")

        # Open the CATS2008a file
        self.log.info("CATS2008a tide file %s", cats_file[0])
        try:
            nc_cat = Dataset(cats_file[0])
            cats_tide = nc_cat.variables["cats_tide"][:].data
            nc_cat.close()
        except (IOError, KeyError) as exc:
            self.log.error("Error reading Dataset %s : %s", cats_file[0], exc)
            return (False, "Error reading Dataset")

        # Check that the CATS2008a has the same number of 20hz records as the L1b file
        if cats_tide.size != shared_dict["num_20hz_records"]:
            self.log.error(
                "CATS2008a tide array length %d should equal num L1b 20Hz records %d",
                cats_tide.size,
                shared_dict["num_20hz_records"],
            )
            return (False, "CATS2008a tide array length mismatch to L1b record size")

        # The CATS2008a file has np.Nan values where there is no tide correction
        # Replace Nan values in the CATS tide with zero : Do we want to do this??
        np.nan_to_num(cats_tide, copy=False)

        shared_dict["cats_tide"] = cats_tide
        shared_dict["cats_tide_required"] = True

        # Return success (True,'')
        return (True, "")


# Note no Algorithm.finalize() required for this particular algorithm
