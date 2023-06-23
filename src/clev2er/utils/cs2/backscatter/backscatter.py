"""
Functions to compute backscatter.

Functions:
----------
def cs_counts_to_watts( pwr_cnt, lin_fact, pow2_fact ):
    Converts from counts to watts.

def compute_backscatter( rx_pow_w, range_m, roll_deg, pitch_deg, tx_pow_w,
                         ellipse_semi_major_m = 6378137.0, speed_of_light_ms = 2.99792458E+08,
                         effective_pulse_len_s = 4.183e-9, ant_gain_linear = 18197.008586099826, 
                         wavelength_m = 2.2084e-2,
                         bandwidth_hz = 320.0e6, beam_angle_az_deg = 1.06, 
                         beam_angle_el_deg = 1.1992,
                         misp_roll_bias_deg = 0, misp_pitch_bias_deg = 0,
                         sigma_bias = 0, sigma_loss_const_db = 0,
                         misp_mode = 0, rough_mode = 0 ):
    Converts watts to backscatter using range, transmitted power, and pointing information. 
Unit Tests:
----------

The __main__ section includes the unit tests of the retracker.
These are run from the command line as follows:
> python backscatter

"""

import numpy as np

# too-many-arguments, pylint: disable=R0913
# too-many-locals, pylint: disable=R0914


def cs_counts_to_watts(pwr_cnt, lin_fact, pow2_fact):
    """Convert CryoSat2 waveform counts to Watts.

    Parameters
    ----------
    pwr_cnt : float
        Power in waveform counts.
    lin_fact : float
        Linear conversion factor from L1b data ('echo_scale_factor')
    pow2_fact : float
        Power of 2 conversion factor from L1b data ('echo_scale_pwr').

    Returns
    -------
    float
        Power in Watts measured at the antenna.

    """
    return pwr_cnt * lin_fact * np.power(2.0, pow2_fact)


def compute_backscatter(
    rx_pow_w,
    range_m,
    roll_deg,
    pitch_deg,
    tx_pow_w,
    ellipse_semi_major_m=6378137.0,
    speed_of_light_ms=2.99792458e08,
    effective_pulse_len_s=4.183e-9,
    ant_gain_linear=18197.008586099826,
    wavelength_m=2.2084e-2,
    bandwidth_hz=320.0e6,
    beam_angle_az_deg=1.06,
    beam_angle_el_deg=1.1992,
    misp_roll_bias_deg=0,
    misp_pitch_bias_deg=0,
    sigma_bias=0,
    sigma_loss_const_db=0,
    misp_mode=0,
    rough_mode=0,
):
    """Compute backscatter from measured power and range, with optional corrections
    for mispointing and roughness.

    Parameters
    ----------
    rx_pow_w : float
        Measured received power in watts
    range_m : float
        Measured range to the surface in meters.
    roll_deg : float
        Roll angle of the platform in degrees.
    pitch_deg : float
        Pitch angle of the platform in degrees.
    tx_pow_w : float
        Transmitted power in watts.
    ellipse_semi_major_m : float
        Semi-major axis of the ellipsoid in meters. Defaults to WGS84.
    speed_of_light_ms : float
        Speed of light in meters. Defaults to standard value.
    effective_pulse_len_s : float
        Effective pulse length of the transmitted pulse. Defaults to the CS2 value.
    ant_gain_linear : float
        Antenna gain expressed in linear units (not dB). Defaults to the CS2 value.
    wavelength_m : float
        Wavelength of the altimeter in meters. Defaults to the CS2 value.
    bandwidth_hz : float
        Bandwidth of the pulse in hertz. Defaults to the CS2 value.
    beam_angle_az_deg : float
        Azimuth beam angle of the elliptical antenna pattern. Defaults to the CS2 value.
    beam_angle_el_deg : float
        Elevation beam angle of the elliptical antenna pattern. Defaults to the CS2 value.
    misp_roll_bias_deg : float
        Optional bias to apply to measured roll. Defaults to zero.
    misp_pitch_bias_deg : type
        Optional bias to apply to measured pitch. Defaults to zero.
    sigma_bias : type
        Optional bias to apply to returned backscatter. Defaults to zero.
    sigma_loss_const_db : type
        Optional loss constant to apply to returned backscatter. Defaults to zero.
    misp_mode : int
        Method to use to compensate for the mispointing. Defaults to 0 (no compensation)
    rough_mode : int
        Method to use to compensate for the surface roughness. Defaults to 0 (no compensation)

    Returns
    -------
    float
        Computed surface backscatter in dB.

    Examples
    --------
    A simple usage example:

    watts = cs_counts_to_watts( counts, echo_scale_factor, echo_scale_pwr )
    sigma0 = compute_backscatter( watts, range_m, roll_deg, pitch_deg, tx_pow_w )
    """

    gamma = (2.0 / np.log(2.0)) * np.power(
        np.sin(
            1.0
            / (
                1.0 / np.radians(beam_angle_az_deg)
                + 1.0 / np.radians(beam_angle_el_deg)
            )
        ),
        2.0,
    )
    power_ratio_db = 10.0 * np.log10(rx_pow_w / tx_pow_w)
    sigma_calc_const_db = 10.0 * np.log10(
        (
            speed_of_light_ms
            * np.pi
            * np.power(wavelength_m, 2.0)
            * np.power(ant_gain_linear, 2.0)
            * effective_pulse_len_s
        )
        / (
            np.power(4.0 * np.pi * range_m, 3.0)
            * ((range_m + ellipse_semi_major_m) / ellipse_semi_major_m)
        )
    )
    mispoint_cor_lin = 0
    if misp_mode == 1:
        mispoint_rad = np.sqrt(
            np.power(np.radians(roll_deg) + np.radians(misp_roll_bias_deg), 2.0)
            + np.power(np.radians(pitch_deg) + np.radians(misp_pitch_bias_deg), 2.0)
        )

        mispoint_cor_lin = -4.0 * np.power(np.sin(mispoint_rad), 2.0) / gamma

    rough_cor_lin = 0.0
    if rough_mode == 1:
        rough_cor_lin = 4.0 * speed_of_light_ms / (gamma * range_m * bandwidth_hz)

        if misp_mode == 1:
            rough_cor_lin *= (
                np.cos(2.0 * mispoint_rad)
                - np.power(np.sin(2.0 * mispoint_rad), 2.0) / gamma
            )

    misp_and_surf_db = 10.0 * (mispoint_cor_lin + rough_cor_lin) / np.log(10.0)

    return (
        power_ratio_db
        - sigma_calc_const_db
        + sigma_loss_const_db
        - misp_and_surf_db
        + sigma_bias
    )


# # ----------------------------------------------------------------------
# #  Main Section: Runs Unit Tests
# # ----------------------------------------------------------------------
# if __name__ == "__main__":
#     print("Unit test started")

#     print("\nTesting counts to watts conversion")
#     expected_watts = 8.79374e-14
#     watts = cs_counts_to_watts(59486.9, 852162018.0e-9, -59.0)
#     print("  Watts", watts, "expected", expected_watts)
#     # Tolerance chosen as limit of precision in BKP file
#     assert math.isclose(watts, expected_watts, rel_tol=1e-6)
#     print("  Test PASSED")

#     # Values taken from VT_05 LIRT BKP record 1
#     rtrk_pow_w = 1.284341e-13
#     rng_m = 7.513549e05
#     roll_deg = -1.442252e-01
#     pitch_deg = -4.156750e-02
#     tx_pow_w = 2.884032e01
#     expected_sigma0 = 4.735963e00
#     print("\nTesting watts to backscatter conversion")
#     sigma0 = compute_backscatter(
#         rtrk_pow_w, rng_m, roll_deg, pitch_deg, tx_pow_w, sigma_bias=-3.45
#     )
#     print("  Backscatter", sigma0, "expected", expected_sigma0)
#     assert math.isclose(sigma0, expected_sigma0, rel_tol=1e-6)
#     print("  Test PASSED")
