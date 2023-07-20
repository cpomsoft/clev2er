"""geolocate_sin.py

"""
import logging

import numpy as np
from scipy.optimize import OptimizeWarning

from clev2er.utils.cs2.geolocate import sarin_phase
from clev2er.utils.cs2.geolocate.lrm_slope import (
    ecef_to_llh_pyproj,
    llh_to_ecef_pyproj,
)

# too-many-branches, pylint: disable=R0912
# too-many-arguments, pylint: disable=R0913
# too-many-locals, pylint: disable=R0914
# too-many-statements, pylint: disable=R0915
# pylint: disable=R0801

log = logging.getLogger(__name__)


def solve_eqn(aaa, bbb, base_vec, crf_centre):
    """djb to document

    Args:
        aaa (_type_): _description_
        bbb (_type_): _description_
        base_vec (_type_): _description_
        crf_centre (_type_): _description_

    Returns:
        _type_: _description_
    """
    crf_point = np.zeros(3)

    d_xplus = 2.0 * bbb * base_vec[0] / np.power(base_vec[2], 2.0)

    d_befosqrt = (
        4.0
        * np.power(bbb, 2.0)
        * np.power(base_vec[0], 2.0)
        / np.power(base_vec[2], 4.0)
    )
    d_befosqrt -= (
        4.0
        * (np.power(base_vec[0], 2.0) / np.power(base_vec[2], 2.0) + 1.0)
        * (np.power(bbb, 2.0) / np.power(base_vec[2], 2.0) - aaa)
    )

    d_xplus += np.sqrt(d_befosqrt)
    d_xplus /= 2.0 * (np.power(base_vec[0], 2.0) / np.power(base_vec[2], 2.0) + 1.0)

    d_xxplus = d_xplus + crf_centre[0]

    d_zplus = (bbb - base_vec[0] * d_xplus) / base_vec[2]

    d_zzplus = d_zplus + crf_centre[2]

    d_xminus = 2.0 * bbb * base_vec[0] / np.power(base_vec[2], 2.0)
    d_xminus -= np.sqrt(d_befosqrt)
    d_xminus /= 2.0 * (np.power(base_vec[0], 2.0) / np.power(base_vec[2], 2.0) + 1.0)

    d_xxminus = d_xminus + crf_centre[0]

    d_zminus = (bbb - base_vec[0] * d_xminus) / base_vec[2]

    d_zzminus = d_zminus + crf_centre[2]

    if d_xxplus > d_xxminus:
        crf_point[0] = d_xxplus
        crf_point[2] = d_zzplus

    if d_xxminus > d_xxplus:
        crf_point[0] = d_xxminus
        crf_point[2] = d_zzminus

    return crf_point


def get_crf_in_efc(lon, lat, alt, vel_vec):
    """djb to document

    Args:
        lon (_type_): _description_
        lat (_type_): _description_
        alt (_type_): _description_
        vel_vec (_type_): _description_

    Returns:
        _type_: _description_
    """
    crf_axis = np.zeros((3, 3))
    efc_cog = np.zeros(3)
    nad = np.zeros(3)
    nad[0], nad[1], nad[2] = llh_to_ecef_pyproj(lat, lon, 0.0)
    log.debug("NADIR LLH %f %f %f", lat, lon, 0.0)
    log.debug("NADIR EFC %f %f %f len %f", nad[0], nad[1], nad[2], np.linalg.norm(nad))

    efc_cog[0], efc_cog[1], efc_cog[2] = llh_to_ecef_pyproj(lat, lon, alt)

    sat_nad_vec = nad - efc_cog
    log.debug(
        "SAT NAD VEC EFC %f %f %f len %f",
        sat_nad_vec[0],
        sat_nad_vec[1],
        sat_nad_vec[2],
        np.linalg.norm(sat_nad_vec),
    )

    ad_crf_axis1 = sat_nad_vec / np.linalg.norm(sat_nad_vec)
    ad_efc_nv = vel_vec / np.linalg.norm(vel_vec)

    scal_prod = np.dot(ad_crf_axis1, ad_efc_nv)
    ad_temp_vect = np.zeros(3)
    ad_temp_vect[0] = ad_efc_nv[0] - ad_crf_axis1[0] * scal_prod
    ad_temp_vect[1] = ad_efc_nv[1] - ad_crf_axis1[1] * scal_prod
    ad_temp_vect[2] = ad_efc_nv[2] - ad_crf_axis1[2] * scal_prod

    ad_crf_axis2 = ad_temp_vect / np.linalg.norm(ad_temp_vect)
    ad_crf_axis3 = np.cross(ad_crf_axis2, ad_crf_axis1)

    # crf_axis[0, :] = ad_crf_axis1
    # crf_axis[1, :] = ad_crf_axis2
    # crf_axis[2, :] = ad_crf_axis3
    # This fixed a problem, but I don't know if I'm abusing vector orientation here
    crf_axis[:, 0] = ad_crf_axis1
    crf_axis[:, 1] = ad_crf_axis2
    crf_axis[:, 2] = ad_crf_axis3

    return crf_axis, efc_cog


def rotation_matrix(crf_axis):
    """djb to document

    Args:
        crf_axis (_type_): _description_

    Returns:
        _type_: _description_
    """
    rot = np.zeros((3, 3))
    rot[0, 0] = np.dot([1, 0, 0], crf_axis[:, 0])
    rot[0, 1] = np.dot([1, 0, 0], crf_axis[:, 1])
    rot[0, 2] = np.dot([1, 0, 0], crf_axis[:, 2])
    rot[1, 0] = np.dot([0, 1, 0], crf_axis[:, 0])
    rot[1, 1] = np.dot([0, 1, 0], crf_axis[:, 1])
    rot[1, 2] = np.dot([0, 1, 0], crf_axis[:, 2])
    rot[2, 0] = np.dot([0, 0, 1], crf_axis[:, 0])
    rot[2, 1] = np.dot([0, 0, 1], crf_axis[:, 1])
    rot[2, 2] = np.dot([0, 0, 1], crf_axis[:, 2])
    return rot


def angle_to_poca(angle, lat, lon, alt, cor_range, vel_vec, base_vec):
    """djb to document

    Args:
        angle (_type_): _description_
        lat (_type_): _description_
        lon (_type_): _description_
        alt (_type_): _description_
        cor_range (_type_): _description_
        vel_vec (_type_): _description_
        base_vec (_type_): _description_

    Returns:
        _type_: _description_
    """
    #    base_vec[0] = 0.0
    #    base_vec[1] = 0.0
    #    base_vec[2] = -1.0
    log.debug("cor_range %f", cor_range)
    log.debug("alt-range %f", alt - cor_range)
    log.debug("vel_vec %s", str(vel_vec))
    log.debug("base_vec %s", str(base_vec))

    crf_centre = base_vec * (cor_range * np.sin(angle))
    log.debug("crf_centre %s", str(crf_centre))

    radius = cor_range * np.cos(angle)
    log.debug("radius %f", radius)

    aaa = np.power(radius, 2) - np.power(crf_centre[1], 2)
    bbb = base_vec[1] * crf_centre[1]

    crf_point = solve_eqn(aaa, bbb, base_vec, crf_centre)
    log.debug("crf_point %s", str(crf_point))

    try:
        crf_axis, efc_cog = get_crf_in_efc(lon, lat, alt, vel_vec)

    except ValueError as exc:
        log.error("Geolocation failed, Floating point exception: %s", exc)
        return np.nan, np.nan, np.nan
    rot = rotation_matrix(crf_axis)

    efc_vec = np.inner(rot, crf_point)
    log.debug("efc_vec %s len %f", str(efc_vec), np.linalg.norm(efc_vec))
    log.debug("efc_cog %s len %f", str(efc_cog), np.linalg.norm(efc_cog))
    efc_point = efc_vec + efc_cog
    log.debug("efc_point %s len %f", str(efc_point), np.linalg.norm(efc_point))
    lat_poca, lon_poca, elev_poca = ecef_to_llh_pyproj(
        efc_point[0], efc_point[1], efc_point[2]
    )
    log.debug("SAT lat=%f lon=%f h=%f", lat, lon, alt)
    log.debug("POCA lat=%f lon=%f h=%f", lat_poca, lon_poca, elev_poca)
    if lon_poca > 180.0:
        lon_poca -= 360.0

    return lat_poca, lon_poca, elev_poca


def phase_to_angle(
    phase,
    wavelength=0.022084,
    baseline=1.1676,
    inferred_angle_cal_mult=1.02775,
    inferred_angle_cal_add=0.0,
):
    """djb to document

    Args:
        phase (_type_): _description_
        wavelength (float, optional): _description_. Defaults to 0.022084.
        baseline (float, optional): _description_. Defaults to 1.1676.
        inferred_angle_cal_mult (float, optional): _description_. Defaults to 1.02775.
        inferred_angle_cal_add (float, optional): _description_. Defaults to 0.0.

    Returns:
        _type_: _description_
    """
    angle = phase * wavelength
    angle = -1.0 * angle / (2 * np.pi * baseline)

    angle = (inferred_angle_cal_mult * angle) + inferred_angle_cal_add
    return angle


def geolocate_sin(
    l1b, config, dem_ant, dem_grn, range_cor_20_ku, ind_wfm_retrack_20_ku
):
    """djb to document

    Args:
        l1b (_type_): _description_
        config (_type_): _description_
        dem_ant (_type_): _description_
        dem_grn (_type_): _description_
        range_cor_20_ku (_type_): _description_
        ind_wfm_retrack_20_ku (_type_): _description_

    Raises:
        sarin_phase.SINLocateError: _description_
        sarin_phase.SINLocateError: _description_
        sarin_phase.SINLocateError: _description_
        e: _description_

    Returns:
        _type_: _description_
    """
    # Do phase estimation
    # Use phase, vectors to get lat/lon/height

    # Extract parameter arrays from L1 file netcdf object
    lat_20_ku = l1b["lat_20_ku"][:].data
    lon_20_ku = l1b["lon_20_ku"][:].data
    ph_diff_waveform_20_ku = l1b["ph_diff_waveform_20_ku"][:].data
    coherence_waveform_20_ku = l1b["coherence_waveform_20_ku"][:].data
    sat_vel_vec_20_ku = l1b["sat_vel_vec_20_ku"][:].data
    inter_base_vec_20_ku = l1b["inter_base_vec_20_ku"][:].data
    alt_20_ku = l1b["alt_20_ku"][:].data

    # Find number of records
    nrec = len(lat_20_ku)

    # Allocate arrays for intermediate aand output parameters
    height_20_ku = np.zeros(nrec)
    final_lat_20_ku = np.zeros(nrec)
    final_lon_20_ku = np.zeros(nrec)

    angle_20_ku = np.zeros(nrec)

    lat_initial_20_ku = np.zeros(nrec)
    lon_initial_20_ku = np.zeros(nrec)
    lat_unwrap_20_ku = np.zeros(nrec)
    lon_unwrap_20_ku = np.zeros(nrec)
    dem_unwrap_20_ku = np.zeros(nrec)
    angle_unwrap_20_ku = np.zeros(nrec)
    delta_unwrap_h = np.zeros(nrec)
    height_unwrap_20_ku = np.zeros(nrec)

    config_fitter = config["sin_geolocation"]["phase_method"]
    if config_fitter == 1:
        fitter = sarin_phase.phase_fit_lsq
    elif config_fitter == 2:
        fitter = sarin_phase.phase_fit_cuf
    else:
        fitter = (
            sarin_phase.phase_fit_sample
        )  # (sample window) 3: used in config/baseline_b_stage1.yml

    log_completed = 10
    log.info("Processing %d records", nrec)
    bad_1 = 0
    bad_2 = 0
    bad_3 = 0

    log.info(
        "Computing SARIN geolocation with method %s",
        str(config["sin_geolocation"]["phase_method"]),
    )
    log.info("Phase unwrapping is %s", str(config["sin_geolocation"]["unwrap"]))

    # ------------------------------------------------------------------------------
    # Process each record
    # ------------------------------------------------------------------------------

    for i in range(nrec):
        log.debug("processing record %d", i)
        complete = (i + 1) * 100.0 / nrec
        if complete >= log_completed:
            log_completed = log_completed + 10
            log.info("Completed %d%%", int(complete))
        try:
            # Check if inputs are OK
            if (
                ind_wfm_retrack_20_ku[i] == -32768
            ):  # This is the fill value used in stage1
                height_20_ku[i] = np.nan
                final_lat_20_ku[i] = np.nan
                final_lon_20_ku[i] = np.nan
                continue

            # Get the phase

            phase, bad_1, bad_2, bad_3 = fitter(
                ph_diff_waveform_20_ku[i],
                coherence_waveform_20_ku[i],
                ind_wfm_retrack_20_ku[i],
                bad_1,
                bad_2,
                bad_3,
                config,
            )
            if np.isnan(phase):
                raise sarin_phase.SINLocateError("Phase retrieval failed")
            if np.abs(phase) > np.pi:
                raise sarin_phase.SINLocateError("Phase out of bounds")
            # Get angle
            angle = phase_to_angle(phase)
            angle_20_ku[i] = angle

            # Calculate the POCA location and height
            log.debug("-- GEOLOCATING  --")
            lat_poca, lon_poca, elev_poca = angle_to_poca(
                angle,
                lat_20_ku[i],
                lon_20_ku[i],
                alt_20_ku[i],
                range_cor_20_ku[i],
                sat_vel_vec_20_ku[i],
                inter_base_vec_20_ku[i],
            )
            final_lat_20_ku[i] = lat_poca
            final_lon_20_ku[i] = lon_poca
            height_20_ku[i] = elev_poca

            if config["sin_geolocation"]["unwrap"]:
                if phase > 0:
                    unwrap_phase = -2.0 * np.pi + phase
                else:
                    unwrap_phase = 2.0 * np.pi + phase

                angle_unwrap_20_ku[i] = phase_to_angle(unwrap_phase)
                log.debug("-- GEOLOCATING  unwrapped --")
                lat_poca, lon_poca, elev_poca = angle_to_poca(
                    angle_unwrap_20_ku[i],
                    lat_20_ku[i],
                    lon_20_ku[i],
                    alt_20_ku[i],
                    range_cor_20_ku[i],
                    sat_vel_vec_20_ku[i],
                    inter_base_vec_20_ku[i],
                )
                lat_unwrap_20_ku[i] = lat_poca
                lon_unwrap_20_ku[i] = lon_poca
                height_unwrap_20_ku[i] = elev_poca
            else:
                lat_unwrap_20_ku[i] = np.nan
                lon_unwrap_20_ku[i] = np.nan
                dem_unwrap_20_ku[i] = np.nan
                delta_unwrap_h[i] = np.nan

            if (
                height_20_ku[i] > config["sin_geolocation"]["height_max"]
                or height_20_ku[i] < config["sin_geolocation"]["height_min"]
            ):
                raise sarin_phase.SINLocateError("Height out of bounds")
        except OptimizeWarning as exc:
            # Here to catch them for debugging but currently handled before here
            # by defaulting results
            # Doesn't indicate an error, indicates the model not fitting the data
            raise exc
        except sarin_phase.SINLocateError as exc:
            log.debug("Defaulting results. Reason is %s", exc.msg)
            final_lat_20_ku[i] = np.nan
            final_lon_20_ku[i] = np.nan
            height_20_ku[i] = np.nan
            # raise e
    #
    # --------------------------------------------------------------------------
    # --------------------------------------------------------------------------
    if config["sin_geolocation"]["unwrap"]:
        # Get the DEM height at both locations
        if lat_20_ku[0] < 0:
            unwrap_dem = dem_ant.interp_dem(
                lat_unwrap_20_ku, lon_unwrap_20_ku, method="linear", xy_is_latlon=True
            )

            orig_dem = dem_ant.interp_dem(
                final_lat_20_ku, final_lon_20_ku, method="linear", xy_is_latlon=True
            )
        else:
            unwrap_dem = dem_grn.interp_dem(
                lat_unwrap_20_ku, lon_unwrap_20_ku, method="linear", xy_is_latlon=True
            )
            orig_dem = dem_grn.interp_dem(
                final_lat_20_ku, final_lon_20_ku, method="linear", xy_is_latlon=True
            )

        # Work out which is best
        idx = np.where(
            np.bitwise_and(
                np.abs(height_unwrap_20_ku - unwrap_dem)
                < np.abs(height_20_ku - orig_dem),
                np.abs(height_20_ku - orig_dem)
                >= config["sin_geolocation"]["unwrap_trigger_m"],
            )
        )[0]

        lat_initial_20_ku[:] = final_lat_20_ku[:]
        lon_initial_20_ku[:] = final_lon_20_ku[:]

        # Use the alternate solution if better
        if len(idx) > 0:
            height_20_ku[idx] = height_unwrap_20_ku[idx]
            final_lat_20_ku[idx] = lat_unwrap_20_ku[idx]
            final_lon_20_ku[idx] = lon_unwrap_20_ku[idx]
            log.info("Phase unwrapping replaced %d measurements", len(idx))

    log.debug("bad counts 1=%d 2=%d 3=%d", bad_1, bad_2, bad_3)
    log.info("Processed %d records", i + 1)

    return height_20_ku, final_lat_20_ku, final_lon_20_ku
