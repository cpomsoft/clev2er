""" clev2er.algorithms.cryotempo.alg_backscatter"""

# These imports required by Algorithm template
import logging
from typing import Any, Dict, Tuple

from codetiming import Timer  # used to time the Algorithm.process() function
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.algorithms.base.base_alg import BaseAlgorithm
from clev2er.utils.cs2.backscatter.backscatter import (
    compute_backscatter,
    cs_counts_to_watts,
)

# too-many-locals, pylint: disable=R0914

# -------------------------------------------------

# pylint config
# Similar lines in 2 files, pylint: disable=R0801
# Too many return statements, pylint: disable=R0911


class Algorithm(BaseAlgorithm):
    """**Algorithm to Calculate Backscatter from CS2 L1b dataset**.

    BaseAlgorithm __init__(config,thislog)
        Args:
            config: Dict[str, Any]: chain configuration dictionary
            thislog: logging.Logger | None: initial logger instance to use or
                                            None (use root logger)

    **Contribution to shared_dict**
        - shared_dict["sig0_20_ku"] (np.ndarray) : array of backscatter values
    **Required from other algorithms**
    -   shared_dict["pwr_at_rtrk_point"]
    -   shared_dict["range_cor_20_ku"]

    """

    def __init__(self, config: Dict[str, Any], thislog: logging.Logger | None) -> None:
        self.alg_name = __name__
        super().__init__(config, thislog)

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
        """CLEV2ER Algorithm

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

        This is required to support logging during multi-processing
        """

        # Required to test L1b and support MP:
        success, error_str = self.process_setup(l1b)
        if not success:
            return (False, error_str)

        # -------------------------------------------------------------------
        # Perform the algorithm processing, store results that need to passed
        # down the chain in the 'shared_dict' dict
        # -------------------------------------------------------------------

        # Get the data we need from the shared_dict
        pwr_at_rtrk_point = shared_dict["pwr_at_rtrk_point"]
        range_cor_20_ku = shared_dict["range_cor_20_ku"]

        # Get the data we need from the l1b
        echo_scale_factor_20_ku = l1b.variables["echo_scale_factor_20_ku"][:].data
        echo_scale_pwr_20_ku = l1b.variables["echo_scale_pwr_20_ku"][:].data
        transmit_pwr_20_ku = l1b.variables["transmit_pwr_20_ku"][:].data
        pitch_deg = l1b.variables["off_nadir_pitch_angle_str_20_ku"][:].data
        roll_deg = l1b.variables["off_nadir_roll_angle_str_20_ku"][:].data

        # Convert the count value at the retracking point to watts

        rtrk_pow_w = cs_counts_to_watts(
            pwr_at_rtrk_point, echo_scale_factor_20_ku, echo_scale_pwr_20_ku
        )

        if shared_dict["instr_mode"] == "LRM":
            sigma_bias = self.config["backscatter"]["sigma_bias_lrm"]
        elif shared_dict["instr_mode"] == "SIN":
            sigma_bias = self.config["backscatter"]["sigma_bias_sin"]
        else:
            self.log.error(
                "mode %s not supported by alg_backscatter algorithm",
                shared_dict["instr_mode"],
            )
            return (
                False,
                f'instrument mode {shared_dict["instr_mode"]} must be LRM or SIN : ',
            )

        sig0_20_ku = compute_backscatter(
            rtrk_pow_w,
            range_cor_20_ku,
            roll_deg,
            pitch_deg,
            transmit_pwr_20_ku,
            sigma_bias=sigma_bias,
        )

        # Save algorithm result in shared dictionary
        shared_dict["sig0_20_ku"] = sig0_20_ku

        # Return success (True,'')
        return (True, "")

    # Note no Algorithm.finalize() required for this particular algorithm
