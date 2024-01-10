""" clev2er.algorithms.cryotempo.alg_geo_corrections """

# These imports required by Algorithm template
from typing import Tuple

import numpy as np
from codetiming import Timer
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.algorithms.base.base_alg import BaseAlgorithm

# -------------------------------------------------

# Similar lines in 2 files, pylint: disable=R0801
# Too many return statements, pylint: disable=R0911
# Too many locals, pylint: disable=R0914
# Too many branches, pylint: disable=R0912


class Algorithm(BaseAlgorithm):
    """**Algorithm to calculate geophysical corrections for a CS2 l1b file**

    1b) Calculate sum of geo-corrections
    Floating ice/ocean: DRY + WET + DAC + GIM + OT + LPEOT + OLT + SET + GPT
    Land ice:           DRY + WET +       GIM +              OLT + SET + GPT

    CLEV2ER Algorithm: inherits from BaseAlgorithm

    BaseAlgorithm __init__(config,thislog)
        Args:
            config: Dict[str, Any]: chain configuration dictionary
            thislog: logging.Logger | None: initial logger instance to use or
                                            None (use root logger)

    **Contribution to Shared Dict **

        - shared_dict["sum_cor_20_ku"] : sum of geo -corrections

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
            iono_cor_gim_20 = l1b.variables["iono_cor_gim_01"][:].data[ind_meas_1hz_20_ku]  # GIM
            solid_earth_tide_20 = l1b.variables["solid_earth_tide_01"][:].data[
                ind_meas_1hz_20_ku
            ]  # SET
            pole_tide_20 = l1b.variables["pole_tide_01"][:].data[ind_meas_1hz_20_ku]  # GPT
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

        if (shared_dict["floating_ice_locations"].size + shared_dict["ocean_locations"].size) > 0:
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

    # No finalize() required by this algorithm
