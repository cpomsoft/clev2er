"""
Slope correction/geolocation function using an adapted LEPTA method from Li et al (2022)
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

    return distances.tolist()  # Convert back to a regular Python list


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


def median_dem_height_around_a_point(
    thisdem: Dem, xpos: float, ypos: float, pulse_limited_footprint_size: int
):
    """Find the median DEM height in a rectangle of width
    pulse_limited_footprint_size around a x,y point

    Args:
        thisdem (Dem): Dem object used for Roemer/LEPTA correction
        xpos (float):x location of point in m
        ypos (float):y location of point in m
        pulse_limited_footprint_size (int): pulse limited footprint size in m

    Returns:
        float|None
    """
    # get the rectangular bounds of the pulse limited footprint
    # about the point

    if thisdem is None:
        raise ValueError("no Dem passed to median_dem_height_around_a_point")

    x_min = xpos - (pulse_limited_footprint_size / 2 + thisdem.binsize)
    x_max = xpos + (pulse_limited_footprint_size / 2 + thisdem.binsize)
    y_min = ypos - (pulse_limited_footprint_size / 2 + thisdem.binsize)
    y_max = ypos + (pulse_limited_footprint_size / 2 + thisdem.binsize)

    segment = [(x_min, x_max), (y_min, y_max)]

    # Extract the rectangular segment from the DEM
    try:
        _, _, zdem = thisdem.get_segment(segment, grid_xy=True, flatten=False)
    except (IndexError, ValueError, TypeError, AttributeError, MemoryError):
        return None
    except Exception:  # pylint: disable=W0718
        return None

    # Check DEM segment for bad values and remove
    nan_mask = np.isnan(zdem)
    include_only_good_zdem_indices = np.where(~nan_mask)[0]
    if len(include_only_good_zdem_indices) < 1:
        return None

    zdem = zdem[include_only_good_zdem_indices]

    # Only keep DEM heights which are in a sensible range
    # this step removes DEM values set to fill_value (a high number)
    valid_dem_heights = np.where(zdem < 5000.0)[0]
    if len(valid_dem_heights) < 1:
        return None

    zdem = zdem[valid_dem_heights]

    smoothed_zdem = median_filter(zdem, size=3)
    return np.nanmedian(smoothed_zdem)


def geolocate_lepta(
    l1b: Dataset,
    thisdem: Dem | None,
    thisdhdt: Dhdt | None,
    config: dict,
    surface_type_20_ku: np.ndarray,
    geo_corrected_tracker_range: np.ndarray,
    retracker_correction: np.ndarray,
    leading_edge_start: np.ndarray,
    leading_edge_stop: np.ndarray,
    waveforms_to_include: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Geolocate CS2 LRM measurements using an adapted LEPTA (Li et al, 2022) method

    Args:
        l1b (Dataset): NetCDF Dataset of L1b file
        thisdem (Dem): Dem object used for Roemer/LEPTA correction
        config (dict): config dictionary containing ["lrm_lepta_geolocation"][params]
        surface_type_20_ku (np.ndarray): surface type for track, where 1 == grounded_ice
        geo_corrected_tracker_range (np.ndarray) : geo-corrected tracker range (NOT retracked)
        retracker_correction (np.ndarray) : retracker correction to range (m)
        leading_edge_start (np.ndarray) : position of start of waveform leading edge (decimal bins)
        leading_edge_stop (np.ndarray) : position of end of waveform leading edge (decimal bins)
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

    reference_bin_index = config["instrument"]["ref_bin_index_lrm"]
    range_bin_size = config["instrument"]["range_bin_size_lrm"]  # meters
    # num_bins = config["instrument"]["num_range_bins_lrm"]
    across_track_beam_width = config["instrument"][
        "across_track_beam_width_lrm"
    ]  # meters
    pulse_limited_footprint_size_lrm = config["instrument"][
        "pulse_limited_footprint_size_lrm"
    ]  # m

    # Search window selection
    use_window_around_retracking_point = config["lrm_lepta_geolocation"][
        "use_window_around_retracking_point"
    ]
    use_full_leading_edge = config["lrm_lepta_geolocation"]["use_full_leading_edge"]
    delta_range_offset = config["lrm_lepta_geolocation"]["delta_range_offset"]

    # POCA(x,y) selection method
    use_xy_at_min_dem_to_sat_distance = config["lrm_lepta_geolocation"][
        "use_xy_at_min_dem_to_sat_distance"
    ]
    use_mean_xy_in_window = config["lrm_lepta_geolocation"]["use_mean_xy_in_window"]

    # POCA(z) selection method
    use_mean_z_in_window = config["lrm_lepta_geolocation"]["use_mean_z_in_window"]
    use_median_z_in_window = config["lrm_lepta_geolocation"]["use_median_z_in_window"]

    use_z_at_min_dem_to_sat_distance = config["lrm_lepta_geolocation"][
        "use_z_at_min_dem_to_sat_distance"
    ]

    use_median_height_around_point = config["lrm_lepta_geolocation"][
        "use_median_height_around_point"
    ]

    # Additional options
    include_dhdt_correction = config["lrm_lepta_geolocation"]["include_dhdt_correction"]

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

        if config["lrm_lepta_geolocation"]["median_filter"]:
            smoothed_zdem = median_filter(zdem, size=3)
        else:
            smoothed_zdem = zdem

        xdem = xdem.flatten()
        ydem = ydem.flatten()
        zdem = smoothed_zdem.flatten()

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

        # Check DEM segment for bad values and remove
        nan_mask = np.isnan(zdem)
        include_only_good_zdem_indices = np.where(~nan_mask)[0]
        if len(include_only_good_zdem_indices) < 1:
            slope_ok[i] = False
            continue

        xdem = xdem[include_only_good_zdem_indices]
        ydem = ydem[include_only_good_zdem_indices]
        zdem = zdem[include_only_good_zdem_indices]

        # Only keep DEM heights which are in a sensible range
        # this step removes DEM values set to fill_value (a high number)
        valid_dem_heights = np.where(zdem < 5000.0)[0]
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

        # Compute distance between each remaining dem location and satellite
        dem_to_sat_dists = calculate_distances(
            nadir_x[i], nadir_y[i], altitudes[i], xdem, ydem, zdem
        )

        # ----------------------------------------------------------------------------------------
        #   Limit DEM points by finding those that would be within a range window
        #   defined by the retracking point +/- delta_range_offset (defined by Li as 1.25m)
        # ----------------------------------------------------------------------------------------

        # range_to_window_start = (
        #     geo_corrected_tracker_range[i] - (reference_bin_index) * range_bin_size
        # )
        # range_to_window_end = (
        #     geo_corrected_tracker_range[i] + (num_bins - reference_bin_index) * range_bin_size
        # )

        # --------------------------------------------------------------------------------------
        # Find locations in DEM to Satellite distances are within the range of the full
        # width of the leading edge
        # --------------------------------------------------------------------------------------
        if use_full_leading_edge:
            range_to_le_start = (
                geo_corrected_tracker_range[i]
                - (reference_bin_index - leading_edge_start[i][0]) * range_bin_size
            )
            range_to_le_end = (
                geo_corrected_tracker_range[i]
                + (leading_edge_stop[i][0] - reference_bin_index) * range_bin_size
            )

            indices_within_range_window = np.where(
                np.logical_and(
                    dem_to_sat_dists >= range_to_le_start,
                    dem_to_sat_dists <= range_to_le_end,
                )
            )[0]

        # --------------------------------------------------------------------------------------
        # Find locations in DEM to Satellite distances are within the range of the
        # retracking point +/- an offset
        # --------------------------------------------------------------------------------------
        elif use_window_around_retracking_point:
            range_to_retracking_point = (
                geo_corrected_tracker_range[i] + retracker_correction[i]
            )
            range_start = range_to_retracking_point - delta_range_offset
            range_end = range_to_retracking_point + delta_range_offset

            indices_within_range_window = np.where(
                np.logical_and(
                    dem_to_sat_dists >= range_start,
                    dem_to_sat_dists <= range_end,
                )
            )[0]

            if len(indices_within_range_window) == 0:
                closest_dem_to_sat_distance = np.min(dem_to_sat_dists)
                diff = closest_dem_to_sat_distance - range_start
                range_start += diff
                range_end += diff

                indices_within_range_window = np.where(
                    np.logical_and(
                        dem_to_sat_dists >= range_start,
                        dem_to_sat_dists <= range_end,
                    )
                )[0]
        else:
            raise ValueError("No LEPTA window method selected")
        # --------------------------------------------------------------------------------------

        if len(indices_within_range_window) == 0:
            log.debug("No points found in DEM using LEPTA delta range offset")
            slope_ok[i] = False
            continue

        # Reduce DEM points to those found within range window
        xdem = xdem[indices_within_range_window]
        ydem = ydem[indices_within_range_window]
        zdem = zdem[indices_within_range_window]
        dem_to_sat_dists = np.array(dem_to_sat_dists)[indices_within_range_window]

        # --------------------------------------------------------------------------------------
        #  Find Location of POCA x,y
        # --------------------------------------------------------------------------------------
        index_of_closest = None

        if use_mean_xy_in_window:
            # use the mean location as per Li et al (2022):https://doi.org/10.5194/tc-16-2225-2022
            # section 3.13
            poca_x[i] = np.mean(xdem)
            poca_y[i] = np.mean(ydem)
        elif use_xy_at_min_dem_to_sat_distance:
            index_of_closest = np.argmin(dem_to_sat_dists)
            if index_of_closest < 0 or index_of_closest > (len(xdem) - 1):
                slope_ok[i] = False
                continue
            poca_x[i] = xdem[index_of_closest]
            poca_y[i] = ydem[index_of_closest]
        else:
            raise ValueError("no method selected for LEPTA POCA(x,y)")

        # --------------------------------------------------------------------------------------
        #  Find Location of POCA z
        # --------------------------------------------------------------------------------------

        if use_mean_z_in_window:
            poca_z[i] = np.mean(zdem)
        elif use_median_z_in_window:
            poca_z[i] = np.median(zdem)

        elif use_z_at_min_dem_to_sat_distance:
            # Find index of minimum range (ie heighest point) in remaining DEM points
            # and assign this as POCA
            if index_of_closest is None:
                index_of_closest = np.argmin(dem_to_sat_dists)
                if index_of_closest < 0 or index_of_closest > (len(xdem) - 1):
                    slope_ok[i] = False
                    continue
            poca_z[i] = zdem[index_of_closest]

        elif use_median_height_around_point:
            poca_z[i] = median_dem_height_around_a_point(
                thisdem,
                poca_x[i],
                poca_y[i],
                pulse_limited_footprint_size_lrm,
            )
        else:
            raise ValueError("no method selected for LEPTA POCA(z)")

        # --------------------------------------------------------------------------------------
        #  Calculate Slope Correction
        # --------------------------------------------------------------------------------------

        dem_to_sat_dists = calculate_distances(
            nadir_x[i], nadir_y[i], altitudes[i], [poca_x[i]], [poca_y[i]], [poca_z[i]]
        )

        # Calculate the slope correction to height
        slope_correction[i] = dem_to_sat_dists[0] + poca_z[i] - altitudes[i]

    # Transform all POCA x,y to lon,lat
    lon_poca_20_ku, lat_poca_20_ku = thisdem.xy_to_lonlat_transformer.transform(
        poca_x, poca_y
    )

    # Calculate height as altitude-(corrected range)+slope_correction
    height_20_ku = np.full_like(lat_20_ku, np.nan)

    num_measurements = len(lat_20_ku)
    for i in range(num_measurements):
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
