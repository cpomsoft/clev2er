""" clev2er.algorithms.cryotempo.alg_geo_corrections """

# These imports required by Algorithm template
import logging

import numpy as np
from codetiming import Timer
from netCDF4 import Dataset  # pylint:disable=E0611

# -------------------------------------------------


# Similar lines in 2 files, pylint: disable=R0801

log = logging.getLogger(__name__)


# Too many return statements, pylint: disable=R0911
# Too many locals, pylint: disable=R0914
# Too many branches, pylint: disable=R0912


class Algorithm:
    """**Algorithm to calculate geophysical corrections for a CS2 l1b file**

    1b) Calculate sum of geo-corrections
    Floating ice/ocean: DRY + WET + DAC + GIM + OT + LPEOT + OLT + SET + GPT
    Land ice:           DRY + WET +       GIM +              OLT + SET + GPT

    Sum of geo -corrections returned in `shared_dict["sum_cor_20_ku"]`

    """

    def __init__(self, config) -> None:
        """initializes the Algorithm

        Args:
            config (dict): configuration dictionary

        Returns: None
        """
        self.alg_name = __name__
        self.config = config

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
        mplog.debug(
            "[f%d] Initializing algorithm %s",
            filenum,
            self.alg_name,
        )

        return (True, "")

    @Timer(name=__name__, text="", logger=None)
    def process(
        self, l1b: Dataset, shared_dict: dict, mplog: logging.Logger, filenum: int
    ) -> tuple[bool, str]:
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

        mplog.info("[f%d] Calculating sum of geo-corrections...", filenum)

        # Index of the 1Hz measurement for each 20Hz measurement
        ind_meas_1hz_20_ku = l1b.variables["ind_meas_1hz_20_ku"][:].data

        # Retrieve FES2014b corrections
        try:
            load_tide_20 = shared_dict["fes2014b_corrections"]["load_tide_20"]
            ocean_tide_20 = shared_dict["fes2014b_corrections"]["ocean_tide_20"]
            ocean_tide_eq_20 = shared_dict["fes2014b_corrections"]["ocean_tide_eq_20"]
        except KeyError:
            mplog.error(
                "[f%d] fes2014b_corrections.load_tide_20 missing from shared_dict",
                filenum,
            )
            return (False, "fes2014b_corrections.load_tide_20 missing from shared_dict")

        # Retrieve CATS2008a tide corrections for SIN mode files in southern hemi
        if shared_dict["hemisphere"] == "south" and shared_dict["instr_mode"] == "SIN":
            try:
                cats_tide = shared_dict["cats_tide"]
            except KeyError:
                mplog.error(
                    "[f%d] cats_tide missing from shared_dict",
                    filenum,
                )
                return (False, "cats_tide missing from shared_dict")
        else:
            cats_tide = None

        # Read in common geo-corrections at 1hz from L1b.
        # Note OLT (load_tide_20) is replaced by FES2014b (load_tide_20)
        try:
            mod_dry_tropo_cor_20 = l1b.variables["mod_dry_tropo_cor_01"][:].data[
                ind_meas_1hz_20_ku
            ]  # DRY
            mod_wet_tropo_cor_20 = l1b.variables["mod_wet_tropo_cor_01"][:].data[
                ind_meas_1hz_20_ku
            ]  # WET
            iono_cor_gim_20 = l1b.variables["iono_cor_gim_01"][:].data[
                ind_meas_1hz_20_ku
            ]  # GIM
            solid_earth_tide_20 = l1b.variables["solid_earth_tide_01"][:].data[
                ind_meas_1hz_20_ku
            ]  # SET
            pole_tide_20 = l1b.variables["pole_tide_01"][:].data[
                ind_meas_1hz_20_ku
            ]  # GPT
        except KeyError as exc:
            mplog.error("[f%d] Error reading l1b tide variables : %s", filenum, exc)
            return (False, "Error reading l1b tide variables")

        # Add corrections for DRY + WET + GIM + OLT (from FES2014b) + SET + GPT
        sum_cor_20_ku = (
            mod_dry_tropo_cor_20
            + mod_wet_tropo_cor_20
            + iono_cor_gim_20
            + load_tide_20
            + solid_earth_tide_20
            + pole_tide_20
        )

        # If we have ocean or floating ice then we need to also include ocean tide
        # corrections DAC, OT, LPEOT
        # Over the southern hemisphere we will use CATS2008a

        if (
            shared_dict["floating_ice_locations"].size
            + shared_dict["ocean_locations"].size
        ) > 0:
            # Load DAC
            hf_fluct_total_cor_20 = l1b.variables["hf_fluct_total_cor_01"][:].data[
                ind_meas_1hz_20_ku
            ]  # DAC

            if shared_dict["hemisphere"] == "north":
                if shared_dict["floating_ice_locations"].size > 0:
                    sum_cor_20_ku[shared_dict["floating_ice_locations"]] += (
                        hf_fluct_total_cor_20[shared_dict["floating_ice_locations"]]
                        + ocean_tide_eq_20[shared_dict["floating_ice_locations"]]
                        + ocean_tide_20[shared_dict["floating_ice_locations"]]
                    )
                if shared_dict["ocean_locations"].size > 0:
                    sum_cor_20_ku[shared_dict["ocean_locations"]] += (
                        hf_fluct_total_cor_20[shared_dict["ocean_locations"]]
                        + ocean_tide_eq_20[shared_dict["ocean_locations"]]
                        + ocean_tide_20[shared_dict["ocean_locations"]]
                    )
        # ----------------------------------------------------------------------------

        if shared_dict["hemisphere"] == "south" and shared_dict["instr_mode"] == "SIN":
            if shared_dict["floating_ice_locations"].size > 0:
                # Apply the tide corrections, just over floating ice
                sum_cor_20_ku[shared_dict["floating_ice_locations"]] += (
                    hf_fluct_total_cor_20[shared_dict["floating_ice_locations"]]
                    + cats_tide[shared_dict["floating_ice_locations"]]
                )
            if shared_dict["ocean_locations"].size > 0:
                # Apply the tide corrections, just over floating ice
                sum_cor_20_ku[shared_dict["ocean_locations"]] += (
                    hf_fluct_total_cor_20[shared_dict["ocean_locations"]]
                    + cats_tide[shared_dict["ocean_locations"]]
                )

        # Find how many correction locations are invalid (nan)
        shared_dict["invalid_corrections_locs"] = np.nonzero(np.isnan(sum_cor_20_ku))[0]
        mplog.info(
            "[f%d] Number of invalid corrections : %d of %d (%d%%)",
            filenum,
            shared_dict["invalid_corrections_locs"].size,
            sum_cor_20_ku.size,
            100 * shared_dict["invalid_corrections_locs"].size / sum_cor_20_ku.size,
        )

        shared_dict["sum_cor_20_ku"] = sum_cor_20_ku

        # Return success (True,'')
        return (True, "")

    def finalize(self):
        """Perform final algorithm actions"""
        log.debug("Finalize algorithm %s", self.alg_name)

        # --------------------------------------------------------
        # \/ Add algorithm finalization here \/
        # --------------------------------------------------------

        # --------------------------------------------------------
