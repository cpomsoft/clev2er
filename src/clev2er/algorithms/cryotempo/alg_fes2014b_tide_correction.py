""" clev2er.algorithms.cryotempo.alg_fes2014b_tide_correction """

# These imports required by Algorithm template
import logging
import os
from pathlib import Path  # for extracting file names from paths

from codetiming import Timer
from netCDF4 import Dataset  # pylint:disable=E0611

# -------------------------------------------------


# Similar lines in 2 files, pylint: disable=R0801

log = logging.getLogger(__name__)


# Too many return statements, pylint: disable=R0911


class Algorithm:
    """Algorithm to get FES2014b tide correction for locations in l1b file"""

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

        self.init()

    def init(self) -> None:
        """Algorithm initialization

        Returns: None
        """

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
            self.init()

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

        # -------------------------------------------------------------------
        # Find year and month from L1b file
        # -------------------------------------------------------------------

        time_string = Path(working["l1b_file_name"]).name[19:-8]
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

        # Find the  FES2014b tide correction file in
        # <fes2014b_base_dir>/SIN,LRM/YYYY/MM/<l1b filename>.fes2014b.nc
        # that matches the L1b time string

        # Get the FES2014b base directory from the config file: tides.fes2014b_base_dir

        if "tides" in self.config and "fes2014b_base_dir" in self.config["tides"]:
            fes2014b_base_dir = self.config["tides"]["fes2014b_base_dir"]
        else:
            mplog.error(
                "[f%d] tides.fes2014b_base_dir missing from config file", filenum
            )
            return (False, "tides.fes2014b_base_dir missing from config file")

        # Check that fes2014b_base_dir exists

        if not os.path.isdir(fes2014b_base_dir):
            mplog.error("[f%d] %s does not exist", filenum, fes2014b_base_dir)
            return (False, "tides.fes2014b_base_dir missing from config file")

        fes_filename = (
            f'{fes2014b_base_dir}/{working["instr_mode"]}/{year}'
            f'/{month:02d}/{Path(working["l1b_file_name"]).name[:-3]}.fes2014b.nc'
        )

        # Open the FES2014b file
        try:
            nc_fes = Dataset(fes_filename)
            # Read the FES2014b tide fields (note already at 20hz), units are m
            ocean_tide_20 = nc_fes.variables["ocean_tide_20"][:].data
            ocean_tide_eq_20 = nc_fes.variables["ocean_tide_eq_20"][:].data
            load_tide_20 = nc_fes.variables["load_tide_20"][:].data
            nc_fes.close()
            mplog.info("[f%d] Found FES2014b file %s", filenum, fes_filename)
        except IOError:
            mplog.error("[f%d] Error reading FES2014b file %s", filenum, fes_filename)
            return (False, f"Error reading FES2014b file {fes_filename}")

        # Check that the FES2014b has the same number of 20hz records as the L1b file
        if ocean_tide_20.size != len(working["lats_nadir"]):
            mplog.error(
                "[f%d] FES2014b array length %d not equal to n_20hz_measurements %d",
                filenum,
                ocean_tide_20.size,
                len(working["lats_nadir"]),
            )
            return (False, "FES2014b array length error")

        working["fes2014b_corrections"] = {}
        working["fes2014b_corrections"]["ocean_tide_20"] = ocean_tide_20
        working["fes2014b_corrections"]["ocean_tide_eq_20"] = ocean_tide_eq_20
        working["fes2014b_corrections"]["load_tide_20"] = load_tide_20

        # Return success (True,'')
        return (True, "")

    def finalize(self):
        """Perform final algorithm actions"""
        log.debug("Finalize algorithm %s", self.alg_name)

        # --------------------------------------------------------
        # \/ Add algorithm finalization here \/
        # --------------------------------------------------------

        # --------------------------------------------------------
