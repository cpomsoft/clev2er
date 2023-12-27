"""
Slope correction/geolocation function using an adapted Roemer method 
from :
Roemer, S., Legrésy, B., Horwath, M., and Dietrich, R.: Refined
analysis of radar altimetry data applied to the region of the
subglacial Lake Vostok/Antarctica, Remote Sens. Environ., 106,
269–284, https://doi.org/10.1016/j.rse.2006.02.026, 2007.
"""

import logging
from datetime import datetime, timedelta  # date and time functions
from typing import Tuple

import numpy as np
import pyproj
from netCDF4 import Dataset  # pylint: disable=no-name-in-module
from pyproj import Transformer
from scipy.ndimage import median_filter

from clev2er.utils.cs2.geolocate.lrm_slope import slope_doppler
from clev2er.utils.dems.dems import Dem
from clev2er.utils.dhdt_data.dhdt import Dhdt

# pylint: disable=too-many-arguments,too-many-locals,too-many-branches,too-many-statements

log = logging.getLogger(__name__)

EARTH_RADIUS = 6378137.0


def calculate_distances(
    x1_coord: float,
    y1_coord: float,
    z1_coord: float,
    x2_array: np.ndarray[float],
    y2_array: np.ndarray[float],
    z2_array: np.ndarray[float],
    squared_only=False,
) -> list[float]:
    """calculates the distances between a  refernce cartesian point (x1,y1,z1) in 3d space
    and a list of other points : x2[],y2[],z2[]

    Args:
        x1_coord (float): x coordinate of ref point
        y1_coord (float): y coordinate of ref point
        z1_coord (float): z coordinate of ref point
        x2_array (list[float]): list of x coordinates
        y2_array (list[float]): list of y coordinates
        z2_array (list[float]): list of z coordinates
        squared_only (bool) : if True, only calculate the squares of diffs and not sqrt
                              this will be faster, but doesn't give actual distances

    Returns:
        list[float]: list of distances between points x1,y1,z1 and x2[],y2[],z2[]
    """

    x2_array = np.array(x2_array)
    y2_array = np.array(y2_array)
    z2_array = np.array(z2_array)

    distances = (
        (x2_array - x1_coord) ** 2
        + (y2_array - y1_coord) ** 2
        + (z2_array - z1_coord) ** 2
    )

    if not squared_only:
        distances = np.sqrt(distances)

    return distances  # Convert back to a regular Python list


def find_poca(dem_interp_f, gridx_f, gridy_f, nadir_x, nadir_y, alt_pt):
    """CLS/McMillan Function that finds the POCA using Roemer et al. method
    (shortest range in the DEM segment)

    Args:
        dem_interp_f (_type_): DEM
        gridx_f (_type_): _description_
        gridy_f (_type_): _description_
        nadir_x (_type_): x location of nadir in polar stereo coordinates (m)
        nadir_y (_type_): y location of nadir in polar stereo coordinates (m)
        alt_pt (float): altitude at nadir (m)

    Returns:
        (float,float,float,float,bool): poca_x, poca_y, poca_z, slope_correction_to_height,
        flg_success
    """

    # ----------------------------------------------------------------
    # compute horizontal plane distance to each cell in beam footprint
    # ----------------------------------------------------------------

    # compute x and y distance of all points in beam footprint from nadir coordinate of
    # current record
    dem_dx_vec = gridx_f - nadir_x
    dem_dy_vec = gridy_f - nadir_y

    # compute magnitude of distance from nadir
    dem_dmag_vec = np.sqrt(dem_dx_vec**2 + dem_dy_vec**2)

    # ------------------------------------------------
    # JA: => accounting for earth curvature
    # ------------------------------------------------

    dem_dmag_vec_ec = dem_dmag_vec / EARTH_RADIUS

    dem_dz_vec = dem_interp_f - alt_pt - EARTH_RADIUS * dem_dmag_vec_ec**2 / 2.0
    dem_range_vec = np.sqrt((dem_dx_vec) ** 2 + (dem_dy_vec) ** 2 + (dem_dz_vec) ** 2)

    # find range to, and indices of, closest dem pixel
    [dem_rpoca, dempoca_ind] = np.nanmin(dem_range_vec), np.nanargmin(dem_range_vec)

    if np.isnan(dem_interp_f[dempoca_ind]) | (dem_interp_f[dempoca_ind] == -9999):
        return -999, -999, -999, -999, 0

    # compute relocation correction to apply to assumed nadir altimeter elevation to move to poca
    slope_correction_to_height = dem_rpoca + dem_interp_f[dempoca_ind] - alt_pt

    flg_success = 1

    return (
        gridx_f[dempoca_ind],
        gridy_f[dempoca_ind],
        dem_interp_f[dempoca_ind],
        slope_correction_to_height,
        flg_success,
    )


def datetime2year(date_dt):
    """calculate decimal year from datetime

    Args:
        date_dt (datetime): datetime obj to process

    Returns:
        float: decimal year
    """
    year_part = date_dt - datetime(year=date_dt.year, month=1, day=1)
    year_length = datetime(year=date_dt.year + 1, month=1, day=1) - datetime(
        year=date_dt.year, month=1, day=1
    )
    return date_dt.year + year_part / year_length


def geolocate_roemer(
    l1b: Dataset,
    thisdem: Dem | None,
    thisdhdt: Dhdt | None,
    config: dict,
    surface_type_20_ku: np.ndarray,
    geo_corrected_tracker_range: np.ndarray,
    retracker_correction: np.ndarray,
    waveforms_to_include: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Geolocate CS2 LRM measurements using an adapted Roemer (Roemer et al, 2007) method

    Args:
        l1b (Dataset): NetCDF Dataset of L1b file
        thisdem (Dem): Dem object used for Roemer/LEPTA correction
        config (dict): config dictionary containing ["lrm_lepta_geolocation"][params]
        surface_type_20_ku (np.ndarray): surface type for track, where 1 == grounded_ice
        geo_corrected_tracker_range (np.ndarray) : geo-corrected tracker range (NOT retracked)
        retracker_correction (np.ndarray) : retracker correction to range (m)
        waveforms_to_include (np.ndarray) : boolean array of waveforms to include (False == reject)
    Returns:
        (np.ndarray, np.ndarray, np.ndarray, np.ndarray):
        (height_20_ku, lat_poca_20_ku, lon_poca_20_ku, slope_ok)
    """

    if thisdem is None:
        raise ValueError("thisdem None value passed")

    # ------------------------------------------------------------------------------------
    # Get configuration parameters
    # ------------------------------------------------------------------------------------

    # reference_bin_index = config["instrument"]["ref_bin_index_lrm"]
    # range_bin_size = config["instrument"]["range_bin_size_lrm"]  # meters
    # num_bins = config["instrument"]["num_range_bins_lrm"]
    across_track_beam_width = config["instrument"][
        "across_track_beam_width_lrm"
    ]  # meters
    pulse_limited_footprint_size_lrm = config["instrument"][
        "pulse_limited_footprint_size_lrm"
    ]  # m

    # Additional options
    include_dhdt_correction = config["lrm_roemer_geolocation"][
        "include_dhdt_correction"
    ]

    max_poca_reloc_distance = config["lrm_roemer_geolocation"][
        "max_poca_reloc_distance"
    ]

    # ------------------------------------------------------------------------------------

    # Get nadir latitude, longitude and satellite altitude from L1b
    lat_20_ku = l1b["lat_20_ku"][:].data
    lon_20_ku = l1b["lon_20_ku"][:].data % 360.0
    altitudes = l1b["alt_20_ku"][:].data

    # Transform to X,Y locs in DEM projection
    nadir_x, nadir_y = thisdem.lonlat_to_xy_transformer.transform(
        lon_20_ku, lat_20_ku
    )  # pylint: disable=unpacking-non-sequence

    # Interpolate DEM heights at nadir locations
    heights_at_nadir = thisdem.interp_dem(nadir_x, nadir_y)

    # Create working parameter arrays
    poca_x = np.full_like(nadir_x, dtype=float, fill_value=np.nan)
    poca_y = np.full_like(nadir_x, dtype=float, fill_value=np.nan)
    poca_z = np.full_like(nadir_x, dtype=float, fill_value=np.nan)
    slope_correction = np.full_like(nadir_x, dtype=float, fill_value=np.nan)
    slope_ok = np.full_like(nadir_x, dtype=bool, fill_value=True)
    height_20_ku = np.full_like(nadir_x, dtype=float, fill_value=np.nan)

    # if using a dh/dt correction to the DEM we need to calculate the time diff in years
    if include_dhdt_correction:
        time_20_ku = l1b["time_20_ku"][:].data[0]

        track_year_dt = datetime(2000, 1, 1, 0) + timedelta(seconds=time_20_ku)
        track_year = datetime2year(track_year_dt)
        if track_year < 2010:
            raise ValueError(
                f"track_year: {track_year} should not be < 2010 in dhdt correction"
            )
        if thisdem.reference_year == 0:
            raise ValueError(
                f"thisdem.reference_year has not been set for DEM {thisdem.name}"
            )

        year_difference = track_year - thisdem.reference_year

    # ------------------------------------------------------------------------------------
    #  Loop through each track record
    # ------------------------------------------------------------------------------------

    for i, _ in enumerate(nadir_x):
        # By default, set POCA x,y to nadir, and height to Nan
        poca_x[i] = nadir_x[i]
        poca_y[i] = nadir_y[i]
        poca_z[i] = np.nan

        # if record is excluded due to previous checks, then skip
        if not waveforms_to_include[i]:
            continue

        # get the rectangular bounds about the track, adjusted for across track beam width and
        # the dem posting
        x_min = nadir_x[i] - (across_track_beam_width / 2 + thisdem.binsize)
        x_max = nadir_x[i] + (across_track_beam_width / 2 + thisdem.binsize)
        y_min = nadir_y[i] - (across_track_beam_width / 2 + thisdem.binsize)
        y_max = nadir_y[i] + (across_track_beam_width / 2 + thisdem.binsize)

        segment = [(x_min, x_max), (y_min, y_max)]

        # Extract the rectangular segment from the DEM
        try:
            xdem, ydem, zdem = thisdem.get_segment(segment, grid_xy=True, flatten=False)
        except (IndexError, ValueError, TypeError, AttributeError, MemoryError):
            slope_ok[i] = False
            continue
        except Exception:  # pylint: disable=W0718
            slope_ok[i] = False
            continue

        if config["lrm_roemer_geolocation"]["median_filter"]:
            smoothed_zdem = median_filter(zdem, size=3)
            zdem = smoothed_zdem

        if config["lrm_roemer_geolocation"]["cls_method"]:
            # Step 1: find the DEM points within a circular area centred on the nadir
            # point corresponding to a radius of half the beam width
            xdem = xdem.flatten()
            ydem = ydem.flatten()
            zdem = zdem.flatten()

            # Compute distance between each dem location and nadir in (x,y,z)
            dem_to_nadir_dists = calculate_distances(
                nadir_x[i], nadir_y[i], heights_at_nadir[i], xdem, ydem, zdem
            )

            # find where dem_to_nadir_dists is within beam. ie extract circular area
            include_dem_indices = np.where(
                np.array(dem_to_nadir_dists) < (across_track_beam_width / 2.0)
            )[0]
            if len(include_dem_indices) == 0:
                slope_ok[i] = False
                continue

            xdem = xdem[include_dem_indices]
            ydem = ydem[include_dem_indices]
            zdem = zdem[include_dem_indices]

            # Check remaining DEM points for bad height values and remove
            nan_mask = np.isnan(zdem)
            include_only_good_zdem_indices = np.where(~nan_mask)[0]
            if len(include_only_good_zdem_indices) < 1:
                slope_ok[i] = False
                continue

            xdem = xdem[include_only_good_zdem_indices]
            ydem = ydem[include_only_good_zdem_indices]
            zdem = zdem[include_only_good_zdem_indices]

            # Only keep DEM heights which are in a sensible range
            # this step removes DEM values set to most fill_values
            valid_dem_heights = np.where(np.abs(zdem) < 5000.0)[0]
            if len(valid_dem_heights) < 1:
                slope_ok[i] = False
                continue

            xdem = xdem[valid_dem_heights]
            ydem = ydem[valid_dem_heights]
            zdem = zdem[valid_dem_heights]

            # Correct DEM elevations for dh/dt changes
            if include_dhdt_correction:
                if thisdhdt is not None:
                    # find dh/dt * year_difference at each DEM location
                    zdem += thisdhdt.interp_dhdt(xdem, ydem) * year_difference

            # Find the POCA location and slope correction to height
            (
                this_poca_x,
                this_poca_y,
                this_poca_z,
                slope_correction_to_height,
                flg_success,
            ) = find_poca(zdem, xdem, ydem, nadir_x[i], nadir_y[i], altitudes[i])
            if not flg_success:
                slope_ok[i] = False
                continue
            poca_x[i] = this_poca_x
            poca_y[i] = this_poca_y
            poca_z[i] = this_poca_z
            slope_correction[i] = slope_correction_to_height
            dist_reloc = np.sqrt(
                (this_poca_x - nadir_x[i]) ** 2 + (this_poca_y - nadir_y[i]) ** 2
            )
            if dist_reloc > max_poca_reloc_distance:
                slope_ok[i] = False

        if config["lrm_roemer_geolocation"]["use_sliding_window"]:
            # Step 1: Calculate all distances once
            all_distances_flat = calculate_distances(
                x1_coord=nadir_x[i],
                y1_coord=nadir_y[i],
                z1_coord=altitudes[i],
                x2_array=xdem.flatten(),
                y2_array=ydem.flatten(),
                z2_array=zdem.flatten(),
                squared_only=False,
            )

            all_distances = np.array(all_distances_flat).reshape(xdem.shape)

            # Step 2: Slide the window over the pre-calculated distance grid
            min_distance = np.inf
            min_position = (0, 0)
            window_size = (int)(pulse_limited_footprint_size_lrm / thisdem.binsize)

            for ii in range(all_distances.shape[0] - window_size + 1):
                for jj in range(all_distances.shape[1] - window_size + 1):
                    # Extract the current window of distances
                    window = all_distances[ii : ii + window_size, jj : jj + window_size]

                    # Calculate the mean distance within the window
                    mean_distance = np.mean(window)

                    # Update the minimum mean and position if a new minimum is found
                    if mean_distance < min_distance:
                        min_distance = mean_distance
                        min_position = (ii, jj)

            # min_position is the position of the window with the smallest mean distance
            # print(f"min_distance={min_distance} at {min_position}")

            # --------------------------------------------------------------------------------------
            #  Find Location of POCA x,y
            # --------------------------------------------------------------------------------------

            poca_x[i] = xdem[min_position]
            poca_y[i] = ydem[min_position]

            # --------------------------------------------------------------------------------------
            #  Find Location of POCA z
            # --------------------------------------------------------------------------------------

            poca_z[i] = zdem[min_position]

            # --------------------------------------------------------------------------------------
            #  Calculate Slope Correction
            # --------------------------------------------------------------------------------------

            dem_to_sat_dists = calculate_distances(
                nadir_x[i],
                nadir_y[i],
                altitudes[i],
                [poca_x[i]],
                [poca_y[i]],
                [poca_z[i]],
            )

            # Calculate the slope correction to height
            slope_correction[i] = dem_to_sat_dists[0] + poca_z[i] - altitudes[i]

    # Transform all POCA x,y to lon,lat
    lon_poca_20_ku, lat_poca_20_ku = thisdem.xy_to_lonlat_transformer.transform(
        poca_x, poca_y
    )

    # Calculate height as altitude-(corrected range)+slope_correction
    height_20_ku = np.full_like(lat_20_ku, np.nan)

    for i in range(len(lat_20_ku)):  # pylint: disable=consider-using-enumerate
        if np.isfinite(geo_corrected_tracker_range[i]):
            if slope_ok[i] and surface_type_20_ku[i] == 1:  # grounded ice type only
                height_20_ku[i] = (
                    altitudes[i]
                    - (geo_corrected_tracker_range[i] + retracker_correction[i])
                    + slope_correction[i]
                )
            else:
                height_20_ku[i] = np.nan
        else:
            height_20_ku[i] = np.nan
        # Set POCA lat,lon to nadir if no slope correction

        if (
            (not np.isfinite(lat_poca_20_ku[i]))
            or (not np.isfinite(lon_poca_20_ku[i]))
            or (not slope_ok[i])
        ):
            lat_poca_20_ku[i] = lat_20_ku[i]
            lon_poca_20_ku[i] = lon_20_ku[i]
            height_20_ku[i] = np.nan

    # ----------------------------------------------------------------
    # Doppler Slope Correction
    # ----------------------------------------------------------------

    if config["lrm_lepta_geolocation"]["include_slope_doppler_correction"]:
        idx = np.where(np.isfinite(height_20_ku))[0]
        if len(idx) > 0:
            ecef = pyproj.Proj(proj="geocent", ellps="WGS84", datum="WGS84")
            lla = pyproj.Proj(proj="latlong", ellps="WGS84", datum="WGS84")
            this_transform = Transformer.from_proj(lla, ecef, always_xy=True)

            (  # pylint: disable=unpacking-non-sequence
                sat_x,
                sat_y,
                sat_z,
            ) = this_transform.transform(
                xx=lon_20_ku[idx],
                yy=lat_20_ku[idx],
                zz=altitudes[idx],
                radians=False,
            )
            (  # pylint: disable=unpacking-non-sequence
                ech_x,
                ech_y,
                ech_z,
            ) = this_transform.transform(
                xx=lon_poca_20_ku[idx],
                yy=lat_poca_20_ku[idx],
                zz=height_20_ku[idx],
                radians=False,
            )

            sdop = slope_doppler(
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

    return (height_20_ku, lat_poca_20_ku, lon_poca_20_ku, slope_ok)
