#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Waveform QC checks for CryoSat

"""

# Imports

import logging  # logging functions
import sys

import numpy as np

# too-many-arguments, pylint: disable=R0913
# too-many-locals, pylint: disable=R0914

log = logging.getLogger(__name__)


def sarin_waveform_qc_checks(
    pwr_waveform_20_ku=None,
    echo_scale_factor_20_ku=None,
    echo_scale_pwr_20_ku=None,
    noise_power_20_ku=None,
    total_power_threshold=5e-17,
    low_peakiness_threshold=0.9,
    low_position_max_power=2,
    high_position_max_power=1011,
):
    """
    Inputs:
    pwr_waveform_20_ku   :  numpy.ndarray of shape (num_measurements, waveform_numbins).
                    waveform_numbins is 128 (LRM) or 1024 (SIN)
                   This is the array returned by :
                   waveforms = nc.variables['pwr_waveform_20_ku'][:].data

    Return values:

    waveforms_ok :  boolean array of True (waveform ok), False (waveform not suitable)

    """

    if not np.any(pwr_waveform_20_ku):
        log.error(
            "No pwr_waveform_20_ku waveforms passed to waveform_qc_checks function"
        )
        sys.exit()

    n_waveforms, waveform_size = np.shape(pwr_waveform_20_ku)
    if waveform_size == 128:
        lrm_mode = True
    elif waveform_size == 1024:
        lrm_mode = False
    else:
        log.error("pwr_waveform_20_ku size must be (,128) for LRM or (,1024) for SIN")
        sys.exit()

    waveforms_ok = np.ones(n_waveforms, dtype=bool)

    # if LRM mode just return all ok
    if lrm_mode:
        return waveforms_ok

    # Perform check on each waveform
    for i, pwr_waveform in enumerate(pwr_waveform_20_ku):
        echo_scale_factor = echo_scale_factor_20_ku[i]
        echo_scale_pwr = echo_scale_pwr_20_ku[i]

        # ---------------------------------------------------------------------
        #  Check waveform total power > threshold (5e-17)
        # ---------------------------------------------------------------------

        total_power = np.sum(pwr_waveform * echo_scale_factor * (2.0**echo_scale_pwr))
        if total_power < total_power_threshold:
            waveforms_ok[i] = False
            continue

        # ---------------------------------------------------------------------
        #  Remove noise below threshold and then check waveform total power
        # > threshold (5e-17)
        # ---------------------------------------------------------------------

        power_watts = pwr_waveform * echo_scale_factor * (2.0**echo_scale_pwr)
        d_power_threshold = pow(10.0, noise_power_20_ku[i] / 10.0)
        power_watts -= d_power_threshold
        neg_vals = np.where(power_watts < 0.0)[0]
        if len(neg_vals) > 0:
            power_watts[neg_vals] = 0.0

        total_power = np.sum(power_watts)
        if total_power < total_power_threshold:
            waveforms_ok[i] = False
            continue

        # -----------------------------------------------------------------------------
        #  Check waveform peakiness
        # -----------------------------------------------------------------------------

        peakiness = (1024 - 256) * np.max(pwr_waveform) / np.sum(pwr_waveform)

        if peakiness < low_peakiness_threshold:
            waveforms_ok[i] = False
            continue

        # -----------------------------------------------------------------------------
        # Check position of max power >1 and < 1012
        # -----------------------------------------------------------------------------

        pos = np.argmax(pwr_waveform)
        if pos < low_position_max_power or pos > high_position_max_power:
            waveforms_ok[i] = False
            continue

    return waveforms_ok


def lrm_waveform_qc_checks(
    pwr_waveform_20_ku=None,
    echo_scale_factor_20_ku=None,
    echo_scale_pwr_20_ku=None,
    total_power_threshold=3e-16,
    low_peakiness_threshold=0.85,
    high_peakiness_threshold=2.8,
):
    """
    Inputs:
    pwr_waveform_20_ku   :  numpy.ndarray of shape (num_measurements, waveform_numbins).
                    waveform_numbins is 128 (LRM) or 1024 (SIN)
                   This is the array returned by :
                   waveforms = nc.variables['pwr_waveform_20_ku'][:].data

    Return values:

    waveforms_ok :  boolean array of True (waveform ok), False (waveform not suitable)

    """

    n_total_power_failed = 0
    n_peakiness_low_failed = 0
    n_peakiness_high_failed = 0
    n_le_failed = 0

    if not np.any(pwr_waveform_20_ku):
        log.error(
            "No pwr_waveform_20_ku waveforms passed to waveform_qc_checks function"
        )
        sys.exit()

    n_waveforms, waveform_size = np.shape(pwr_waveform_20_ku)
    if waveform_size == 128:
        lrm_mode = True
    elif waveform_size == 1024:
        lrm_mode = False
    else:
        log.error("pwr_waveform_20_ku size must be (,128) for LRM or (,1024) for SIN")
        sys.exit()

    waveforms_ok = np.ones(n_waveforms, dtype=bool)

    # if SIN mode just return all ok
    if not lrm_mode:
        return waveforms_ok

    # Perform check on each waveform
    for i, pwr_waveform in enumerate(pwr_waveform_20_ku):
        # debug plot waveform
        # if 0:
        #     import matplotlib.pyplot as plt
        #     fig, ax1 = plt.subplots()
        #     ax1.plot(pwr_waveform)
        #     plt.show()

        if echo_scale_factor_20_ku is not None:
            echo_scale_factor = echo_scale_factor_20_ku[i]
            echo_scale_pwr = echo_scale_pwr_20_ku[i]

            # -----------------------------------------------------------------------------
            #  Check waveform total power > threshold (3e-16 )
            # -----------------------------------------------------------------------------

            total_power = np.sum(
                pwr_waveform * echo_scale_factor * (2.0**echo_scale_pwr)
            )
            if total_power < total_power_threshold:
                waveforms_ok[i] = False
                n_total_power_failed += 1
                continue

        # -----------------------------------------------------------------------------
        #  Check waveform peakiness
        # -----------------------------------------------------------------------------

        peakiness = 64 * np.max(pwr_waveform) / np.sum(pwr_waveform)

        if peakiness < low_peakiness_threshold:
            waveforms_ok[i] = False
            n_peakiness_low_failed += 1
            # if 0:
            #     import matplotlib.pyplot as plt

            #     fig, ax1 = plt.subplots()
            #     ax1.plot(pwr_waveform)
            #     plt.title(f"{i}: Peakiness {peakiness}")
            #     plt.show()
            continue
        if peakiness > high_peakiness_threshold:
            waveforms_ok[i] = False
            n_peakiness_high_failed += 1
            continue

        # ---------------------------------------------------------------------
        #  Check Leading Edge check: sum bins 0-31 and 32-127. Left must be
        #  less than 0.5 of right.
        # ---------------------------------------------------------------------

        left = np.sum(pwr_waveform[0:32])
        right = np.sum(pwr_waveform[32:128])
        if left > (0.5 * right):
            waveforms_ok[i] = False
            n_le_failed += 1

            # if 0:
            #     import matplotlib.pyplot as plt

            #     fig, ax1 = plt.subplots()
            #     ax1.plot(pwr_waveform)
            #     plt.title(f"{i}: Peakiness {peakiness:.2f} Power {total_power}")
            #     plt.show()

            continue

        # if 0:
        #     import matplotlib.pyplot as plt

        #     fig, ax1 = plt.subplots()
        #     ax1.plot(pwr_waveform)
        #     plt.title(f"{i}: Peakiness {peakiness:.2f} Power {total_power}")
        #     plt.show()

    log.debug(
        "Total power test failed: %d : %.2f%%",
        n_total_power_failed,
        (100.0 * n_total_power_failed) / n_waveforms,
    )
    log.debug(
        "Peakiness low test failed: %d : %.2f%%",
        n_peakiness_low_failed,
        (100.0 * n_peakiness_low_failed) / n_waveforms,
    )
    log.debug(
        "Peakiness high test failed: %d : %.2f%%",
        n_peakiness_high_failed,
        (100.0 * n_peakiness_high_failed) / n_waveforms,
    )
    log.debug(
        "Leading Edge test failed: %d : %.2f%%",
        n_le_failed,
        (100.0 * n_le_failed) / n_waveforms,
    )

    return waveforms_ok
