#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TCOG retracker for CS2 waveforms from CS2 L1b (baseline-D/E only)
python port of Matlab original by M.McMillan (CPOM, Lancaster)

Added Savitsky-Golay waveform smoothing (Aublanc et al, 2021)

Functions:
----------
def retrack_tcog_waveforms_cs2(l1b_file,retrack_threshold_lrm,retrack_threshold_sin,
retrack_smooth_wf=False, plot_flag=0, measurement_index=None):

Used as:

    dr_bin_tcog,dr_meters_tcog,leading_edge_start,leading_edge_stop, n_retracker_failures=\
        retrack_tcog_waveforms_cs2(l1b_file=
        '/path/to/CS_OFFL_SIR_LRM_1B_20190504T122726_20190504T123244_D001.nc',
                             retrack_threshold_lrm=0.2,
                             retrack_threshold_sin=0.5,
                             debug_flag=False,
                             plot_flag=0,
                             measurement_index=None)

    or by passing in waveforms directly:

    nc = Dataset('/path/to/CS_OFFL_SIR_LRM_1B_20190504T122726_20190504T123244_D001.nc')
    wfs = nc.variables['pwr_waveform_20_ku'][:].data

    dr_bin_tcog,dr_meters_tcog,leading_edge_start,leading_edge_stop,  n_retracker_failures=\
        retrack_tcog_waveforms_cs2(waveforms=wfs,
                             retrack_threshold_lrm=0.2,
                             retrack_threshold_sin=0.5,
                             debug_flag=False,
                             plot_flag=0,
                             measurement_index=None)

Unit Tests:
----------

The __main__ section includes the unit tests of the retracker. These are run
from the command line as follows:

% cs2_tcog_retracker.py -h     :  for all command line options of the unit tests
Examples:
% cs2_tcog_retracker.py --lrmtest  : run unit test on a sample L1b LRM file.
Results are compared to Matlab outputs from original code.
% cs2_tcog_retracker.py --sintest  : run unit test on a sample L1b SIN file
Results are compared to Matlab outputs from original code.
% cs2_tcog_retracker.py --lrmtest --debug : enable debug mode, which prints results
from intermediate retracker steps
% cs2_tcog_retracker.py --lrmtest --plot  : enable plot mode, which plots input waveforms
leading edge, maximum peak, and retracker points
% cs2_tcog_retracker.py --lrmtest --plot  --index 312  --debug : just retrack measurement
number 312 (index count from 0)
% cs2_tcog_retracker.py --infile /path/to/l1bfile --plot : test with another
Baseline-D L1b file
% cs2_tcog_retracker.py --infile /path/to/l1bfile --outfile /path/to/output_results.txt
: write retracker output results to text file.
        Results are formatted as 1 waveform retracking result per line: tfmra epoch
        (bins) tfmra epoch (m) tcog epoch (bins) tcog epoch (m)

"""

import logging  # logging functions
from math import sqrt
from typing import List, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import gridspec
from netCDF4 import Dataset  # pylint: disable=E0611
from scipy.signal import savgol_filter  # waveform smoothing filter

from clev2er.utils.cs2.retrackers.fastsmooth import (  # waveform smoothing filter (option 2)
    fastsmooth,
)

# too-many-arguments,too-many-locals, too-many-statements pylint: disable=R0912,R0913,R0914,R0915
# too-many-nested-blocks, pylint: disable=R1702
# pylint: disable=R0801

log = logging.getLogger(__name__)

np.seterr("raise")  # show arithmetic errors locations in the code


class InvalidArraySizeError(Exception):
    """Exception for invalid array sizes"""


def retrack_tcog_waveforms_cs2(
    l1b_file: str = "",
    waveforms: Union[np.ndarray, None] = None,
    retrack_threshold_lrm: float = 0.2,
    retrack_threshold_sin: float = 0.5,
    retrack_smooth_wf: bool = False,
    debug_flag: bool = False,
    plot_flag: bool = False,
    measurement_index: Union[int, None] = None,
    include_measurements_array: Union[List[bool], None] = None,
    savitsky_golay_smoothing: bool = True,
    savitsky_golay_width: int = 9,
    savitsky_golay_poly_order: int = 3,
    ref_bin_ind_lrm: int = 64,
    ref_bin_ind_sin: int = 512,
    noise_sample_limit: int = 6,
    wf_oversampling_factor: int = 100,
    noise_threshold: float = 0.3,
    le_id_threshold: float = 0.05,
    le_dp_threshold: float = 0.20,
) -> Tuple[
    List[float],
    List[float],
    List[List[float]],
    List[List[float]],
    List[float],
    int,
    List[List[int]],
]:
    """
    Purpose:
        Retracking of CS2 LRM and SIN waveforms TCOG
        Reference: CryoSat-2 Product Handbook Baseline D1.1, C2-LI-ACS-ESL-5319.
        This is an adapted python port of Matlab original by M.McMillan

    Args:
        l1b_file(str,def=None): l1b .nc file (must be Baseline-D, NetCDF format)
                                LRM or SIN, file names must contain SIR_SIN_1B, or SIR_LRM_1B
        waveforms(np.ndarray,def=None): instead of reading from L1b file, you can pass in a
                                        numpy.ndarray of shape (num_measurements, waveform_numbins).
                                        waveform_numbins is 128 (LRM) or 1024 (SIN)
                                        This is the array returned by
                                        nc.variables['pwr_waveform_20_ku'][:].data
        retrack_threshold_lrm(float, def=0.2): lrm retracker threshold
        retrack_threshold_sin(float, def=0.5): sin retracker threshold
        retrack_smooth_wf(bool, def=False): specify whether to retrack raw or smoothed waveform
                                            False - raw waveform  |  True - smoothed waveform
        debug_flag(bool, def=False): set to True to output intermediate debugging output text
        plot_flag(bool, def=False): set to True to plot waveforms and retracking points for testing
        measurement_index(int, def=None): if not None, only retrack this measurement index (from 0)
        include_measurements_array(List[bool],def=None): None or [array of boolean values of size
                                                         equal to number of waveforms].
                                                        if not None, only retrack waveforms
                                                        corresponding to True values in this array
        savitsky_golay_smoothing(bool, def=True): if True then use a 1-d Savitsky-Golay filter to
                                                  smooth waveform
        savitsky_golay_width(int, def=9): Savitsky Golay smoothing width
        savitsky_golay_poly_order(int, def=3): Savitsky Golay polynomial order
        ref_bin_ind_lrm(int, def=64): from CS2 Baseline-D User Manual, p36;
        ref_bin_ind_sin(int, def=512): from CS2 Baseline-D User Manual, p36
        noise_sample_limit(int, def=6): maximum bin used to compute noise statistics
        wf_oversampling_factor(int,def=100): waveform oversampling factor
        noise_threshold(float, def=0.3): if mean amplitude in noise bins exceeds threshold then
                                         reject waveform
        le_id_threshold(float, def=0.05): power must exceed thermal noise by this amount to be
                                          identified as a leading edge
        le_dp_threshold(float, def=0.20): define threshold on normalised amplitude change which
                                          is required to be accepted as lead edge

    Returns:
        Tuple (dr_bin_tcog, dr_meters_tcog, leading_edge_start, leading_edge_stop,
        pwr_at_rtrk_point_tcog,n_retracker_failures,retrack_flag):
            dr_bin_tcog (List[float]) : tcog epoch relative to nominal tracking point
                                          in bins
            dr_meters_tcog (List[float]) : tcog epoch relative to nominal tracking point
                                        in meters
            leading_edge_start (List[List[float]]): leading edge start coordinates
                                                column 1 = bin  |  column 2 = normalised power
            leading_edge_stop (List[List[float]]): leading edge stop coordinates
                                                column 1 = bin  |  column 2 = normalised power
            pwr_at_rtrk_point_tcog (List[float]): power in counts at retracking point
            n_retracker_failures (int): number of waveforms were retracking failed
            retrack_flag : returned retracker flags for each waveform indicate how
                           retracking failed
                           col 1 (index 0): 0 or 1 if noise > threshold in noise gates
                           col 2 (index 1): 0 or 1 if no samples are sufficiently above
                                            the noise floor
                           col 3 (index 2): 0 or 1 if no waveform peak can be identified
                                            after the leading edge starts
                           col 4 (index 3): 0 or 1 if no leading edge found by end of waveform
                           col 5 (index 4): 0 (currently unused)
                           col 6 (index 5): 0 or 1 if  TCOG retracking point could not be found
    """

    if retrack_threshold_lrm < 0.0 or retrack_threshold_lrm > 1.0:
        raise ValueError(f"retrack_threshold_lrm {retrack_threshold_lrm} not between 0. and 1.")
    if retrack_threshold_sin < 0.0 or retrack_threshold_sin > 1.0:
        raise ValueError(f"retrack_threshold_sin {retrack_threshold_sin} not between 0. and 1.")
    if noise_threshold < 0.0 or noise_threshold > 1.0:
        raise ValueError(f"noise_threshold {noise_threshold} not between 0. and 1.")

    if le_dp_threshold < 0.0 or le_dp_threshold > 1.0:
        raise ValueError(f"le_dp_threshold {le_dp_threshold} not between 0. and 1.")

    if l1b_file and waveforms:
        raise ValueError("Must have either l1b_file or waveforms, not both as input to function")

    # ---------------------------------
    # Find if input L1b file is LRM or SIN
    # ---------------------------------

    if l1b_file:
        if "SIR_SIN_1B" in l1b_file:
            lrm_mode = False
            mode_str = "SIN"
        elif "SIR_LRM_1B" in l1b_file:
            lrm_mode = True
            mode_str = "LRM"
        else:
            raise ValueError(f"L1b file name {l1b_file} must include SIR_SIN_1B or SIR_LRM_1B")

        # Load netcdf L1 data file
        nc = Dataset(l1b_file)

        # Retrieve the waveforms
        wfs = nc.variables["pwr_waveform_20_ku"][:].data
        n_waveforms, waveform_size = np.shape(wfs)

    elif np.any(waveforms):
        n_waveforms, waveform_size = np.shape(waveforms)
        if waveform_size == 128:
            lrm_mode = True
            mode_str = "LRM"
        elif waveform_size == 1024:
            lrm_mode = False
            mode_str = "SIN"
        else:
            raise ValueError("waveforms size must be (,128) for LRM or (,1024) for SIN")
        wfs = waveforms

    log.debug("retrack_threshold_lrm %f", retrack_threshold_lrm)
    log.debug("retrack_threshold_sin %f", retrack_threshold_sin)

    # -------------------------
    # Define system parameters
    # -------------------------

    speed_of_light = 299792458  # speed of light (m/s) from CS2 Baseline-D User Manual, p36.
    bandwidth = 320000000  # chirp bandwidth used (Hz) from from CS2 Baseline-D User Manual, p36.

    # compute size of range bin
    rbin_size_lrm = speed_of_light / (
        2 * bandwidth
    )  # meters; from CS2 Baseline-D User Manual, p36.
    rbin_size_sin = speed_of_light / (
        4 * bandwidth
    )  # meters; from CS2 Baseline-D User Manual, p37.

    # ----------------------------
    # Define processing parameters
    # ----------------------------

    #   define width of fast smoothing window applied to waveform
    if lrm_mode:
        sm_width = 3
    else:  # SIN
        sm_width = 11

    #   define Savitsky-Golay smoothing parameters
    if savitsky_golay_smoothing:
        sm_width = savitsky_golay_width
        sm_polynomial_order = savitsky_golay_poly_order

    # -------------------------
    # define quality thresholds
    # -------------------------

    # specify how noise is computed
    noise_definition = "min_power"

    # Check if the include_measurements_array is of the correct length
    if include_measurements_array is not None:
        if len(include_measurements_array) != n_waveforms:
            raise InvalidArraySizeError(
                f"include_measurements_array size {len(include_measurements_array)}  \
                    must be same dimensions as number of waveforms {n_waveforms}"
            )

    # If measurement_index is specified then we want to only include waveforms from that index
    if measurement_index is not None:
        include_measurements_array = [False for i in range(n_waveforms)]
        include_measurements_array[measurement_index] = True

    # preallocate output arrays (list for each waveform)
    leading_edge_start = [[np.nan for _ in range(2)] for _ in range(n_waveforms)]
    leading_edge_stop = [[np.nan for _ in range(2)] for _ in range(n_waveforms)]
    retrack_point_tcog = [[np.nan for _ in range(3)] for _ in range(n_waveforms)]
    retrack_flag = [[0 for _ in range(6)] for _ in range(n_waveforms)]

    # Process each waveform
    for i, waveform in enumerate(wfs):
        # Special case for debugging individual measurements
        if measurement_index:
            if i != measurement_index:
                continue

        # skip waveform if include_measurements_array[i] is set to False
        if include_measurements_array is not None:
            if not include_measurements_array[i]:
                log.debug("Skipping as include_measurements_array is false")
                continue

        log.debug("retracking waveform %d of %d", i, n_waveforms)

        # compute max amplitude
        wf_max = np.max(waveform)
        if debug_flag:
            print("maximum amplitude=", wf_max)

        if wf_max == 0.0:
            if debug_flag:
                log.debug("wf_max is 0 so skipping")
            # set flag
            retrack_flag[i][0] = 1
            continue

        # normalise so that max amplitude is 1
        wfnorm = waveform / wf_max

        # ---------
        # smooth waveform
        # ---------

        if savitsky_golay_smoothing:
            # Apply 1-d Savitsky-Golay filter to smooth waveform
            wfnorm_sm = savgol_filter(wfnorm, sm_width, sm_polynomial_order)
        else:
            # apply (sliding-average) boxcar smooth; the edges are smoothed with
            # progressively smaller smooths the closer to the end.
            wfnorm_sm = fastsmooth(wfnorm, sm_width)

        if plot_flag:
            # Plot echo and smoothed echo for debugging
            plt.plot(wfnorm)
            plt.plot(wfnorm_sm)
            plt.ylim(0, 1)
            plt.show()

        # switch end values from 0 to nan
        wfnorm_sm[wfnorm_sm == 0] = np.nan  # COMMENT : sets any 0 to Nan, not just end points?

        # ---------------------
        # compute thermal noise
        # ---------------------
        if noise_definition == "first_bins":
            # estimate noise based on first samples of waveform
            wf_noise_mean = np.mean(wfnorm[0:noise_sample_limit])

        elif noise_definition == "min_power":
            # alternatively sort power values of unsmoothed waveform in ascending order
            wfsort = sorted(wfnorm)

            if debug_flag:
                print("lowest six samples of normalised waveform are ", wfsort[0:6])

            # estimate noise based on lowest 6 samples
            wf_noise_mean = np.mean(wfsort[0:6])
        else:
            raise ValueError(f"noise definition {noise_definition} unsupported")

        if debug_flag:
            print("wf_noise_mean=", wf_noise_mean)

        # ------------------------------------------------------------
        # quality check 1 - if mean noise above a predefined threshold
        # ------------------------------------------------------------

        if (wf_noise_mean > noise_threshold) or np.isnan(wf_noise_mean):
            # set flag
            retrack_flag[i][0] = 1
            log.debug("%d : mean noise above a predefined threshold", i)
            # do not attempt retracking and leave as nan

        else:  # continue with retracking
            # ------------------------
            # Over Sample the waveform
            # ------------------------
            wf_bin_num = np.linspace(0, waveform_size - 1, waveform_size)
            #  LRM: array([  0.,1.,..,127.]), size=128

            # create oversampled waveform bin indices
            wf_bin_numi = np.linspace(0, waveform_size - 1, waveform_size * wf_oversampling_factor)
            # LRM: array([  0.,1.,..,127.]), size=12800

            # Oversample normalised waveform
            wfi = np.interp(wf_bin_numi, wf_bin_num, wfnorm)

            # Oversample smoothed normalised waveform
            wfi_sm = np.interp(wf_bin_numi, wf_bin_num, wfnorm_sm)

            # ------------------
            # compute derivative
            # ------------------

            # compute first derivative of smoothed waveform using central difference
            # which is calculated between i-1:i+1
            d_wf_sm = np.gradient(wfi_sm, (1 / wf_oversampling_factor))

            # ------------------------------------
            # initiate leading edge identification
            # ------------------------------------

            # initiate parameters for iteratively finding leading edge with amplitude
            # above predefined threshold
            previous_le_ind = 0
            le_dp = 0
            count = 1
            # -------------------------------------------------------------------
            # loop through leading edges until minimum amplitude requirement met
            # or the end of the waveform is reached
            # --------------------------------------------------------------------

            # searches for leading edge greater than the amplitude threshold
            while le_dp < le_dp_threshold:
                # Find the first index of the waveform wfi_sm that satifies the criteria:
                #    > (wf_noise_mean + le_id_threshold)
                #    d_wf_sm > 0
                #    index > previous_le_ind

                le_index = np.where((wfi_sm > (wf_noise_mean + le_id_threshold)) & (d_wf_sm > 0))[0]

                if le_index.size > 0:
                    le_index = le_index[le_index > (previous_le_ind + wf_oversampling_factor)]

                # ----------------------------------------------------------------------
                # quality check 2 - if no samples are sufficiently above the noise floor
                # ----------------------------------------------------------------------

                if le_index.size == 0:
                    # set flag
                    retrack_flag[i][1] = 1
                    # exit search for leading edge
                    log.debug("%d no samples above noise floor", i)
                    break

                # Select the first leading edge index found
                le_index = le_index[0]

                # ----------------------------------------------------------
                # leading edge exists so find position and amplitude of peak
                # ----------------------------------------------------------

                # find where the gradient first becomes negative after the power threshold
                # is exceeded
                first_peak_ind = np.where((d_wf_sm <= 0) & (wf_bin_numi > wf_bin_numi[le_index]))[0]
                # Select the first one
                if first_peak_ind.size > 0:
                    first_peak_ind = first_peak_ind[0]

                    # calculate the amplitude of the peak above the identified start point
                    # of the leading edge
                    le_dp = wfi_sm[first_peak_ind] - wfi_sm[le_index]

                    # update previously identified peak to the current one in case the while
                    # loop continues
                    previous_le_ind = first_peak_ind

                    # if reached end of waveform
                    if previous_le_ind > (wf_bin_numi.size - wf_oversampling_factor - 1):
                        # set flag
                        retrack_flag[i][3] = 1
                        # exit search for leading edge
                        log.debug("%d: reached end of waveform", i)
                        break
                else:
                    # -------------------------------------------------------------------
                    # quality check 3 - if no waveform peak can be identified after the
                    # leading edge starts
                    # -------------------------------------------------------------------
                    # first_peak_ind array is empty so set flag
                    retrack_flag[i][2] = 1
                    log.debug(
                        "no waveform peak can be identified after the \
                                leading edge starts"
                    )
                    # exit search for leading edge
                    break

                # update count of how many iterations through loop
                count = count + 1

            # ----------------------
            # find retracking point
            # ----------------------

            # only compute retracking points if no flags set

            if np.sum(retrack_flag[i]) > 0:
                log.debug("Retracker flags set, so not finding retracker point")
            else:
                # --------------------------
                # find tcog retracking point
                # --------------------------

                retrack_ind_tcog = None

                # compute ocog amplitude
                tcog_amp = sqrt(sum(wfnorm**4) / sum(wfnorm**2))

                log.debug("ocog amplitude, tcog_amp=%f", tcog_amp)

                # switch to handle mode specific retracking thresholds
                if lrm_mode:
                    # compute retracking threshold as proportion of tcog amplitude
                    retrack_wf_threshold_tcog = retrack_threshold_lrm * tcog_amp
                else:  # SIN mode
                    # compute retracking threshold as proportion of tcog amplitude
                    retrack_wf_threshold_tcog = retrack_threshold_sin * tcog_amp

                log.debug("retrack_wf_threshold_tcog=%f", retrack_wf_threshold_tcog)

                # select whether to retrack smoothed or original waveform  - default is non
                # smoothed to keep precision
                if retrack_smooth_wf:
                    # find first wf sample above threshold apply to oversampled waveform to
                    # improve precision,
                    samples_above_threshold = np.where((wfi_sm > retrack_wf_threshold_tcog))[0]
                    n_samples_above_threshold = len(samples_above_threshold)
                    log.debug("n_samples_above_threhold=%d", n_samples_above_threshold)

                    if n_samples_above_threshold > 0:
                        retrack_ind_tcog = samples_above_threshold[0]
                    else:
                        log.debug("TCOG retracking point could not be found")
                        retrack_flag[i][5] = 1

                else:
                    # find first leading edge value above the retracking threshold for
                    # unsmoothed waveform
                    samples_above_threshold = np.where(
                        (wfi > retrack_wf_threshold_tcog) & (wf_bin_numi > wf_bin_numi[le_index])
                    )[0]

                    if plot_flag:
                        # Plot echo and smoothed echo for debugging
                        plt.plot(wfi)
                        # plt.ylim(0, 1)
                        plt.show()
                    log.debug("retrack_wf_threshold_tcog %f", retrack_wf_threshold_tcog)

                    n_samples_above_threshold = len(samples_above_threshold)
                    log.debug("n_samples_above_threshold=%d", n_samples_above_threshold)
                    if n_samples_above_threshold > 0:
                        retrack_ind_tcog = samples_above_threshold[0]
                    else:
                        log.debug("TCOG retracking point could not be found")
                        retrack_flag[i][5] = 1

                if retrack_flag[i][5]:
                    log.debug("TCOG retracker failed, so skipping")
                    continue

                if plot_flag:
                    print("TCOG : ", wf_bin_numi[retrack_ind_tcog], retrack_ind_tcog)

                    # Plot echo with retracking points
                    fig = plt.figure(figsize=(15, 6))
                    this_gridspec = gridspec.GridSpec(1, 2, width_ratios=[2.5, 1])
                    ax1 = plt.subplot(this_gridspec[0])
                    ax2 = plt.subplot(this_gridspec[1])

                    ax1.plot(
                        wf_bin_numi,
                        wfi,
                        color="green",
                        marker=".",
                        label="oversampled waveform",
                    )
                    ax1.plot(
                        wf_bin_numi,
                        wfi_sm,
                        color="blue",
                        marker=".",
                        label="oversampled smoothed waveform",
                    )
                    ax1.plot(wf_bin_numi, d_wf_sm, color="lightgray", label="gradient")
                    ax1.set_xlabel("Waveform bin number")
                    ax1.set_ylabel("Normalised power")
                    ax1.set_title(f"{mode_str} Waveform Retracking for Measurement Number : {i}")
                    ax1.xaxis.grid()
                    ax1.yaxis.grid()
                    ax1.axvline(
                        x=wf_bin_numi[first_peak_ind],
                        color="grey",
                        linestyle="-.",
                        label="1st peak index",
                    )
                    ax1.axvline(
                        x=wf_bin_numi[le_index],
                        color="grey",
                        linestyle="--",
                        label="LE index",
                    )

                    if retrack_ind_tcog:
                        ax1.axvline(
                            x=wf_bin_numi[retrack_ind_tcog],
                            color="red",
                            linestyle="-",
                            label="TCOG Retracking point",
                        )
                    ax1.axhline(
                        y=wf_noise_mean,
                        color="yellow",
                        linestyle="--",
                        label="Mean Noise in noise gates",
                        linewidth=2,
                    )

                    ax1.legend()

                    # Create 2nd subplot,and display waveform around the leading edge
                    # find indices around leading edge
                    plot_start_index = le_index - int(wf_bin_numi.size / 80)
                    plot_start_index = max(plot_start_index, 0)

                    plot_end_index = first_peak_ind + int(wf_bin_numi.size / 80)
                    if plot_end_index > (wf_bin_numi.size - 1):
                        plot_end_index = wf_bin_numi.size - 1

                    ax2.plot(
                        wf_bin_numi[plot_start_index:plot_end_index],
                        wfi[plot_start_index:plot_end_index],
                        color="green",
                        marker=".",
                        label="oversampled waveform",
                    )
                    ax2.plot(
                        wf_bin_numi[plot_start_index:plot_end_index],
                        wfi_sm[plot_start_index:plot_end_index],
                        color="blue",
                        marker=".",
                        label="oversampled smoothed waveform",
                    )
                    ax2.axvline(
                        x=wf_bin_numi[first_peak_ind],
                        color="grey",
                        linestyle="-.",
                        linewidth=4,
                        label="1st peak index",
                    )
                    ax2.axvline(
                        x=wf_bin_numi[le_index],
                        color="grey",
                        linestyle="--",
                        label="LE index",
                    )

                    if retrack_ind_tcog:
                        ax2.axvline(
                            x=wf_bin_numi[retrack_ind_tcog],
                            color="red",
                            linestyle="-",
                            label="TCOG Retracking point",
                        )
                    ax2.axhline(
                        y=wf_noise_mean,
                        color="yellow",
                        linestyle="--",
                        label="Mean Noise in noise gates",
                        linewidth=2,
                    )

                    ax2.set_ylim(ymin=0.0, ymax=1.0)
                    ax2.set_title("Around Leading Edge")
                    fig.tight_layout()
                    plt.show(block=True)

                # ------------------------------
                # store leading edge coordinates
                # ------------------------------

                # columns give bin number, normalised amplitude value, original amplitude value
                leading_edge_start[i][0] = wf_bin_numi[
                    le_index
                ]  # LRM: array([  0.,..,127.]), size=12800
                leading_edge_start[i][1] = wfi_sm[
                    le_index
                ]  # Oversampled smoothed normalised waveform
                leading_edge_stop[i][0] = wf_bin_numi[first_peak_ind]
                leading_edge_stop[i][1] = wfi_sm[first_peak_ind]

                # ----------------------------
                # store retracking coordinates
                # ----------------------------

                if not retrack_flag[i][5]:
                    if retrack_smooth_wf:
                        retrack_point_tcog[i][0] = wf_bin_numi[retrack_ind_tcog]
                        retrack_point_tcog[i][1] = wfi_sm[retrack_ind_tcog]
                        retrack_point_tcog[i][2] = wfi_sm[retrack_ind_tcog] * wf_max
                    else:
                        retrack_point_tcog[i][0] = wf_bin_numi[retrack_ind_tcog]
                        retrack_point_tcog[i][1] = wfi[retrack_ind_tcog]
                        retrack_point_tcog[i][2] = wfi[retrack_ind_tcog] * wf_max

                    if retrack_point_tcog[i][2] == 0:
                        retrack_point_tcog[i][0] = np.nan
                        retrack_point_tcog[i][1] = np.nan
                        retrack_point_tcog[i][2] = np.nan

                        log.debug("TCOG : zero power found at retracking point")
                        retrack_flag[i][5] = 1

                else:
                    log.debug("No retracking point retrieved for TCOG")

    # Completed retracking loop over waveforms

    # --------------------------------------------
    # compute retracker offsets for all waveforms
    # --------------------------------------------

    # switch to handle different mode reference bin
    if lrm_mode:
        # compute range offsets from reference to retracked bins
        dr_bin_tcog = np.array(retrack_point_tcog)[:, 0] - ref_bin_ind_lrm
        log.debug("dr_bin_tcog %s", dr_bin_tcog)

        # convert offsets to meters
        dr_meters_tcog = dr_bin_tcog * rbin_size_lrm

    else:  # SIN mode
        # compute range offsets from reference to retracked bins
        dr_bin_tcog = np.array(retrack_point_tcog)[:, 0] - ref_bin_ind_sin

        # convert offsets to meters
        dr_meters_tcog = dr_bin_tcog * rbin_size_sin

    # Store power in counts at retracking point (used for backscatter calculation)

    pwr_at_rtrk_point_tcog = np.array(retrack_point_tcog)[:, 2]

    n_retracker_failures = 0

    for i in range(n_waveforms):
        if measurement_index is not None:
            if i != measurement_index:
                continue
        if (
            retrack_flag[i][5]
            or retrack_flag[i][3]
            or retrack_flag[i][2]
            or retrack_flag[i][1]
            or retrack_flag[i][0]
        ):
            n_retracker_failures += 1

    log.debug("Number of waveforms : %d", n_waveforms)
    if include_measurements_array is not None:
        log.debug(
            "Number of included waveforms : %d",
            np.count_nonzero(include_measurements_array),
        )
    log.debug("n_retracker_failures=%d", n_retracker_failures)

    return (
        dr_bin_tcog,
        dr_meters_tcog,
        leading_edge_start,
        leading_edge_stop,
        pwr_at_rtrk_point_tcog,
        n_retracker_failures,
        retrack_flag,
    )
