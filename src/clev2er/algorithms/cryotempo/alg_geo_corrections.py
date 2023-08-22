""" clev2er.algorithms.cryotempo.alg_geo_corrections """

# These imports required by Algorithm template
import logging
from typing import Any, Dict, Tuple

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

    **Contribution to Shared Dict **

        - shared_dict["sum_cor_20_ku"] : sum of geo -corrections

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

        self.log.info("Calculating sum of geo-corrections...")

        # Index of the 1Hz measurement for each 20Hz measurement
        ind_meas_1hz_20_ku = l1b.variables["ind_meas_1hz_20_ku"][:].data

        # Retrieve FES2014b corrections
        try:
            load_tide_20 = shared_dict["fes2014b_corrections"]["load_tide_20"]
            ocean_tide_20 = shared_dict["fes2014b_corrections"]["ocean_tide_20"]
            ocean_tide_eq_20 = shared_dict["fes2014b_corrections"]["ocean_tide_eq_20"]
        except KeyError:
            self.log.error(
                "fes2014b_corrections.load_tide_20 missing from shared_dict",
            )
            return (False, "fes2014b_corrections.load_tide_20 missing from shared_dict")

        # Retrieve CATS2008a tide corrections for SIN mode files in southern hemi
        if shared_dict["cats_tide_required"]:
            try:
                cats_tide = shared_dict["cats_tide"]
            except KeyError:
                self.log.error(
                    "cats_tide missing from shared_dict",
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
            self.log.error("Error reading l1b tide variables : %s", exc)
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
        self.log.info(
            "Number of invalid corrections : %d of %d (%d%%)",
            shared_dict["invalid_corrections_locs"].size,
            sum_cor_20_ku.size,
            100 * shared_dict["invalid_corrections_locs"].size / sum_cor_20_ku.size,
        )

        shared_dict["sum_cor_20_ku"] = sum_cor_20_ku

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
