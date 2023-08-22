""" clev2er.algorithms.cryotempo.alg_cats2008a_tide_correction """

# These imports required by Algorithm template
import logging
import os
from glob import glob
from pathlib import Path  # for extracting file names from paths
from typing import Any, Dict, Tuple

import numpy as np
from codetiming import Timer
from netCDF4 import Dataset  # pylint:disable=E0611

# -------------------------------------------------


# Similar lines in 2 files, pylint: disable=R0801

log = logging.getLogger(__name__)


# Too many return statements, pylint: disable=R0911


class Algorithm:
    """Algorithm to load the corresponding CATS2008a tide correction file
    and extract the tide corrections.

    **Requires from shared dictionary**:

    - `shared_dict["l1b_file_name"]` : str
    - `shared_dict["hemisphere"]` : str
    - `shared_dict["instr_mode"]` : str
    - `shared_dict["num_20hz_records"]` : int

    **Outputs to shared dictionary**:

    - `shared_dict["cats_tide"]` : np.ndarray
    - `shared_dict["cats_tide_required"]` : bool, True if CATS tide has been calculated
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

        shared_dict["cats_tide_required"] = False

        if shared_dict["hemisphere"] == "north":
            self.log.info(
                "no CATS tide correction required for northern hemisphere",
            )
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

        time_string = Path(shared_dict["l1b_file_name"]).name[19:-8]
        year = int(time_string[:4])
        month = int(time_string[4:6])

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

        cats_file = glob(
            f"{self.cats2008a_base_dir}/{year}/{month:02d}/*{time_string}*.nc"
        )
        if len(cats_file) != 1:
            self.log.error(
                "Missing CATS2008a file for timestring %s in %s",
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
            self.log.error("Error reading Dataset %s : %s", cats_file[0], exc)
            return (False, "Error reading Dataset")

        # Check that the CATS2008a has the same number of 20hz records as the L1b file
        if cats_tide.size != shared_dict["num_20hz_records"]:
            self.log.error(
                "CATS2008a tide array length %d should == num L1b 20Hz records %d",
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

        # --------------------------------------------------------
