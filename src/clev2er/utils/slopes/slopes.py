"""
Module to get degree of slope data for locations in the Cryosphere

Author: Alan Muir (CPOM/UCL)
Date: 2019

Updated 22/05/20 by Lin Gilbert - added co-ordinate reference system to self
                                - added interp_slope_from_lat_lon method
Updated 24/09/21 by Lin Gilbert - changed pyproj.Proj to pyproj.CRS to avoid deprecation notices
                                - updated polarplot calls in unit test grid type, set default to 
                                point type

Copyright: UCL/MSSL/CPOM. 

"""

# Imports

from __future__ import annotations

import logging
import os

import numpy as np
from netCDF4 import Dataset  # pylint: disable=no-name-in-module
from pyproj import CRS, Transformer  # converter, co-ord definitions
from scipy.interpolate import interpn  # interpolation functions
from tifffile import imread  # required to read 64-bit tif file for slope data

# pylint: disable=too-many-statements
# pylint: disable=too-many-instance-attributes
# pylint: disable=unpacking-non-sequence
# pylint: disable=too-many-branches

all_slope_scenarios = [
    "cpom_ant_2018_1km_slopes",
    "awi_grn_2013_1km_slopes",
]

log = logging.getLogger(__name__)


# Class contains Slope handling functions
class Slopes:
    """**class to load surface slope data derived from DEMS for AIS, GIS**"""

    def __init__(self, name: str, config: dict | None = None):
        """initialize Slopes class

        Args:
            name (str): slope scenario name, must bin in all_slope_scenarios
            config (dict) : dictionary containing ['slope_data'][name] (==path of slope file)
                            for scenario self.name
        """
        self.name = name
        self.config = config

        if name not in all_slope_scenarios:
            raise ValueError(f"{name} not a valid slope scenario")

        slope_file = ""
        # Try to get slope file name from config dictionary
        if config:
            if "slope_data" not in config:
                log.error("slope_data key not in config dict")
                raise KeyError("slope_data key not in config dict")
            if name not in config["slope_data"]:
                log.error(" %s key not in config[slope_data]", name)
                raise KeyError(f" {name} key not in config[slope_data]")
            slope_file = config["slope_data"][name]

        log.info("Loading slope data scenario %s", name)

        # Load CPOM Antarctic DEM 1km (Slater 2018)
        if name == "cpom_ant_2018_1km_slopes":
            # Needed to use the unpacked version as the tifffile module does not support
            # TIFF compression
            if not slope_file:  # get from default path instead of config dict
                slope_file = (
                    os.environ["CPDATA_DIR"] + "/SATS/RA/DEMS/ant_cpom_cs2_1km/"
                    "Antarctica_Cryosat2_1km_DEMv1.0_slope.unpacked.tif"
                )
            if not os.path.isfile(slope_file):
                log.error("%s not found", slope_file)
                raise FileNotFoundError(f"{slope_file} not found")

            image = imread(slope_file, key=0)

            # Ensure that 'image' is an ndarray
            if not isinstance(image, np.ndarray):
                log.error("Unexpected image data type: %s", type(image).__name__)
                raise TypeError("Unexpected image data type")

            nrows = image.shape[0]
            ncols = image.shape[1]

            self.slopes = image
            self.slopes = image.reshape((nrows, ncols))
            self.slopes = np.flip(self.slopes, 0)
            self.minx = -2819500.0
            self.maxx = 2819500.0
            self.miny = -2419500.0
            self.maxy = 2419500.0

            self.x = np.linspace(self.minx, self.maxx, ncols, endpoint=True)
            self.y = np.linspace(self.miny, self.maxy, nrows, endpoint=True)
            self.xmesh, self.ymesh = np.meshgrid(self.x, self.y)

            self.coordinate_reference_system = CRS(
                "epsg:3031"
            )  # WGS 84 / Antarctic Polar Stereographic, lon0=0E, X along 90E, Y along 0E

        # Load CPOM Greenland DEM 1km (Slater 2018) - Preliminary (unverified)
        elif name == "cpom_grn_2018_1km_prelim_slopes":
            # Needed to use the unpacked version as the tifffile module does not support TIFF
            # compression
            # gdal_translate Greenland_Cryosat2_1km_DEMv1.0_slope.tif
            # Greenland_Cryosat2_1km_DEMv1.0_slope.unpacked.tif
            if not slope_file:  # get from default path instead of config dict
                slope_file = (
                    os.environ["CPDATA_DIR"] + "/SATS/RA/DEMS/grn_cpom_cs2_1km_prelim/"
                    "Greenland_Cryosat2_1km_DEMv1.0_slope.unpacked.tif"
                )

            image = imread(slope_file, key=0)

            # Ensure that 'image' is an ndarray
            if not isinstance(image, np.ndarray):
                log.error("Unexpected image data type: %s", type(image).__name__)
                raise TypeError("Unexpected image data type")

            nrows = image.shape[0]
            ncols = image.shape[1]

            self.slopes = image
            self.slopes = image.reshape((nrows, ncols))
            self.slopes = np.flip(self.slopes, 0)
            self.minx = -999500.0
            self.maxx = 999500.0
            self.miny = -3499500.0
            self.maxy = -400500.0

            self.x = np.linspace(self.minx, self.maxx, ncols, endpoint=True)
            self.y = np.linspace(self.miny, self.maxy, nrows, endpoint=True)
            self.xmesh, self.ymesh = np.meshgrid(self.x, self.y)

            self.coordinate_reference_system = CRS(
                "epsg:3413"
            )  # WGS 84 / NSIDC Sea Ice Polar Stereographic North: lon0=45W, X along 45E, Y
            # along 135E

        # Load AWI Greenland DEM 1km (Helm 2013)
        elif name == "awi_grn_2013_1km_slopes":
            if not slope_file:  # get from default path instead of config dict
                slopefile = (
                    os.environ["CPDATA_DIR"]
                    + "/SATS/RA/DEMS/grn_awi_2013_dem/grn_awi_2013_dem_slope.nc"
                )
            nc_dem = Dataset(slopefile)

            self.slopes = nc_dem.variables["slope"][:]

            nrows = self.slopes.shape[0]
            ncols = self.slopes.shape[1]

            self.minx = -1823000.0
            self.maxx = 1973000.0
            self.miny = -3441000.0
            self.maxy = -533000.0

            self.x = np.linspace(self.minx, self.maxx, ncols, endpoint=True)
            self.y = np.linspace(self.miny, self.maxy, nrows, endpoint=True)
            self.xmesh, self.ymesh = np.meshgrid(self.x, self.y)

            self.coordinate_reference_system = CRS(
                "epsg:3413"
            )  # WGS 84 / NSIDC Sea Ice Polar Stereographic North: lon0=45W, X along 45E,
            # Y along 135E

        else:
            raise ValueError(f"slope scenario : {name} not valid")

        # setup coordinate reference system (crs) for this projection
        self.crs_bng = self.coordinate_reference_system
        self.crs_wgs = CRS("epsg:4326")  # Assume lat/lon use WGS84
        # Setup the Transforms
        self.lonlat_to_xy_transformer = Transformer.from_proj(
            self.crs_wgs, self.crs_bng, always_xy=True
        )

    # Revised interp_slope method to address the mypy error

    def interp_slope(self, x, y, method="linear", xy_is_lonlat=False):
        """
        Interpolate Slope data
        input x, y can be arrays or single, units m,

        Args:
            x (np.ndarray | float): x-coordinates (either in meters or longitude)
            y (np.ndarray | float): y-coordinates (either in meters or latitude)
            method (str, optional): interpolation method. Defaults to "linear".
            xy_is_lonlat (bool, optional): if True, x and y are treated as longitude and latitude.

        Returns:
            np.ndarray: returns the interpolated slope(s) at x, y
        """
        # Ensure x and y are numpy arrays
        x = np.atleast_1d(x)
        y = np.atleast_1d(y)

        # Transform to x, y if inputs are lon, lat
        if xy_is_lonlat:
            x, y = self.lonlat_to_xy_transformer.transform(x, y)  # transform lon, lat -> x, y

        # Identify out-of-bounds values in x and y, replacing them with boundary values
        x = np.clip(x, self.minx, self.maxx)
        y = np.clip(y, self.miny, self.maxy)

        # Perform interpolation
        slope_data = interpn((self.y, self.x), self.slopes, (y, x), method=method)

        # Replace out-of-bounds values with NaN
        slope_data[(x == self.minx) | (x == self.maxx)] = np.nan
        slope_data[(y == self.miny) | (y == self.maxy)] = np.nan

        return slope_data

    # Interpolate Slope data, input lat, lon can be arrays or single. Converts to x/y in slope map
    # projection and calls interp_slope. Returns the interpolated slope(s) at lat, lon

    def interp_slope_from_lat_lon(
        self, lat: np.ndarray | float, lon: np.ndarray | float, method: str = "linear"
    ):
        """Interpolate Slope data

        Args:
            lat (np.ndarray | float): array or single latitude value(s)
            lon (np.ndarray | float): array or single longitude value(s)
            method (str, optional): interpolation method. Defaults to "linear".

        Returns:
            np.ndarray: slope values at each lat,lon location
        """
        if not isinstance(lat, np.ndarray):
            lat = np.array(lat)
        if not isinstance(lon, np.ndarray):
            lon = np.array(lon)

        (
            thisx,
            thisy,
        ) = self.lonlat_to_xy_transformer.transform(lon, lat)

        slope_data = self.interp_slope(thisx, thisy, method=method)

        return slope_data
