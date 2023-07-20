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

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Runs init() if not in multi-processing mode
        Args:
            config (dict): configuration dictionary

        Returns:
            None
        """
        self.alg_name = __name__
        self.config = config

        # For multi-processing we do the init() in the Algorithm.process() function
        # This avoids pickling the init() data which is very slow
        if config["chain"]["use_multi_processing"]:
            return

        _, _ = self.init(log, 0)

    def init(self, mplog: logging.Logger, filenum: int) -> Tuple[bool, str]:
        """Algorithm initialization template

        Args:
            mplog (logging.Logger): log instance to use
            filenum (int): file number being processed

        Returns:
            (bool,str) : success or failure, error string
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
    ) -> Tuple[bool, str]:
        """CLEV2ER Algorithm

        Args:
            l1b (Dataset): input l1b file dataset (constant)
            shared_dict (dict): shared_dict data passed between algorithms
            mplog (logging.Logger): multi-processing safe logger to use
            filenum (int) : file number of list of L1b files

        Returns:
            Tuple : (success (bool), failure_reason (str))
            ie
            (False,'error string'), or (True,'')

        **IMPORTANT NOTE:** when logging within the Algorithm.process() function you must use
        the mplog logger with a filenum as an argument:

        `mplog.error("[f%d] your message",filenum)`

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

        mplog.info(
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
            mplog.error(
                "[f%d] mode %s not supported by alg_backscatter algorithm",
                filenum,
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

    def finalize(self):
        """Perform final algorithm actions"""
        log.debug("Finalize algorithm %s", self.alg_name)

        # --------------------------------------------------------
        # \/ Add algorithm finalization here \/
        # --------------------------------------------------------

        # --------------------------------------------------------
