""" clev2er.algorithms.cryotempo.alg_waveform_quality """

# These imports required by Algorithm template
import logging
from typing import Any, Dict, Tuple

import numpy as np
from codetiming import Timer
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.utils.cs2.waveform_quality.waveform_qc_checks import (
    lrm_waveform_qc_checks,
    sarin_waveform_qc_checks,
)

# -------------------------------------------------


# Similar lines in 2 files, pylint: disable=R0801

log = logging.getLogger(__name__)


# Too many return statements, pylint: disable=R0911


class Algorithm:
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

        # Get the waveforms from the L1b file
        pwr_waveform_20_ku = l1b.variables["pwr_waveform_20_ku"][:].data

        echo_scale_factor_20_ku = l1b.variables["echo_scale_factor_20_ku"][:].data
        echo_scale_pwr_20_ku = l1b.variables["echo_scale_pwr_20_ku"][:].data

        # Waveform Quality Checks
        self.log.debug("Performing Waveform QC checks..")

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
            "Waveforms passed QC %d of  %d : %.2f",
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
