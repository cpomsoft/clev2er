""" clev2er.algorithms.cryotempo.alg_retrack"""

# These imports required by Algorithm template
import logging
from typing import Any, Dict, Tuple

import numpy as np
from codetiming import Timer  # used to time the Algorithm.process() function
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.utils.cs2.retrackers.cs2_sin_max_coherence_retracker import (
    retrack_cs2_sin_max_coherence,
)
from clev2er.utils.cs2.retrackers.cs2_tcog_retracker import (
    retrack_tcog_waveforms_cs2,
)

# too-many-locals, pylint: disable=R0914

# -------------------------------------------------

# pylint config
# Similar lines in 2 files, pylint: disable=R0801
# Too many return statements, pylint: disable=R0911

log = logging.getLogger(__name__)


class Algorithm:
    """**Algorithm to retrack CS2 waveforms**

    **For SARin** waveforms:
    `clev2er.utils.cs2.retrackers.cs2_sin_max_coherence_retracker` called<br>
    **For LRM** waveforms: `cs2_tcog_retracker()` called

    Tuning thresholds are set in config.

    **Contribution to shared dictionary**

    - shared_dict["ind_wfm_retrack_20_ku"]: (np.ndarray) closest bin number to retracking point(s)
    - shared_dict["pwr_at_rtrk_point"] : (np.ndarray) waveform power at the retracking point
    - shared_dict["range_cor_20_ku"] : (np.ndarray) corrected range (retracked and geo-corrected)
    - shared_dict["num_retracker_failures"] (int) : number of retracker failures
    - shared_dict["percent_retracker_failure"]  (float) : percentage of retracker failures

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
        if self.config["chain"]["use_multi_processing"]:
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
        """CLEV2ER Algorithm to perform retracking

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

        # Get the waveforms from the L1b file
        pwr_waveform_20_ku = l1b.variables["pwr_waveform_20_ku"][:].data
        waveforms_to_include = shared_dict["waveforms_to_include"]
        n_waveforms_to_include = np.count_nonzero(waveforms_to_include)

        if shared_dict["instr_mode"] == "SIN":
            coherence_waveform_20_ku = l1b.variables["coherence_waveform_20_ku"][:].data
            ref_bin_index = self.config["mc_retracker"]["ref_bin_ind_sin"]

            mplog.info("[f%d] Retracking SIN waveform using MC Retracker..", filenum)
            (
                dr_bin,
                dr_meters,
                _,  # leading_edge_start
                _,  # leading_edge_stop
                pwr_at_rtrk_point,
                n_retrack_failed,
                _,  # retracker_flags
            ) = retrack_cs2_sin_max_coherence(
                plot_flag=self.config["mc_retracker"]["show_plots"],
                waveforms=pwr_waveform_20_ku,  # input waveforms
                coherence=coherence_waveform_20_ku,  # coherence waveform (SIN only)
                ref_bin_ind_sin=self.config["mc_retracker"]["ref_bin_ind_sin"],
                wf_oversampling_factor=self.config["mc_retracker"][
                    "wf_oversampling_factor"
                ],  # Waveform oversampling factor
                noise_sample_limit=self.config["mc_retracker"][
                    "noise_sample_limit"
                ],  # maximum bin used to compute noise statistics
                noise_threshold=self.config["mc_retracker"][
                    "noise_threshold"
                ],  # if mean amplitude in noise bins exceeds threshold then reject waveform
                savitsky_golay_width=self.config["mc_retracker"][
                    "savitsky_golay_width"
                ],  # Width of Savitsky-Golay waveform smoothing window
                savitsky_golay_poly_order=self.config["mc_retracker"][
                    "savitsky_golay_poly_order"
                ],  # Savitsky-Golay polynomial order
                le_id_threshold=self.config["mc_retracker"][
                    "le_id_threshold"
                ],  # power must exceed thermal noise by this amount to be identified as
                # leading edge
                le_dp_threshold=self.config["mc_retracker"][
                    "le_dp_threshold"
                ],  # define threshold on normalised amplitude change which is required to
                # be accepted as lead edge
                coherence_smoothing_width=self.config["mc_retracker"][
                    "coherence_smoothing_width"
                ],  # define coherence boxcar average smoothing width
                include_measurements_array=waveforms_to_include,
            )  # if not None, pass a boolean array to indicate which waveforms to retrack

            # calculate the closest  bin number to the retracking point : units count

            ind_wfm_retrack_20_ku = 512.0 + np.array(dr_bin)

        else:
            log.info("Retracking LRM waveform using TCOG Retracker..")

            ref_bin_index = self.config["tcog_retracker"]["ref_bin_ind_lrm"]

            (
                dr_bin,
                dr_meters,
                _,  # leading_edge_start
                _,  # leading_edge_stop
                pwr_at_rtrk_point,
                n_retrack_failed,
                _,  # retracker_flags
            ) = retrack_tcog_waveforms_cs2(
                plot_flag=self.config["tcog_retracker"]["show_plots"],
                waveforms=pwr_waveform_20_ku,  # input waveforms
                retrack_threshold_lrm=self.config["tcog_retracker"][
                    "retrack_threshold_lrm"
                ],
                ref_bin_ind_lrm=self.config["tcog_retracker"][
                    "ref_bin_ind_lrm"
                ],  # from CS2 Baseline-D User Manual, p36;
                noise_sample_limit=self.config["tcog_retracker"][
                    "noise_sample_limit"
                ],  # maximum bin used to compute noise statistics
                savitsky_golay_width=self.config["tcog_retracker"][
                    "savitsky_golay_width"
                ],  # Width of Savitsky-Golay waveform smoothing window
                savitsky_golay_poly_order=self.config["tcog_retracker"][
                    "savitsky_golay_poly_order"
                ],  # Savitsky-Golay polynomial order
                wf_oversampling_factor=self.config["tcog_retracker"][
                    "wf_oversampling_factor"
                ],  # Waveform oversampling factor
                noise_threshold=self.config["tcog_retracker"][
                    "noise_threshold"
                ],  # if mean amplitude in noise bins exceeds threshold then reject waveform
                le_id_threshold=self.config["tcog_retracker"][
                    "le_id_threshold"
                ],  # power must exceed thermal noise by this amount to be identified as
                # leading edge
                le_dp_threshold=self.config["tcog_retracker"][
                    "le_dp_threshold"
                ],  # define threshold on normalised amplitude change which is required to
                # be accepted as lead edge
                include_measurements_array=waveforms_to_include,
            )  # if not None, pass a boolean array to indicate which waveforms to retrack

            # calculate the closest  bin number to the retracking point : units count

        mplog.info(
            f"[f{filenum}] Number of retracker failures inside mask= {n_retrack_failed} of"
            f" {n_waveforms_to_include}, "
            f"{100.0 * n_retrack_failed / n_waveforms_to_include:.2f}%"
        )

        # -------------------------------------------------------------------------------------
        # Calculate the closest  bin number to the retracking point : units count
        # --------------------------------------------------------------------------------------
        ind_wfm_retrack_20_ku = ref_bin_index + dr_bin

        # set Nan values to Fillvalue of -32768
        ind_wfm_retrack_20_ku[np.isnan(ind_wfm_retrack_20_ku)] = -32768

        shared_dict["ind_wfm_retrack_20_ku"] = ind_wfm_retrack_20_ku

        # --------------------------------------------------------------------------------------
        # Step 1d) Calculate Corrected Range : range_cor_xxxx_20_ku = 0.5 * c * window_del_20_ku
        # + sum_cor_20_ku + dr_meters_xxxx
        # --------------------------------------------------------------------------------------

        window_del_20_ku = l1b.variables["window_del_20_ku"][:].data

        shared_dict["pwr_at_rtrk_point"] = pwr_at_rtrk_point

        shared_dict["range_cor_20_ku"] = (
            0.5 * self.config["geophysical"]["speed_light"] * window_del_20_ku
            + shared_dict["sum_cor_20_ku"]
            + dr_meters
        )

        shared_dict["num_retracker_failures"] = n_retrack_failed
        shared_dict["percent_retracker_failure"] = (
            100.0 * n_retrack_failed / n_waveforms_to_include
        )

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
