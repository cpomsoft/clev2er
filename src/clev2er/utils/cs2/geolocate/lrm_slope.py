"""lrm_slope.py
"""
import logging
import math
import struct

import numpy as np
import pyproj
from pyproj import Transformer

# too-many-arguments, pylint: disable=R0913
# too-many-locals, pylint: disable=R0914
# too-many-returns, pylint: disable=R0911


log = logging.getLogger(__name__)

# to be done list
# 1) Consider whether making this a class that only opens the slope file once is a
# better way to go for performance


def llh_to_ecef_pyproj(lat, lon, alt):
    """djb to document

    Args:
        lat (_type_): _description_
        lon (_type_): _description_
        alt (_type_): _description_

    Returns:
        _type_: _description_
    """
    ecef = pyproj.Proj(proj="geocent", ellps="WGS84", datum="WGS84")
    lla = pyproj.Proj(proj="latlong", ellps="WGS84", datum="WGS84")

    trans = Transformer.from_proj(lla, ecef, always_xy=True)

    x, y, z = trans.transform(xx=lon, yy=lat, zz=alt, radians=False)  # pylint: disable=E0633

    return x, y, z


def ecef_to_llh_pyproj(x, y, z):
    """djb to document

    Args:
        x (_type_): _description_
        y (_type_): _description_
        z (_type_): _description_

    Returns:
        _type_: _description_
    """
    ecef = pyproj.Proj(proj="geocent", ellps="WGS84", datum="WGS84")
    lla = pyproj.Proj(proj="latlong", ellps="WGS84", datum="WGS84")

    trans = Transformer.from_proj(ecef, lla, always_xy=True)

    lon, lat, height = trans.transform(xx=x, yy=y, zz=z, radians=False)  # pylint: disable=E0633

    return lat, lon, height


def trans_coord(lat, lon, eccentricity, semimajor):
    """djb to document

    Args:
        lat (_type_): _description_
        lon (_type_): _description_
        eccentricity (_type_): _description_
        semimajor (_type_): _description_

    Returns:
        _type_: _description_
    """
    # eccentricity = math.sqrt( 2.0*0.00335281066 - 0.00335281066*0.00335281066 )
    # semimajor = 6378137.000

    lat_rad = math.radians(lat)

    lon_rad = math.radians(lon)

    meridional = semimajor * (1.0 - eccentricity * eccentricity)
    temp = eccentricity * math.sin(lat_rad)

    temp *= temp

    temp = 1.0 - temp

    meridional /= math.sqrt(temp * temp * temp)

    zonal = semimajor * math.cos(lat_rad)

    zonal /= math.sqrt(temp)

    x_coord = 2.0 * meridional * math.sin(((np.pi / 2.0) - math.fabs(lat_rad)) / 2.0)

    y_coord = x_coord * math.sin(lon_rad)

    x_coord *= math.cos(lon_rad)

    return x_coord, y_coord, meridional, zonal


def setup_slopes(x, y, lat, slope):
    """djb to document

    Args:
        x (_type_): _description_
        y (_type_): _description_
        lat (_type_): _description_
        slope (_type_): _description_

    Returns:
        _type_: _description_
    """
    error = 1

    m = 0
    n = 0
    p = 0.0
    q = 0.0
    model = 0

    if lat < 0:
        hemi = 2
    else:
        hemi = 1

    for i, slp in enumerate(slope):
        n = int(((x - slp["corner_x"]) / slp["resolution"]))
        m = int(((y - slp["corner_y"]) / slp["resolution"]))

        log.debug("Corner_X=%f Corner_Y=%f", slp["corner_x"], slp["corner_y"])

        log.debug("Resolution = %f", slp["resolution"])
        log.debug("X_square(i_n)=%d Y-square(i_m)=%d", m, n)
        log.debug("X_num=%d y-num=%d", slp["x_num"], slp["y_num"])
        log.debug(
            "x_num=%d y_num=%d hemi=%d",
            slp["x_num"],
            slp["y_num"],
            slp["hemisphere_flag"],
        )

        if (
            (0 < n)
            & (n < (slp["x_num"] - 1))
            & (0 < m)
            & (m < (slp["y_num"] - 1))
            & (slp["hemisphere_flag"] == hemi)
        ):
            log.debug("Found a model")

            error = 0

            model = i

            p = (x - slp["corner_x"] - n * slp["resolution"]) / slp["resolution"]

            q = (y - slp["corner_y"] - m * slp["resolution"]) / slp["resolution"]

            break
    return error, model, m, n, p, q


def interp_slope(model, n, m, p, q, slope_filename):
    """djb to document

    Args:
        model (_type_): _description_
        n (_type_): _description_
        m (_type_): _description_
        p (_type_): _description_
        q (_type_): _description_
        slope_filename (_type_): _description_

    Returns:
        _type_: _description_
    """
    error = 1

    att = 0.0

    azimuth = 0.0

    with open(slope_filename, "rb") as file_desc:
        file_desc.seek(model["offset"] + 8 * (n * model["y_num"] + (m - 1)), 0)

        xs = struct.unpack(">f", file_desc.read(4))[0]

        ys = struct.unpack(">f", file_desc.read(4))[0]

        log.debug("  slope(n,m-1) [X..Y] = %f,%f", xs, ys)

        if (xs > 999) | (ys > 999):
            return error, att, azimuth

        xso = xs * q * (q - 1.0) / 2.0

        yso = ys * q * (q - 1.0) / 2.0

        file_desc.seek(model["offset"] + 8 * ((n - 1) * model["y_num"] + m), 0)

        xs = struct.unpack(">f", file_desc.read(4))[0]

        ys = struct.unpack(">f", file_desc.read(4))[0]

        log.debug("  slope(n-1,m) [X..Y] = %f,%f", xs, ys)

        if (xs > 999) | (ys > 999):
            return error, att, azimuth

        xso += xs * p * (p - 1.0) / 2.0

        yso += ys * p * (p - 1.0) / 2.0

        file_desc.seek(model["offset"] + 8 * (n * model["y_num"] + m), 0)

        xs = struct.unpack(">f", file_desc.read(4))[0]

        ys = struct.unpack(">f", file_desc.read(4))[0]

        log.debug("  slope(n,m) [X..Y] = %f,%f", xs, ys)

        if (xs > 999) | (ys > 999):
            return error, att, azimuth

        xso += xs * (1.0 + p * q - p * p - q * q)

        yso += ys * (1.0 + p * q - p * p - q * q)

        file_desc.seek(model["offset"] + 8 * ((n + 1) * model["y_num"] + m), 0)

        xs = struct.unpack(">f", file_desc.read(4))[0]

        ys = struct.unpack(">f", file_desc.read(4))[0]

        log.debug("  slope(n+1,m) [X..Y] = %f,%f", xs, ys)

        if (xs > 999) | (ys > 999):
            return error, att, azimuth

        xso += xs * p * (p - q * 2.0 + 1.0) / 2.0

        yso += ys * p * (p - q * 2.0 + 1.0) / 2.0

        file_desc.seek(model["offset"] + 8 * (n * model["y_num"] + (m + 1)), 0)

        xs = struct.unpack(">f", file_desc.read(4))[0]

        ys = struct.unpack(">f", file_desc.read(4))[0]

        log.debug("  slope(n,m+1) [X..Y] = %f,%f", xs, ys)

        if (xs > 999) | (ys > 999):
            return error, att, azimuth

        xso += xs * q * (q - p * 2.0 + 1.0) / 2.0

        yso += ys * q * (q - p * 2.0 + 1.0) / 2.0

        file_desc.seek(model["offset"] + 8 * ((n + 1) * model["y_num"] + (m + 1)), 0)

        xs = struct.unpack(">f", file_desc.read(4))[0]

        ys = struct.unpack(">f", file_desc.read(4))[0]

        log.debug("  slope(n+1,m+1) [X..Y] = %f,%f", xs, ys)

        if (xs > 999) | (ys > 999):
            return error, att, azimuth

        xso += xs * q * p

        yso += ys * q * p

        error = 0

        log.debug("slope X (X,Y) = %f", xso)

        log.debug("slope Y (X,Y) = %f", yso)

    return error, xso, yso


def comp_part_devs(lat, lon, meridional, eccentricity):
    """djb to document

    Args:
        lat (_type_): _description_
        lon (_type_): _description_
        meridional (_type_): _description_
        eccentricity (_type_): _description_

    Returns:
        _type_: _description_
    """
    # eccentricity = math.sqrt(2.0 * 0.00335281066 - 0.00335281066 * 0.00335281066)
    # semimajor = 6378137.000

    lat_rad = math.radians(lat)

    lon_rad = math.radians(lon)

    deriv00 = math.sin(((np.pi / 2.0) - abs(lat_rad)) / 2.0)

    deriv00 *= 3.0 * math.sin(2.0 * lat_rad)

    deriv00 *= eccentricity * eccentricity

    denom = 1.0 - (eccentricity * eccentricity * math.sin(lat_rad) * math.sin(lat_rad))

    if abs(denom) < 0.0000001:
        deriv00 = 0.0

        deriv01 = 0.0

        deriv10 = 0.0

        deriv11 = 0.0

    else:
        deriv00 /= denom

        deriv00 -= np.sign(lat_rad) * math.cos(((np.pi / 2.0) - abs(lat_rad)) / 2.0)

        deriv00 *= meridional

        deriv01 = deriv00 * math.sin(lon_rad)

        deriv00 *= math.cos(lon_rad)

        deriv10 = 2.0 * meridional * math.sin(((np.pi / 2.0) - abs(lat_rad)) / 2.0)

        deriv11 = deriv10 * math.cos(lon_rad)

        deriv10 *= -1.0 * math.sin(lon_rad)

    return deriv00, deriv01, deriv10, deriv11


def calc_echo_dir(deriv00, deriv01, deriv10, deriv11, xs, ys, meridional, zonal, alt, lat):
    """djb to document

    Args:
        deriv00 (_type_): _description_
        deriv01 (_type_): _description_
        deriv10 (_type_): _description_
        deriv11 (_type_): _description_
        xs (_type_): _description_
        ys (_type_): _description_
        meridional (_type_): _description_
        zonal (_type_): _description_
        alt (_type_): _description_
        lat (_type_): _description_

    Returns:
        _type_: _description_
    """
    error = 0

    lat_rad = math.radians(lat)

    cor_slope_x = xs * deriv00

    cor_slope_x += ys * deriv01

    cor_slope_x /= meridional + alt

    cor_slope_y = xs * deriv10

    cor_slope_y += ys * deriv11

    cor_slope_y /= zonal + (alt * math.cos(lat_rad))

    azimuth = math.atan2(-1.0 * cor_slope_y, -1.0 * cor_slope_x)

    att = math.sqrt(cor_slope_x * cor_slope_x + cor_slope_y * cor_slope_y)

    att = math.asin(att)

    return error, att, azimuth


def prepare_slope(slope_filename):
    """djb to document

    Args:
        slope_filename (_type_): _description_

    Returns:
        _type_: _description_
    """
    log.debug("Reading ASCII slope header")

    # read ASCII header of 2497 bytes

    dsd_read = 0

    num_dsd = -1

    with open(slope_filename, "rb") as file_desc:
        header_b = file_desc.read(2470)

    header_a = str(header_b, "utf-8")

    header_lines = header_a.split()

    model_head = {
        "id": 0,
        "hemisphere_flag": 0,
        "corner_x": 0.0,
        "corner_y": 0.0,
        "x_num": 0,
        "y_num": 0,
        "resolution": 0.0,
        "offset": 0,
    }

    slope_header = []

    offset = 0

    for line in header_lines:
        # NUM_DSD=+0000000004

        if "NUM_DSD" in line:
            num_dsd = int((line.split("="))[1])

            log.debug("Detected %d DSDs in Slope Model %s", num_dsd, slope_filename)

            # DS_OFFSET = +00000000000000002465 < bytes >

            # DS_SIZE = +00000000000000000032 < bytes >

            # NUM_DSR = +0000000001

        if "DS_OFFSET" in line:
            offset = int((line.split("="))[1].split("<")[0])

            log.debug("Found a DSD at offset %d", offset)

        if "NUM_DSR" in line:
            dsd_read = dsd_read + 1

            num = int((line.split("="))[1])

            if num == 1:
                log.debug("Reading the header")

                slope_header.append(model_head.copy())

                #               Fill model header from offset

                with open(slope_filename, "rb") as file_desc:
                    file_desc.seek(offset, 0)

                    slope_header[-1]["id"] = struct.unpack(">h", file_desc.read(2))[0]

                    slope_header[-1]["hemisphere_flag"] = struct.unpack(">h", file_desc.read(2))[0]

                    slope_header[-1]["corner_x"] = struct.unpack(">d", file_desc.read(8))[0]

                    slope_header[-1]["corner_y"] = struct.unpack(">d", file_desc.read(8))[0]

                    slope_header[-1]["x_num"] = struct.unpack(">h", file_desc.read(2))[0]

                    slope_header[-1]["y_num"] = struct.unpack(">h", file_desc.read(2))[0]

                    slope_header[-1]["resolution"] = struct.unpack(">d", file_desc.read(8))[0]

                    log.debug("Read id %d", slope_header[-1]["id"])

            else:
                log.debug("Storing the offset in the previous header")

                slope_header[-1]["offset"] = offset

        if dsd_read == num_dsd:
            break

    log.debug("Read in %d DSDs", dsd_read)

    log.debug(slope_header)

    return slope_header


def do_slope(lat, lon, alt, slope, slope_filename, eccentricity, semimajor):
    """djb to document

    Args:
        lat (_type_): _description_
        lon (_type_): _description_
        alt (_type_): _description_
        slope (_type_): _description_
        slope_filename (_type_): _description_
        eccentricity (_type_): _description_
        semimajor (_type_): _description_

    Returns:
        _type_: _description_
    """
    # Read binary data

    att = 0.0

    azimuth = 0.0

    log.debug("Reading binary slope")

    x, y, meridional, zonal = trans_coord(lat, lon, eccentricity, semimajor)

    log.debug("Cartesian X coord %f Cartesian Y coord %f", x, y)

    log.debug("Zonal radius %f Meridional radius %f", zonal, meridional)

    error, model, m, n, p, q = setup_slopes(x, y, lat, slope)

    if error:
        log.debug("No model found")

    else:
        log.debug("Model %d matches %f %f %f %f", model, n, m, p, q)

        error, xs, ys = interp_slope(slope[model], n, m, p, q, slope_filename)

        if error:
            log.debug("bad slope point")

        else:
            log.debug("interpolated slope %f,%f", xs, ys)

        deriv00, deriv01, deriv10, deriv11 = comp_part_devs(lat, lon, meridional, eccentricity)

        log.debug("Derivs: %f %f %f %f", deriv00, deriv01, deriv10, deriv11)

        error, att, azimuth = calc_echo_dir(
            deriv00, deriv01, deriv10, deriv11, xs, ys, meridional, zonal, alt, lat
        )

    return error, att, azimuth, meridional, zonal


def proc_elev(lat, lon, alt, range_1, att, azimuth, meridional, zonal):
    """djb to document

    Args:
        lat (_type_): _description_
        lon (_type_): _description_
        alt (_type_): _description_
        range_1 (_type_): _description_
        att (_type_): _description_
        azimuth (_type_): _description_
        meridional (_type_): _description_
        zonal (_type_): _description_

    Returns:
        _type_: _description_
    """
    lat_rad = math.radians(lat)

    lon_rad = math.radians(lon)

    rho = meridional * zonal

    rho /= meridional * math.cos(lat_rad) * math.sin(azimuth) * math.sin(
        azimuth
    ) + zonal * math.cos(azimuth) * math.cos(azimuth)

    height = (
        alt
        - (range_1 * math.cos(att))
        + (range_1 * math.sin(att) * range_1 * math.sin(att) / (2.0 * rho))
    )

    lat_cor = lat_rad + range_1 * math.cos(azimuth) * math.sin(att) / meridional

    lon_cor = lon_rad + range_1 * math.sin(azimuth) * math.sin(att) / zonal

    if lat_cor > np.pi / 2.0:
        lat_cor = np.pi - lat_cor

        lon_cor += np.pi

    if lat_cor < np.pi / (-2.0):
        lat_cor = -1.0 * np.pi - lat_cor

        lon_cor += np.pi

    if lon_cor < 0:
        lon_cor += np.pi * 2.0

    if lon_cor > np.pi * 2.0:
        lon_cor -= np.pi * 2.0

    if lon_cor > np.pi:
        lon_cor -= np.pi * 2.0

    log.debug("Attitude %f", att)

    log.debug("Azimuth %f", azimuth)

    log.debug("Input latitude (radians) %f", lat_rad)

    log.debug("Input longitude (radians) %f", lon_rad)

    log.debug("Zonal radius of curvature (m) %f", zonal)

    log.debug("Meridional radius of curvature (m) %f", meridional)

    log.debug("Range %f", range_1)

    log.debug("Altitude (m) %f", alt)

    log.debug("Computed elevation (pre bias) %f", height)

    log.debug("Computed latitude (radians) %f", lat_cor)

    log.debug("Computed longitude (radians) %f", lon_cor)

    return height, lat_cor, lon_cor


def slope_doppler(
    sat_x,
    sat_y,
    sat_z,
    echo_x,
    echo_y,
    echo_z,
    vel,
    chirp_slope,
    wavelength,
    speed_light,
):
    """
    slope_doppler
    """
    los_x = echo_x - sat_x

    los_y = echo_y - sat_y

    los_z = echo_z - sat_z

    los_mag = np.sqrt(np.power(los_x, 2.0) + np.power(los_y, 2.0) + np.power(los_z, 2.0))

    v_los = ((vel[:, 0] * los_x) + (vel[:, 1] * los_y) + (vel[:, 2] * los_z)) / los_mag

    sdop = -1.0 * ((speed_light / wavelength) * v_los) / chirp_slope

    return sdop
