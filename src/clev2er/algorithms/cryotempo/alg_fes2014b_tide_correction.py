""" clev2er.algorithms.cryotempo.alg_fes2014b_tide_correction """

# These imports required by Algorithm template
import os
from pathlib import Path  # for extracting file names from paths
from typing import Tuple

from codetiming import Timer
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.algorithms.base.base_alg import BaseAlgorithm

# -------------------------------------------------


# Similar lines in 2 files, pylint: disable=R0801
# Too many return statements, pylint: disable=R0911


class Algorithm(BaseAlgorithm):
    """Algorithm to get FES2014b tide correction for locations in l1b file

    CLEV2ER Algorithm: inherits from BaseAlgorithm

    BaseAlgorithm __init__(config,thislog)
        Args:
            config: Dict[str, Any]: chain configuration dictionary
            thislog: logging.Logger | None: initial logger instance to use or
                                            None (use root logger)

    **Contribution to Shared Dict **
        - shared_dict["fes2014b_corrections"]["ocean_tide_20"] : np.ndarray
        - shared_dict["fes2014b_corrections"]["ocean_tide_eq_20"] : np.ndarray
        - shared_dict["fes2014b_corrections"]["load_tide_20"] : np.ndarray

    """

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

        # Get the FES2014b base directory from the config file: tides.fes2014b_base_dir

        if "tides" in self.config and "fes2014b_base_dir" in self.config["tides"]:
            self.fes2014b_base_dir = self.config["tides"]["fes2014b_base_dir"]
        else:
            self.log.error("tides.fes2014b_base_dir missing from config file")
            return (False, "tides.fes2014b_base_dir missing from config file")

        # Check that fes2014b_base_dir exists

        if not os.path.isdir(self.fes2014b_base_dir):
            self.log.error("%s does not exist", self.fes2014b_base_dir)
            return (
                False,
                f"tides.fes2014b_base_dir {self.fes2014b_base_dir} not found",
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

        # Find the  FES2014b tide correction file in
        # <fes2014b_base_dir>/SIN,LRM/YYYY/MM/<l1b filename>.fes2014b.nc
        # that matches the L1b time string

        fes_filename = (
            f'{self.fes2014b_base_dir}/{shared_dict["instr_mode"]}/{year}'
            f'/{month:02d}/{Path(shared_dict["l1b_file_name"]).name[:-3]}.fes2014b.nc'
        )

        # Open the FES2014b file
        try:
            nc_fes = Dataset(fes_filename)
            # Read the FES2014b tide fields (note already at 20hz), units are m
            ocean_tide_20 = nc_fes.variables["ocean_tide_20"][:].data
            ocean_tide_eq_20 = nc_fes.variables["ocean_tide_eq_20"][:].data
            load_tide_20 = nc_fes.variables["load_tide_20"][:].data
            nc_fes.close()
            self.log.info("Found FES2014b file %s", fes_filename)
        except IOError:
            self.log.error("Error reading FES2014b file %s", fes_filename)
            return (False, f"Error reading FES2014b file {fes_filename}")

        # Check that the FES2014b has the same number of 20hz records as the L1b file
        if ocean_tide_20.size != shared_dict["num_20hz_records"]:
            self.log.error(
                "FES2014b array length %d not equal to n_20hz_measurements %d",
                ocean_tide_20.size,
                shared_dict["num_20hz_records"],
            )
            return (False, "FES2014b array length error")

        shared_dict["fes2014b_corrections"] = {}
        shared_dict["fes2014b_corrections"]["ocean_tide_20"] = ocean_tide_20
        shared_dict["fes2014b_corrections"]["ocean_tide_eq_20"] = ocean_tide_eq_20
        shared_dict["fes2014b_corrections"]["load_tide_20"] = load_tide_20

        # Return success (True,'')
        return (True, "")


# Note no Algorithm.finalize() required for this particular algorithm
