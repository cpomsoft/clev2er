""" clev2er.algorithms.cryotempo.alg_waveform_quality """

# These imports required by Algorithm template
from typing import Tuple

import numpy as np
from codetiming import Timer
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.algorithms.base.base_alg import BaseAlgorithm
from clev2er.utils.cs2.waveform_quality.waveform_qc_checks import (
    lrm_waveform_qc_checks,
    sarin_waveform_qc_checks,
)

# -------------------------------------------------
# Similar lines in 2 files, pylint: disable=R0801
# Too many return statements, pylint: disable=R0911


class Algorithm(BaseAlgorithm):
    """**Algorithm to perform waveform quality checks**.

    Separate checks for SARIN and LRM waveforms

    SARIN waveforms : `sarin_waveform_qc_checks()`<br>
        thresholds :<br>
        config["sin_waveform_quality_tests"]["total_power_threshold"]<br>
        config["sin_waveform_quality_tests"]["low_peakiness_threshold"]<br>
        config["sin_waveform_quality_tests"]["low_position_max_power"]<br>
        config["sin_waveform_quality_tests"]["high_position_max_power"]


    LRM waveforms: `lrm_waveform_qc_checks()`<br>
        config["lrm_waveform_quality_tests"]["total_power_threshold"]<br>
        config["lrm_waveform_quality_tests"]["low_peakiness_threshold"]<br>
        config["lrm_waveform_quality_tests"]["high_peakiness_threshold"]<br>

    **Contribution to shared_dict**:<br>
    `shared_dict["waveforms_to_include"]` : nd.array of size num_records containing bool vals
    indicating to include waveform in future analysis based on waveform quality and being
    inside dilated surface mask

    CLEV2ER Algorithm: inherits from BaseAlgorithm

    BaseAlgorithm __init__(config,thislog)
        Args:
            config: Dict[str, Any]: chain configuration dictionary
            thislog: logging.Logger | None: initial logger instance to use or
                                            None (use root logger)
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

        # Get the waveforms from the L1b file
        pwr_waveform_20_ku = l1b.variables["pwr_waveform_20_ku"][:].data

        echo_scale_factor_20_ku = l1b.variables["echo_scale_factor_20_ku"][:].data
        echo_scale_pwr_20_ku = l1b.variables["echo_scale_pwr_20_ku"][:].data

        # Waveform Quality Checks
        self.log.debug(" Performing Waveform QC checks..")

        if shared_dict["instr_mode"] == "SIN":
            noise_power_20_ku = l1b.variables["noise_power_20_ku"][:].data

            # Perform QC checks on the waveforms, returning a boolean array of
            # True (waveform ok), False (waveform not suitable)
            waveforms_ok = sarin_waveform_qc_checks(
                pwr_waveform_20_ku,
                echo_scale_factor_20_ku,
                echo_scale_pwr_20_ku,
                noise_power_20_ku,
                total_power_threshold=float(
                    self.config["sin_waveform_quality_tests"]["total_power_threshold"]
                ),
                low_peakiness_threshold=self.config["sin_waveform_quality_tests"][
                    "low_peakiness_threshold"
                ],
                low_position_max_power=self.config["sin_waveform_quality_tests"][
                    "low_position_max_power"
                ],
                high_position_max_power=self.config["sin_waveform_quality_tests"][
                    "high_position_max_power"
                ],
            )
        else:
            waveforms_ok = lrm_waveform_qc_checks(
                pwr_waveform_20_ku,
                echo_scale_factor_20_ku,
                echo_scale_pwr_20_ku,
                low_peakiness_threshold=self.config["lrm_waveform_quality_tests"][
                    "low_peakiness_threshold"
                ],
                high_peakiness_threshold=self.config["lrm_waveform_quality_tests"][
                    "high_peakiness_threshold"
                ],
                total_power_threshold=float(
                    self.config["lrm_waveform_quality_tests"]["total_power_threshold"]
                ),
            )

        self.log.debug(
            " Waveforms passed QC %d of  %d : %.2f",
            np.count_nonzero(waveforms_ok),
            len(waveforms_ok),
            100.0 * np.count_nonzero(waveforms_ok) / len(waveforms_ok),
        )

        # Only retrack waveforms that pass the QC check and are in the surface mask
        # shared_dict["waveforms_to_include"] : nd.array of size num_records containing bool vals
        # indicating to include waveform in future analysis based on waveform quality and being
        # inside dilated surface mask
        shared_dict["waveforms_to_include"] = (
            waveforms_ok & shared_dict["dilated_surface_mask"]
        )

        # Return success (True,'')
        return (True, "")


# No finalize() required in this algorithm
