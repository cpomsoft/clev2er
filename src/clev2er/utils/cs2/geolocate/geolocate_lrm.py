"""LRM geolocation functions
"""
import logging
import math
from typing import Tuple

import numpy as np
import pyproj
from netCDF4 import Dataset  # pylint:disable=E0611
from pyproj import Transformer

from clev2er.utils.cs2.geolocate import lrm_slope

# too-many-statements, pylint: disable=R0915
# too-many-locals, pylint: disable=R0914
# pylint: disable=R0801

log = logging.getLogger(__name__)


def geolocate_lrm(
    l1b: Dataset,
    config: dict,
    surface_type_20_ku: np.ndarray,
    range_cor_20_ku: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Perform slope correction index to get alt/azimuth

    Use alt/azimuth/range to get lat/lon/height. Return lat/lon/heights

    Args:
        l1b (np.ndarray): CS2 L1b dataset
        config (dict): configuration dictionary
        slope_model_dir (str): path of slope model files
        surface_type_20_ku (np.ndarray): surface type
        range_cor_20_ku (np.ndarray): corrected range

    Returns:
        _type_: _description_
    """

    # slope model file name taken from config file, path from slope_model_dir
    log.info("Inside geolocate_lrm")
    slp_model_file = config["slope_models"]["model_file"]
    num_height = len(l1b["alt_20_ku"])
    log.debug("Number of L1 measurements: %d", num_height)
    height_20_ku = np.zeros(num_height)
    lat_poca_20_ku = np.zeros(num_height)
    lon_poca_20_ku = np.zeros(num_height)
    slope = lrm_slope.prepare_slope(slp_model_file)
    lat_20_ku = l1b["lat_20_ku"][:]
    lon_20_ku = l1b["lon_20_ku"][:]
    alt_20_ku = l1b["alt_20_ku"][:]

    log_completed = 10
    nrec = num_height
    log.info("Processing %d records", nrec)
    do_sdop = np.full(num_height, False)

    for i in range(nrec):
        log.debug("processing record %d", i)
        complete = (i + 1) * 100.0 / nrec
        if complete >= log_completed:
            log_completed = log_completed + 10
            log.info("Completed %d %%", int(complete))
        #       Check if this record is land-ice
        lat = lat_20_ku[i]
        lon = lon_20_ku[i]
        alt = alt_20_ku[i]

        if surface_type_20_ku[i] == 1:  # grounded ice type
            if np.isfinite(range_cor_20_ku[i]):
                range_1 = range_cor_20_ku[i]

                error, att, azimuth, meridional, zonal = lrm_slope.do_slope(
                    lat,
                    lon,
                    alt,
                    slope,
                    slp_model_file,
                    config["geophysical"]["eccentricity"],
                    config["geophysical"]["earth_semi_major"],
                )

                log.debug(
                    "Att %s %s azi %s %s %s",
                    att,
                    str(math.degrees(att)),
                    azimuth,
                    str(math.degrees(azimuth)),
                    str(math.degrees(azimuth)),
                )

                if error == 0:
                    log.debug("Applying slope")
                    height, lat_cor, lon_cor = lrm_slope.proc_elev(
                        lat, lon, alt, range_1, att, azimuth, meridional, zonal
                    )
                    do_sdop[i] = True

                    log.debug(
                        "height %s from %s,%s to %s, %s",
                        str(height),
                        str(lat),
                        str(lon),
                        str(math.degrees(lat_cor)),
                        str(math.degrees(lon_cor)),
                    )
                    height_20_ku[i] = height

                    lat_poca_20_ku[i] = math.degrees(lat_cor)
                    lon_poca_20_ku[i] = math.degrees(lon_cor)
                    lat_20_ku[i] = lat_poca_20_ku[i]
                    lon_20_ku[i] = lon_poca_20_ku[i]
                else:
                    # Slope cor error
                    log.debug("Slope cor error")
                    height_20_ku[i] = np.nan
                    lat_20_ku[i] = lat
                    lon_20_ku[i] = lon % 360.0
            else:
                # range used for slope correction is masked
                log.debug("range used for slope correction is masked")
                height_20_ku[i] = np.nan
                lat_20_ku[i] = lat
                lon_20_ku[i] = lon % 360.0
        else:
            # Not continental ice, so don't try and slope correct
            height_20_ku[i] = alt - range_cor_20_ku[i]
            lat_20_ku[i] = lat
            lon_20_ku[i] = lon % 360.0

    # Slope Doppler Correction
    idx = np.where(do_sdop)[0]

    if len(idx) > 0:
        ecef = pyproj.Proj(proj="geocent", ellps="WGS84", datum="WGS84")
        lla = pyproj.Proj(proj="latlong", ellps="WGS84", datum="WGS84")
        trans = Transformer.from_proj(lla, ecef, always_xy=True)

        sat_x, sat_y, sat_z = trans.transform(  # pylint: disable=E0633
            xx=l1b["lon_20_ku"][idx],
            yy=l1b["lat_20_ku"][idx],
            zz=l1b["alt_20_ku"][idx],
            radians=False,
        )
        ech_x, ech_y, ech_z = trans.transform(  # pylint: disable=E0633
            xx=lon_poca_20_ku[idx],
            yy=lat_poca_20_ku[idx],
            zz=height_20_ku[idx],
            radians=False,
        )

        sdop = lrm_slope.slope_doppler(
            sat_x,
            sat_y,
            sat_z,
            ech_x,
            ech_y,
            ech_z,
            l1b["sat_vel_vec_20_ku"][idx, :],
            config["instrument"]["chirp_slope"],
            config["instrument"]["wavelength"],
            config["geophysical"]["speed_light"],
        )

        height_20_ku[idx] += l1b["dop_cor_20_ku"][idx]
        height_20_ku[idx] -= sdop

    return height_20_ku, lat_20_ku, lon_20_ku
