""" clev2er.algorithms.cryotempo.alg_backscatter"""

# These imports required by Algorithm template
import logging
from typing import Any, Dict, Tuple

from codetiming import Timer  # used to time the Algorithm.process() function
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.utils.cs2.backscatter.backscatter import (
    compute_backscatter,
    cs_counts_to_watts,
)

# too-many-locals, pylint: disable=R0914

# -------------------------------------------------

# pylint config
# Similar lines in 2 files, pylint: disable=R0801
# Too many return statements, pylint: disable=R0911

log = logging.getLogger(__name__)


class Algorithm:
    """**Algorithm to Calculate Backscatter from CS2 L1b dataset**.

    **Contribution to shared_dict**
        - shared_dict["sig0_20_ku"] (np.ndarray) : array of backscatter values
    **Required from other algorithms**
    -   shared_dict["pwr_at_rtrk_point"]
    -   shared_dict["range_cor_20_ku"]

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

        shared_dict["sig0_20_ku"] = sig0_20_ku

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
