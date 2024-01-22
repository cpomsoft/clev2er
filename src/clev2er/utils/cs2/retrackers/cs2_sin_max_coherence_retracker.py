#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CS2 Maximum Coherence Retracker for SARin waveforms only
Adapted by A.Muir (CPOM) from M.McMillan (CPOM) Leading Edge Detection and
J.Aublanc (CLS) LMC Retracker from Aublanc et al, 2021 (Ice Sheet Topography from a
New CryoSat-2 SARIn Processing Chain, and Assessment by Comparison to ICESat-2 over
Antarctica)


Functions:
----------
def retrack_cs2_sin_max_coherence(l1b_file=None,waveforms=None,coherence=None,
retrack_smooth_wf=False, plot_flag=False,
measurement_index=None, include_measurements_array=None)

Used as:

    dr_bin_mc,dr_meters_mc,leading_edge_start,leading_edge_stop, pwr_at_rtrk_point_mc,
    n_retrack_mc_failed=\
    retrack_cs2_sin_max_coherence(l1b_file=
    '/path/to/CS_OFFL_SIR_LRM_1B_20190504T122726_20190504T123244_D001.nc')

    or by passing in waveforms directly:

    nc = Dataset('/path/to/CS_OFFL_SIR_LRM_1B_20190504T122726_20190504T123244_D001.nc')
    wfs = nc.variables['pwr_waveform_20_ku'][:].data
    coh = nc.variables['coherence_waveform_20_ku'][:].data

    dr_bin_tfmra,dr_meters_tfmra,dr_bin_mc,dr_meters_mc,leading_edge_start,
    leading_edge_stop, n_retrack_tfmra_failed, n_retrack_mc_failed=\
        retrack_tfmra_tcog_waveforms_cs2(waveforms=wfs,coherence=coh)

Unit Tests:
----------

The __main__ section includes the unit tests of the retracker. These are run from the
command line as follows:

% cs2_tfmra_tcof_retracker.py -h     :  for all command line options of the unit tests
Examples:
% cs2_tfmra_tcof_retracker.py --lrmtest  : run unit test on a sample L1b LRM file.
Results are compared to Matlab outputs from original code.
% cs2_tfmra_tcof_retracker.py --sintest  : run unit test on a sample L1b SIN file.
Results are compared to Matlab outputs from original code.
% cs2_tfmra_tcof_retracker.py --lrmtest --debug : enable debug mode, which prints
results from intermediate retracker steps
% cs2_tfmra_tcof_retracker.py --lrmtest --plot  : enable plot mode, which plots input
% waveforms, leading edge, maximum peak, and retracker points
% cs2_tfmra_tcof_retracker.py --lrmtest --plot  --index 312  --debug : just
retrack measurement number 312 (index count from 0)
% cs2_tfmra_tcof_retracker.py --infile /path/to/l1bfile --plot : test with another
 Baseline-D L1b file
% cs2_tfmra_tcof_retracker.py --infile /path/to/l1bfile --outfile
/path/to/output_results.txt : write retracker output results to text file.
        Results are formatted as 1 waveform retracking result per line: tfmra epoch
        (bins) tfmra epoch (m) tcog epoch (bins) tcog epoch (m)

"""

import logging  # logging functions
from typing import List, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import gridspec
from netCDF4 import Dataset  # pylint: disable=E0611
from scipy.signal import savgol_filter

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


def retrack_cs2_sin_max_coherence(
    l1b_file: str = "",
    waveforms: Union[np.ndarray, None] = None,
    coherence: Union[np.ndarray, None] = None,
    retrack_smooth_wf: bool = False,
    plot_flag: bool = False,
    measurement_index: Union[int, None] = None,
    include_measurements_array: Union[List[bool], None] = None,
    ref_bin_ind_sin: int = 512,
    wf_oversampling_factor: int = 100,
    noise_sample_limit: int = 6,
    noise_threshold: float = 0.30,
    savitsky_golay_width: int = 9,
    savitsky_golay_poly_order: int = 3,
    le_id_threshold: float = 0.05,
    le_dp_threshold: float = 0.20,
    coherence_smoothing_width=9,
) -> Tuple[
    np.ndarray,
    np.ndarray,
    List[List[float]],
    List[List[float]],
    np.ndarray,
    int,
    List[List[int]],
]:
    """
    % SUMMARY
    %   Retracking of CS2 SIN waveforms using Max Coherence Retracker
    %   Reference: CryoSat-2 Product Handbook Baseline D1.1, C2-LI-ACS-ESL-5319.
    %   This is an adapted python port of Matlab original by M.McMillan for Leading Edge
    %   Detection, and
    %   the LMC retracker in Aublanc et al, 2021 (Ice Sheet Topography from a
    %   New CryoSat-2 SARIn Processing Chain, and Assessment by Comparison to ICESat-2
    %   over Antarctica)
    % ------------------------------------------------------------------------

    Args:
        l1b_file (str) : file name of L1b file
        waveforms (np.ndarray): instead of reading from L1b file, you can pass in a
                                numpy.ndarray of shape (num_measurements, waveform_numbins).
                                waveform_numbins is 128 (LRM) or 1024 (SIN)
        coherence (np.ndarray): SIN only coherence waveform for use in maximum coherence
                                retracking
        retrack_smooth_wf (bool, def=False): specify whether to retrack raw (False) or
                                  smoothed waveform (True)
        plot_flag (bool, def=False): set to True to plot waveforms and retracking points
                                    for testing/debugging purposes
                                    (Note, blocks until each plot closed)
        measurement_index (int, def=None): if not None, only retrack this measurement index
                                           (from 0). Used for debugging
        include_measurements_array (List[bool]): None or [array of boolean values of size equal to
                                    number of waveforms]. if not None, only retrack waveforms
                                    corresponding to True values in this array
        ref_bin_ind_sin (int, def=512) : reference bin index, from CS2 Baseline-D User
                                         Manual, p36;
        wf_oversampling_factor (int) : waveform oversampling factor (default=100)
        noise_sample_limit (int, def=6) : maximum bin used to compute noise statistics
        noise_threshold (float,def=0.3) : if mean amplitude in noise bins exceeds threshold then
                                          reject waveform
        savitsky_golay_width (int, def=9): Savitsky Golay smoothing width
        savitsky_golay_poly_order (int, def=3): Savitsky Golay polynomial order
        le_id_threshold (float, def=0.05) : power must exceed thermal noise by this amount to be
                                            identified as a leading edge
        le_dp_threshold (float, def=0.2): define threshold on normalised amplitude change which is
                                          required to be accepted as lead edge
        coherence_smoothing_width (int, def-9): coherence boxcar average smoothing width


    Returns:
        Tuple: (dr_bin_mc, dr_meters_mc, leading_edge_start, leading_edge_stop,pwr_at_rtrk_point_mc,
                n_retrack_mc_failed, retrack_flag)
                dr_bin_mc (List[float]) : max coherence epoch relative to nominal tracking point
                                          in bins
                dr_meters_mc (List[float]) : max coherence epoch relative to nominal tracking point
                                          in meters
                leading_edge_start (List[List[float]]): leading edge start coordinates
                                                    column 1 = bin  |  column 2 = normalised power
                leading_edge_stop (List[List[float]]): leading edge stop coordinates
                                                    column 1 = bin  |  column 2 = normalised power
                pwr_at_rtrk_point_mc (List[float]): power in counts at retracking point
                n_retrack_mc_failed (int): number of waveforms were retracking failed
                retrack_flag (List[List[int]]): returned retracker flags for each waveform indicate
                            how retracking failed | 6 x t |
                                column 1 (index 0): 0 or 1 max amplitude is 0 so skippings
                                                    or mean noise above a predefined threshold
                                column 2 (index 1): 0 or 1 if no samples are sufficiently above the
                                    noise floor
                                column 3 (index 2): 0 or 1 if no peak identified
                                column 4 (index 3): 0 or 1 if no leading edge found by end of
                                waveform
                                column 5 (index 4): 0 (currently unused)
                                column 6 (index 5): 0 or 1 if  No retracking point retrieved

    """

    if l1b_file and waveforms:
        raise ValueError("Must have either l1b_file or waveforms, not both as input to function")

    # -------------------------
    # Find if input file is LRM or SIN. Only SIN allowed
    # -------------------------

    if l1b_file:
        if "SIR_SIN_1B" in str(l1b_file):
            mode_str = "SIN"
        elif "SIR_LRM_1B" in str(l1b_file):
            raise ValueError("Must be a file containing SARin waveforms, not LRM")
        else:
            raise ValueError(f"L1b file name {l1b_file} must include SIR_SIN_1B")
    elif waveforms is not None:
        if waveforms.ndim == 2 and waveforms.shape[1] == 1024:
            n_waveforms, waveform_size = np.shape(waveforms)
            mode_str = "SIN"
        else:
            raise ValueError("waveforms size must be (,1024) for SIN")

    # -------------------------
    # Define system parameters
    # -------------------------

    speed_of_light = 299792458  # speed of light (m/s) from CS2 Baseline-D User Manual, p36.
    bandwidth = 320000000  # chirp bandwidth used (Hz) from from CS2 Baseline-D User Manual, p36.

    # compute size of range bin
    rbin_size_sin = speed_of_light / (
        4 * bandwidth
    )  # meters; from CS2 Baseline-D User Manual, p37.

    #   define Savitsky-Golay smoothing parameters
    sm_width = savitsky_golay_width
    sm_polynomial_order = savitsky_golay_poly_order

    # -------------------------
    # define quality thresholds
    # -------------------------

    # specify how noise is computed
    noise_definition = "min_power"

    if l1b_file:
        # Load netcdf L1 data file
        nc = Dataset(l1b_file)

        # Retrieve the waveforms
        wfs = nc.variables["pwr_waveform_20_ku"][:].data
        n_waveforms, waveform_size = np.shape(wfs)

        # Retrieve the coherence for SIN waveforms
        coherence = nc.variables["coherence_waveform_20_ku"][:].data
    else:
        wfs = waveforms
        # coherence passed as function parameter

    # Check if the include_measurements_array is of the correct length
    if include_measurements_array is not None:
        if len(include_measurements_array) != n_waveforms:
            raise InvalidArraySizeError(
                f"include_measurements_array size {len(include_measurements_array)}  \
                    must be same dimensions as number of waveforms {n_waveforms}"
            )

    # preallocate output arrays (list for each waveform)
    leading_edge_start = [[np.nan for _ in range(2)] for _ in range(n_waveforms)]
    leading_edge_stop = [[np.nan for _ in range(2)] for _ in range(n_waveforms)]
    retrack_point_mc = [[np.nan for _ in range(3)] for _ in range(n_waveforms)]
    retrack_flag = [[0 for _ in range(6)] for _ in range(n_waveforms)]

    # Process each waveform
    for i, waveform in enumerate(wfs):
        # Special case for debugging individual measurements
        if measurement_index:
            if i != measurement_index:
                continue

        # log.debug('retracking measurment: {} '.format(i))

        # skip waveform if include_measurements_array[i] is set to False
        if include_measurements_array is not None:
            if not include_measurements_array[i]:
                log.debug("skip waveform as include_measurements_array[i] is set to False")
                continue

        # ßlog.debug('retracking waveform {} of {}'.format(i ,n_waveforms))

        # compute max amplitude
        wf_max = np.max(waveform)

        if wf_max == 0.0:
            log.debug("wf_max is 0 so skipping")
            # set flag
            retrack_flag[i][0] = 1
            continue

        # normalise so that max amplitude is 1
        wfnorm = waveform / wf_max

        # ---------
        # smooth waveform
        # ---------

        # Apply 1-d Savitsky-Golay filter, to smooth waveform
        wfnorm_sm = savgol_filter(wfnorm, sm_width, sm_polynomial_order)

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

            # estimate noise based on lowest 6 samples
            wf_noise_mean = np.mean(wfsort[0:6])
        else:
            raise ValueError(f"noise definition {noise_definition} unsupported")

        # ------------------------------------------------------------
        # quality check 1 - if mean noise above a predefined threshold
        # ------------------------------------------------------------

        if (wf_noise_mean > noise_threshold) or np.isnan(wf_noise_mean):
            # set flag
            retrack_flag[i][0] = 1

            log.debug("quality check 1 FAILED : mean noise above a predefined threshold")

            # do not attempt retracking and leave as nan

        else:  # continue with retracking
            # ------------------------
            # Over Sample the waveform
            # ------------------------
            wf_bin_num = np.linspace(0, waveform_size - 1, waveform_size)

            # create oversampled waveform bin indices
            wf_bin_numi = np.linspace(0, waveform_size - 1, waveform_size * wf_oversampling_factor)

            # Oversample normalised waveform
            wfi = np.interp(wf_bin_numi, wf_bin_num, wfnorm)

            # Oversample smoothed normalised waveform
            wfi_sm = np.interp(wf_bin_numi, wf_bin_num, wfnorm_sm)

            # ------------------
            # compute derivative
            # ------------------

            # compute first derivative of smoothed waveform using central difference which is
            # calculated between i-1:i+1
            d_wf_sm = np.gradient(wfi_sm, (1 / wf_oversampling_factor))

            # ------------------------------------
            # initiate leading edge identification
            # ------------------------------------

            # initiate parameters for iteratively finding leading edge with amplitude above
            # predefined threshold
            previous_le_ind = 0
            le_dp = 0
            count = 1
            # -------------------------------------------------------------------------------
            # loop through leading edges until minimum amplitude requirement met or the end of
            # the waveform is reached
            # -------------------------------------------------------------------------------

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
                    log.debug(
                        "quality check 2 FAILED :no samples are sufficiently above the noise floor"
                    )
                    # exit search for leading edge
                    break

                # Select the first leading edge index found
                le_index = le_index[0]

                # ----------------------------------------------------------
                # leading edge exists so find position and amplitude of peak
                # ----------------------------------------------------------

                # find where the gradient first becomes negative after the power threshold is
                # exceeded
                first_peak_indices = np.where(
                    (d_wf_sm <= 0) & (wf_bin_numi > wf_bin_numi[le_index])
                )[0]
                # Select the first one
                if first_peak_indices.size > 0:
                    first_peak_ind = int(first_peak_indices[0])

                    # calculate the amplitude of the peak above the identified start point of
                    # the leading edge
                    le_dp = wfi_sm[first_peak_ind] - wfi_sm[le_index]

                    # update previously identified peak to the current one in case the while
                    # loop continues
                    previous_le_ind = first_peak_ind

                    # if reached end of waveform
                    if previous_le_ind > (wf_bin_numi.size - wf_oversampling_factor - 1):
                        # set flag
                        retrack_flag[i][3] = 1
                        # exit search for leading edge
                        break
                else:
                    # ---------------------------------------------------------------------
                    # quality check 3 - if no waveform peak can be identified after the
                    # leading edge starts
                    # ---------------------------------------------------------------------
                    # first_peak_ind array is empty so set flag
                    retrack_flag[i][2] = 1
                    log.debug(
                        "quality check 3 FAILED :no waveform peak can be identified after \
                            the leading edge starts"
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
                log.debug("Retracker flags set, so not continuing to find retracking point")
            else:
                # ----------------------------------------------------------------------------
                # find Max Coherence retracking point for SIN waveforms
                # ----------------------------------------------------------------------------

                # Smooth the coherence waveform using a running average window
                # Coherence waveform is not oversampled
                if coherence is not None:
                    coherence_sm = fastsmooth(coherence[i], coherence_smoothing_width)
                else:
                    raise ValueError("coherence is None instead of np.ndarray")
                # Find indices of 50% up the leading edge to start search for max coherence
                #  where WFnorm [ns...ne] > 0.5 * LEamp + LEmin_energy
                if retrack_smooth_wf:
                    top_of_le_indices = np.where((wfi_sm - wfi_sm[le_index]) > 0.5 * le_dp)[0]
                else:
                    top_of_le_indices = np.where((wfi - wfi[le_index]) > 0.5 * le_dp)[0]
                # Restrict to between le_index and first_peak_ind
                top_of_le_indices = np.unique(
                    np.rint(
                        wf_bin_numi[
                            top_of_le_indices[
                                (top_of_le_indices >= le_index)
                                & (top_of_le_indices <= first_peak_ind)
                            ]
                        ]
                    ).astype(int)
                )

                if len(top_of_le_indices) < 1:
                    retrack_flag[i][5] = 1
                else:
                    mc_start_index = top_of_le_indices[0]
                    mc_end_index = top_of_le_indices[-1]
                    # find the index of maximum coherence in wf indices
                    index_of_max_coherence = top_of_le_indices[
                        np.argmax(coherence_sm[top_of_le_indices])
                    ]

                    if retrack_smooth_wf:
                        retrack_point_mc[i][0] = index_of_max_coherence
                        retrack_point_mc[i][1] = wfi_sm[
                            index_of_max_coherence * wf_oversampling_factor
                        ]
                        retrack_point_mc[i][2] = (
                            wfi_sm[index_of_max_coherence * wf_oversampling_factor] * wf_max
                        )
                    else:
                        retrack_point_mc[i][0] = index_of_max_coherence
                        retrack_point_mc[i][1] = waveform[index_of_max_coherence] / wf_max
                        retrack_point_mc[i][2] = waveform[index_of_max_coherence]

                    if retrack_point_mc[i][2] == 0:
                        retrack_point_mc[i][0] = np.nan
                        retrack_point_mc[i][1] = np.nan
                        retrack_point_mc[i][2] = np.nan
                        log.debug("zero power found at retracking point")
                        retrack_flag[i][5] = 1

                if plot_flag:
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
                        x=float(wf_bin_numi[le_index]),
                        color="grey",
                        linestyle="--",
                        label="LE index",
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
                    plot_start_index = int(le_index - int(wf_bin_numi.size / 80))
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
                        x=float(wf_bin_numi[le_index]),
                        color="grey",
                        linestyle="--",
                        label="LE index",
                    )

                    ax2.axvline(x=mc_start_index, color="pink", linestyle="-.", label="MC Start")
                    ax2.axvline(x=mc_end_index, color="pink", linestyle="-.", label="MC End")
                    ax2.axvline(
                        x=index_of_max_coherence,
                        color="pink",
                        linestyle="-",
                        linewidth=4,
                        label="MC retrack point",
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
                leading_edge_start[i][0] = wf_bin_numi[le_index].item()
                leading_edge_start[i][1] = wfi_sm[le_index].item()
                leading_edge_stop[i][0] = wf_bin_numi[first_peak_ind]
                leading_edge_stop[i][1] = wfi_sm[first_peak_ind]

                # ----------------------------
                # store retracking coordinates
                # ----------------------------

                if retrack_flag[i][5]:
                    log.debug("No retracking point retrieved for Max Coherence")

    # Completed retracking loop over waveforms

    # --------------------------------------------
    # compute retracker offsets for all waveforms
    # --------------------------------------------

    # compute range offsets from reference to retracked bins
    dr_bin_mc = np.array(retrack_point_mc)[:, 0] - ref_bin_ind_sin

    # convert offsets to meters
    dr_meters_mc = dr_bin_mc * rbin_size_sin

    # Store power in counts at retracking point (used for backscatter calculation)

    pwr_at_rtrk_point_mc = np.array(retrack_point_mc)[:, 2]

    n_retrack_mc_failed = 0

    for i in range(n_waveforms):
        # Check MC retracker flags
        if (
            retrack_flag[i][5]
            or retrack_flag[i][3]
            or retrack_flag[i][2]
            or retrack_flag[i][1]
            or retrack_flag[i][0]
        ):
            n_retrack_mc_failed += 1

    log.debug("Number of waveforms = %d", n_waveforms)
    if include_measurements_array is not None:
        log.debug(
            "Number of included waveforms : %d",
            np.count_nonzero(include_measurements_array),
        )
    log.debug("n_retrack_mc_failed=%d", n_retrack_mc_failed)

    return (
        dr_bin_mc,
        dr_meters_mc,
        leading_edge_start,
        leading_edge_stop,
        pwr_at_rtrk_point_mc,
        n_retrack_mc_failed,
        retrack_flag,
    )
