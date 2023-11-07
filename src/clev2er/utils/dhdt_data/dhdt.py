"""clev2er.utils.dhdt_data.dhdt

class to read dh/dt grid data
"""
import logging
import os

import numpy as np
from netCDF4 import Dataset  # pylint:disable=E0611
from pyproj import CRS  # coordinate reference system
from pyproj import Transformer  # transforms
from scipy.interpolate import interpn

# pylint: disable=too-many-instance-attributes

log = logging.getLogger(__name__)


# List of supported dh/dt data
#   - add to this list if you add a new dh/dt data resource
dhdt_list = [
    "grn_2010_2021",  # Greenland dh/dt grid
]


class Dhdt:
    """class to load and interpolate dh/dt gridded data set resources"""

    def __init__(
        self,
        name: str,
        thislog: logging.Logger | None = None,
        config: None | dict = None,
        dhdt_dir: str | None = None,
    ):
        """class initialization

        Args:
            name (str): name of dh/dt data set
            thislog (logging.Logger|None, optional): attach to a different log instance
            config (dict, optional): configuration dictionary, defaults to None
            dhdt_dir (str, optional): path of directory containing dh/dt file. Defaults to None

        Raises:
            ValueError: if name not supported in dhdt_list
        """
        self.name = name
        self.config = config
        self.dhdt_dir = dhdt_dir

        if thislog is not None:
            self.log = thislog  # optionally attach to a different log instance
        else:
            self.log = log

        if name not in dhdt_list:
            self.log.error("Dh/dt dataset name %s not in allowed list", name)
            raise ValueError(f"Dh/dt name {name} not in allowed list")

        self.load()

    def load(
        self,
    ):
        """Read the dhdt file, setting up required variables

        Raises:
            ValueError: if self.name not found in allowed list
        """
        if self.name == "grn_2010_2021":
            self.filename = "greenland_dhdt_2011_2022.nc"
            # default_dir provided but will be overridden by config['dhdt_data_dir'][self.name]
            self.default_dir = f'{os.environ["CPDATA_DIR"]}/RESOURCES/dhdt_data'
            self.crs_wgs = CRS("epsg:4326")  #  WGS84
            self.crs_bng = CRS(
                "epsg:3413"
            )  # Polar Stereo - North -lat of origin 70N, 45

            # Find the dataset path/filename
            filename = self.get_filename(self.default_dir, self.filename)

            with Dataset(filename) as nc:
                self.dhdt = nc.variables["dhdt_sm"][:]
                self.xmin = int(nc.variables["x"].getncattr("min"))
                self.xmax = int(nc.variables["x"].getncattr("max"))
                self.ymin = int(nc.variables["y"].getncattr("min"))
                self.ymax = int(nc.variables["y"].getncattr("max"))
                self.ncols = self.dhdt.shape[1]
                self.nrows = self.dhdt.shape[0]

            self.xdem = np.linspace(self.xmin, self.xmax, self.ncols, endpoint=True)
            self.ydem = np.linspace(self.ymin, self.ymax, self.nrows, endpoint=True)
            self.ydem = np.flip(self.ydem)
            self.mindemx = self.xdem.min()
            self.mindemy = self.ydem.min()
            self.binsize = self.xdem[1] - self.xdem[0]  # grid resolution in m

        else:
            raise ValueError(f"loading {self.name} not supported")

        # Setup the Transforms
        self.xy_to_lonlat_transformer = Transformer.from_proj(
            self.crs_bng, self.crs_wgs, always_xy=True
        )
        self.lonlat_to_xy_transformer = Transformer.from_proj(
            self.crs_wgs, self.crs_bng, always_xy=True
        )

    # ----------------------------------------------------------------------------------------------
    # Interpolate DEM, input x,y can be arrays or single, units m, in projection (epsg:3031")
    # returns the interpolated elevation(s) at x,y
    # x,y : x,y cartesian coordinates in the DEM's projection in m
    # OR, when xy_is_latlon is True:
    # x,y : latitude, longitude values in degs N and E (note the order, not longitude, latitude!)
    #
    # method: string containing the interpolation method. Default is 'linear'. Options are
    # “linear” and “nearest”, and “splinef2d” (see scipy.interpolate.interpn docs).
    #
    # Where your input points are outside the DEM area, then np.nan values will be returned
    # ----------------------------------------------------------------------------------------------

    def interp_dhdt(self, x, y, method="nearest", xy_is_latlon=False) -> np.ndarray:
        """Interpolate DEM to return elevation values corresponding to
           cartesian x,y in DEM's projection or lat,lon values

        Args:
            x (np.ndarray): x cartesian coords in the dhdt grid's projection in m, or lat values
            y (np.ndarray): x cartesian coords in the dhdt grid's projection in m, or lon values
            method (str, optional): linear, nearest, splinef2d. Defaults to "linear".
            xy_is_latlon (bool, optional): if True, x,y are lat, lon values. Defaults to False.

        Returns:
            np.ndarray: interpolated dhdt values in m/yr
        """
        # Transform to x,y if inputs are lat,lon
        if xy_is_latlon:
            x, y = self.lonlat_to_xy_transformer.transform(  # pylint: disable=E0633
                y, x
            )  # transform lon,lat -> x,y
        # myydem = np.flip(self.ydem.copy())
        myydem = self.ydem
        myzdem = np.flip(self.dhdt.copy(), 0)
        return interpn(
            (myydem, self.xdem),
            myzdem,
            (y, x),
            method=method,
            bounds_error=False,
            fill_value=np.nan,
        )

    def get_filename(self, default_dir: str, filename: str) -> str:
        """Find the path of the dhdt file from dir and file names :
        For the directory, it is chosen in order of preference:
        a) self.config["dhdt_data_dir"][self.name], or
        b) supplied self.dhdt_dir, or
        c) default_dir
        The file name is:
        filename: is filename

        Args:
            default_dir (str): default dir to find dhdt file names
            filename (str): file name of dhdt
        Returns:
            str : path of dhdt file
        Raises:
            OSError : directory or file not found
        """
        this_dhdt_dir = None
        if self.config:
            if (
                "dhdt_data_dir" in self.config
                and self.name in self.config["dhdt_data_dir"]
            ):
                this_dhdt_dir = self.config["dhdt_data_dir"][self.name]
                self.log.info(
                    "Loading dhdt path from config['dhdt_data_dir']['%s']", self.name
                )
        if this_dhdt_dir is None and self.dhdt_dir:
            this_dhdt_dir = self.dhdt_dir
            self.log.info("Loading dhdt path from supplied dir: %s", self.name)
        if this_dhdt_dir is None:
            self.log.info("Loading dhdt path from default dir for : %s", self.name)
            this_dhdt_dir = default_dir

        if not os.path.isdir(this_dhdt_dir):
            raise OSError(f"{this_dhdt_dir} not found")

        this_path = f"{this_dhdt_dir}/{filename}"

        self.log.info("Loading dhdt file: %s", this_path)

        if not os.path.isfile(this_path):
            raise OSError(f"{this_path} not found")

        return this_path
