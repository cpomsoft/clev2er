""" SARIN Phase funcs"""
import logging
import warnings

import numpy as np
import scipy.optimize
from scipy.optimize import OptimizeWarning

# too-many-branches, pylint: disable=R0912
# too-many-arguments, pylint: disable=R0913
# too-many-locals, pylint: disable=R0914


warnings.simplefilter("error", OptimizeWarning)
log = logging.getLogger(__name__)


# to be done...
# ----
# 1) Harmonise the versions in terms of parameter order
# 2) Add a Cython version that uses the original C code
# 3) Try and get the Python versions closer to C in terms of weighting and Jacobian
#       May be difficult without the ability to alter the internals of the python fits


class SINLocateError(Exception):
    """to be documented by djb"""

    def __init__(self, msg: str):
        self.msg = msg

    def __str__(self) -> str:
        return repr(self.msg)


def phase_func_least_squares(ttt, params):
    """to be documented by djb

    Args:
        ttt (_type_): _description_
        params (_type_): _description_

    Returns:
        _type_: _description_
    """
    slope = params[0]
    constant = params[1]
    tt0 = params[2]
    log.debug("slope %f constant %f tt0 %f", slope, constant, tt0)
    data = np.zeros(len(ttt))
    for i, tvv in enumerate(ttt):
        if tvv < tt0:
            data[i] = constant
        else:
            data[i] = slope * (tvv - tt0) + constant
    return data


def resid_least_squares(vals, *args):
    """to be documented by djb

    Args:
        vals (_type_): _description_

    Returns:
        _type_: _description_
    """
    actual = args[1]
    coherence = args[2]
    ccx = coherence**3.0 / (1.0 - coherence**2.0)
    ddd = phase_func_least_squares(args[0], [vals[1], vals[0], vals[2]]) - actual
    # No idea why /2.0 but's that how it is in the C
    res = 4.0 * ccx * np.sin(ddd / 2.0) * np.sin(ddd / 2.0)
    return res


def jac_least_squares(vals, *args):
    """to be documented by djb

    Args:
        vals (_type_): _description_

    Returns:
        _type_: _description_
    """
    ttt = args[0]
    data = np.zeros((len(ttt), 3))

    actual = args[1]
    ddd = phase_func_least_squares(args[0], [vals[1], vals[0], vals[2]]) - actual

    for i, tvv in enumerate(ttt):
        # No idea if I need the sin/cos terms from alpha/beta in the NR code in here
        ssd = np.sin(ddd[i])
        # ssd = 1.0
        if tvv < vals[2]:
            data[i, 0] = 1 * ssd
            data[i, 1] = 0
            data[i, 2] = 0
        else:
            data[i, 0] = 1
            data[i, 1] = -1.0 * vals[1] * ssd
            data[i, 2] = tvv - vals[2] * ssd
    return data


# Has slope and constant swapped compared with least_squares version.
# Needed because the two versions have the guess in different orders.
def jac_curve_fit(vals, *args):
    """to be documented by djb

    Args:
        vals (_type_): _description_

    Returns:
        _type_: _description_
    """
    data = np.zeros((len(vals), 3))

    for i, tvv in enumerate(vals):
        if tvv < args[2]:
            data[i, 0] = 0
            data[i, 1] = 1
            data[i, 2] = 0
        else:
            data[i, 0] = tvv - args[2]
            data[i, 1] = 1
            data[i, 2] = -1.0 * args[0]
    return data


def phase_func_curve_fit(ttt, slope, constant, tt0):
    """to be documented by djb

    Args:
        ttt (_type_): _description_
        slope (_type_): _description_
        constant (_type_): _description_
        tt0 (_type_): _description_

    Returns:
        _type_: _description_
    """
    log.debug("slope %f constant %f tt0 %f", slope, constant, tt0)
    data = np.zeros(len(ttt))
    for i, tvv in enumerate(ttt):
        if tvv < tt0:
            data[i] = constant
        else:
            data[i] = slope * (tvv - tt0) + constant
    return data


def extract_phase_window(phase_in, phase_window_start, phase_window_width, unwrap=True):
    """to be documented by djb

    Args:
        phase_in (_type_): _description_
        phase_window_start (_type_): _description_
        phase_window_width (_type_): _description_
        unwrap (bool, optional): _description_. Defaults to True.

    Returns:
        _type_: _description_
    """
    if unwrap:
        phase_i = np.copy(
            phase_in[phase_window_start : phase_window_start + phase_window_width]
        )
        phase_o = np.unwrap(phase_i)
        while np.median(phase_o) < -np.pi:
            phase_o = phase_o + 2.0 * np.pi
        while np.median(phase_o) > np.pi:
            phase_o = phase_o - 2.0 * np.pi
        return phase_o
    return phase_in[phase_window_start : phase_window_start + phase_window_width]


def phase_fit_lsq(phase, coherence, position, bad_1, bad_2, bad_3, config):
    """to be documented by djb

    Args:
        phase (_type_): _description_
        coherence (_type_): _description_
        position (_type_): _description_
        bad_1 (_type_): _description_
        bad_2 (_type_): _description_
        bad_3 (_type_): _description_
        config (_type_): _description_

    Returns:
        _type_: _description_
    """
    window_start = int(
        np.floor(position) - config["sin_geolocation"]["phase_window_width"] / 2
    )
    if window_start < 0:
        return np.nan, bad_1, bad_2, bad_3
    if window_start + config["sin_geolocation"]["phase_window_width"] >= len(phase):
        return np.nan, bad_1, bad_2, bad_3
    phase_data = extract_phase_window(
        phase,
        window_start,
        config["sin_geolocation"]["phase_window_width"],
        unwrap=False,
    )
    coherence_data = coherence[
        window_start : window_start + config["sin_geolocation"]["phase_window_width"]
    ]
    guess = [
        np.mean(
            np.unwrap(
                phase_data[0 : int(config["sin_geolocation"]["phase_window_width"] / 2)]
            )
        ),
        0.0,
        position,
    ]

    # x vals need to be in a list or it gets spread across the tuple
    res_1 = scipy.optimize.least_squares(
        resid_least_squares,
        guess,
        args=(
            np.asarray(
                np.arange(
                    window_start,
                    window_start + config["sin_geolocation"]["phase_window_width"],
                    1,
                )
            ),
            phase_data,
            coherence_data,
        ),
        method="lm",  # jac=jac_least_squares,
        ftol=1.0e-6,
        max_nfev=15 * config["sin_geolocation"]["phase_window_width"],
    )
    fits = res_1["x"][0]

    if "do_three" in config["sin_geolocation"]:
        guess = [
            np.mean(
                np.unwrap(
                    phase_data[
                        0 : int(config["sin_geolocation"]["phase_window_width"] / 2)
                    ]
                )
            ),
            0.05,
            position,
        ]

        # x vals need to be in a list or it gets spread across the tuple
        res_2 = scipy.optimize.least_squares(
            resid_least_squares,
            guess,
            args=(
                np.asarray(
                    np.arange(
                        window_start,
                        window_start + config["sin_geolocation"]["phase_window_width"],
                        1,
                    )
                ),
                phase_data,
                coherence_data,
            ),
            method="lm",  # jac=jac_least_squares,
            ftol=1.0e-6,
            max_nfev=15 * config["sin_geolocation"]["phase_window_width"],
        )
        guess = [
            np.mean(
                np.unwrap(
                    phase_data[
                        0 : int(config["sin_geolocation"]["phase_window_width"] / 2)
                    ]
                )
            ),
            -0.05,
            position,
        ]

        # x vals need to be in a list or it gets spread across the tuple
        res_3 = scipy.optimize.least_squares(
            resid_least_squares,
            guess,
            args=(
                np.asarray(
                    np.arange(
                        window_start,
                        window_start + config["sin_geolocation"]["phase_window_width"],
                        1,
                    )
                ),
                phase_data,
                coherence_data,
            ),
            method="lm",  # jac=jac_least_squares,
            ftol=1.0e-6,
            max_nfev=15 * config["sin_geolocation"]["phase_window_width"],
        )
        if res_3["cost"] < res_2["cost"] and res_3["cost"] < res_1["cost"]:
            fits = res_3["x"][0]
        elif res_2["cost"] < res_1["cost"] and res_2["cost"] < res_3["cost"]:
            fits = res_2["x"][0]
        else:
            fits = res_1["x"][0]
    if np.abs(fits) > np.pi:
        fits = np.nan
    return fits, bad_1, bad_2, bad_3


def phase_fit_cuf(phase, coherence, position, bad_1, bad_2, bad_3, config):
    """to be documented by djb

    Args:
        phase (_type_): _description_
        coherence (_type_): _description_
        position (_type_): _description_
        bad_1 (_type_): _description_
        bad_2 (_type_): _description_
        bad_3 (_type_): _description_
        config (_type_): _description_

    Returns:
        _type_: _description_
    """
    window_start = int(
        np.floor(position) - config["sin_geolocation"]["phase_window_width"] / 2
    )

    if window_start < 0:
        return np.nan, bad_1, bad_2, bad_3
    if window_start + config["sin_geolocation"]["phase_window_width"] >= len(phase):
        return np.nan, bad_1, bad_2, bad_3
    if np.ma.is_masked(position):
        return np.nan, bad_1, bad_2, bad_3

    phase_data = extract_phase_window(
        phase[:],
        window_start,
        config["sin_geolocation"]["phase_window_width"],
        unwrap=True,
    )

    const_guess = np.mean(
        phase_data[0 : int(config["sin_geolocation"]["phase_window_width"] / 2)]
    )
    guess = np.asarray([0.0, const_guess, position], dtype=np.float64)
    coh = coherence[
        int(window_start) : int(
            window_start + config["sin_geolocation"]["phase_window_width"]
        )
    ]
    # x vals need to be in a list or it gets spread across the tuple
    ttt = np.asarray(
        np.arange(
            window_start,
            window_start + config["sin_geolocation"]["phase_window_width"],
            1,
        )
    )
    www = np.sqrt(1.0 / ((coh**3) / (1 - coh**2)))

    try:
        res_1 = scipy.optimize.curve_fit(
            phase_func_curve_fit,
            ttt,
            phase_data,
            guess,
            sigma=www,  # jac=jac_curve_fit,
            method="lm",
        )
        fits = res_1[0][1]
        resid_1 = np.sum(
            np.power(
                phase_func_curve_fit(ttt, res_1[0][0], res_1[0][1], res_1[0][2])
                - phase_data,
                2.0,
            )
        )
    except (OptimizeWarning, RuntimeError):
        fits = np.nan
        resid_1 = np.inf
        bad_1 = bad_1 + 1

    if "do_three" in config["sin_geolocation"]:
        guess = np.asarray([0.05, const_guess, position], dtype=np.float64)
        try:
            res_2 = scipy.optimize.curve_fit(
                phase_func_curve_fit,
                ttt,
                phase_data,
                guess,
                sigma=www,  # jac=jac_curve_fit,
                method="lm",
            )
            resid_2 = np.sum(
                np.power(
                    phase_func_curve_fit(ttt, res_2[0][0], res_2[0][1], res_2[0][2])
                    - phase_data,
                    2.0,
                )
            )
        except (OptimizeWarning, RuntimeError):
            resid_2 = np.inf
            bad_2 = bad_2 + 1

        guess = np.asarray([-0.05, const_guess, position], dtype=np.float64)
        try:
            res_3 = scipy.optimize.curve_fit(
                phase_func_curve_fit,
                ttt,
                phase_data,
                guess,
                sigma=www,  # jac=jac_curve_fit,
                method="lm",
            )
            resid_3 = np.sum(
                np.power(
                    phase_func_curve_fit(ttt, res_3[0][0], res_3[0][1], res_3[0][2])
                    - phase_data,
                    2.0,
                )
            )
        except (OptimizeWarning, RuntimeError):
            resid_3 = np.inf
            bad_3 = bad_3 + 1

        try:
            if resid_3 < resid_2 and resid_3 < resid_1:
                fits = res_3[0][1]
            elif resid_2 < resid_3 and resid_2 < resid_1:
                fits = res_2[0][1]
            else:
                fits = res_1[0][1]
        except UnboundLocalError:
            # Possible to have none of the results defined so catch that
            fits = np.nan

    if np.abs(fits) > np.pi:
        fits = np.nan
    return fits, bad_1, bad_2, bad_3


def phase_fit_sample(phase, coherence, position, bad_1, bad_2, bad_3, config=None):
    """Requires documenting by djb

    Args:
        phase (_type_): _description_
        coherence (_type_): _description_
        position (_type_): _description_
        bad_1 (_type_): _description_
        bad_2 (_type_): _description_
        bad_3 (_type_): _description_
        config (_type_, optional): _description_. Defaults to None.

    Raises:
        SINLocateError: _description_
        Exception: _description_
        SINLocateError: _description_

    Returns:
        _type_: _description_
    """
    # if phase_fit_sample.once == 0:
    #     phase_fit_sample.once = 1
    #     log.info(
    #         "Performing phase sampling with method "
    #         + config["sin_geolocation"]["window_method"]
    #     )

    if np.ma.is_masked(position):
        raise SINLocateError("Bad retrack")

    ttt = int(np.rint(position))
    if config is None:
        return phase[:ttt]

    wstart = ttt - int(config["sin_geolocation"]["phase_window_width"] / 2)
    wend = ttt + int(config["sin_geolocation"]["phase_window_width"] / 2)

    if "window_method" in config["sin_geolocation"]:
        if config["sin_geolocation"]["window_method"] == "max":
            try:
                ccc = np.nanmax(coherence[wstart:wend])
                pos = np.nanargmax(coherence[wstart:wend])
                if not isinstance(pos, np.int64):
                    pos = pos[0]
                ppp = np.nanmean(phase[wstart + pos])
            except ValueError:
                ccc = np.nan
                ppp = np.nan
        elif config["sin_geolocation"]["window_method"] == "interp":
            low = int(np.floor(position))
            high = int(np.ceil(position))
            frac = float(position - low)
            ccc = (1.0 - frac) * coherence[low] + frac * coherence[high]
            ppp = (1.0 - frac) * phase[low] + frac * phase[high]
        elif config["sin_geolocation"]["window_method"] == "sample":
            ccc = coherence[ttt]
            ppp = phase[ttt]
        else:
            ppp = np.nanmean(phase[wstart:wend])
            ccc = np.nanmean(coherence[wstart:wend])
    else:
        raise ValueError(
            "Invalid config: window phase extraction requested without a method"
        )

    if "mask" in config["sin_geolocation"]:
        if config["sin_geolocation"]["mask"]:
            if "mask_coh_ths" in config["sin_geolocation"]:
                ths = config["sin_geolocation"]["mask_coh_ths"]
            else:
                ths = 0.8
            if ccc < ths:
                ppp = np.nan
                raise SINLocateError(
                    "Phase retrieval failed due to coherence threshold"
                )

    return ppp, bad_1, bad_2, bad_3


# phase_fit_sample.once = 0
