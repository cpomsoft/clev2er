"""clev2er.utils.dhdt_data.dhdt

class to read dh/dt grid data
"""
import logging
import os

import numpy as np
import rasterio  # to extract GeoTIFF extents
from netCDF4 import Dataset  # pylint:disable=E0611
from pyproj import CRS  # coordinate reference system
from pyproj import Transformer  # transforms
from rasterio.errors import RasterioIOError
from scipy.interpolate import interpn
from scipy.ndimage import median_filter
from tifffile import imread  # to support large TIFF files

# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-locals

log = logging.getLogger(__name__)


# List of supported dh/dt data
#   - add to this list if you add a new dh/dt data resource
dhdt_list = [
    "grn_2010_2021",  # Greenland dh/dt grid
    "grn_is2_is1_smith",  # GrIS dh/dt from IS2-IS1, Smith, 2020, doi.org/10.1126/science.aaz5845
    "ais_is2_is1_smith",  # AIS dh/dt from IS2-IS1, Smith, 2020, doi.org/10.1126/science.aaz5845
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
        self.dhdt = np.array([])
        self.xdem = np.array([])
        self.ydem = np.array([])
        self.mindemx: float | None = None
        self.mindemy: float | None = None
        self.binsize: int | None = None

        if thislog is not None:
            self.log = thislog  # optionally attach to a different log instance
        else:
            self.log = log

        if name not in dhdt_list:
            self.log.error("Dh/dt dataset name %s not in allowed list", name)
            raise ValueError(f"Dh/dt name {name} not in allowed list")

        self.load()

    def get_geotiff_extent(self, fname: str):
        """Get info from GeoTIFF on its extent

        Args:
            fname (str): path of GeoTIFF file

        Raises:
            ValueError: _description_
            IOError: _description_

        Returns:
            tuple(int,int,int,int,int,int,int): width,height,top_left,top_right,bottom_left,
            bottom_right,pixel_width
        """
        try:
            with rasterio.open(fname) as dataset:
                transform = dataset.transform
                width = dataset.width
                height = dataset.height

                top_left = transform * (0, 0)
                top_right = transform * (width, 0)
                bottom_left = transform * (0, height)
                bottom_right = transform * (width, height)

                pixel_width = transform[0]
                pixel_height = -transform[4]  # Negative because the height is
                # typically negative in GeoTIFFs
                if pixel_width != pixel_height:
                    raise ValueError(
                        f"pixel_width {pixel_width} != pixel_height {pixel_width}"
                    )
        except RasterioIOError as exc:
            raise IOError(f"Could not read GeoTIFF: {exc}") from exc
        return (
            width,
            height,
            top_left,
            top_right,
            bottom_left,
            bottom_right,
            pixel_width,
        )

    def load_geotiff(
        self,
        dhdt_file: str,
        flip_y: bool = True,
        median_filter_width: int | None = None,
        abs_filter: int | None = None,
    ):
        """Load a GeoTIFF file

        Args:
            dhdt_file (str): path of GeoTIFF
            flip_y (bool): if True flip the dhdt data in y dirn
            median_filter_width (int|None): median filter width
            abs_filter (int| None): set dhdt to np.Nan where abs(dhdt) > abs_filter
        """
        (
            ncols,
            nrows,
            top_l,
            top_r,
            bottom_l,
            _,
            binsize,
        ) = self.get_geotiff_extent(dhdt_file)

        self.dhdt = imread(dhdt_file)

        # Set void data to Nan
        if self.void_value:
            void_data = np.where(self.dhdt == self.void_value)
            if np.any(void_data):
                self.dhdt[void_data] = np.nan

        self.xdem = np.linspace(top_l[0], top_r[0], ncols, endpoint=True)
        self.ydem = np.linspace(bottom_l[1], top_l[1], nrows, endpoint=True)
        if flip_y:
            self.ydem = np.flip(self.ydem)
        self.mindemx = self.xdem.min()
        self.mindemy = self.ydem.min()
        self.binsize = binsize  # grid resolution in m

        if abs_filter:
            void_data = np.where(np.abs(self.dhdt) > abs_filter)
            if np.any(void_data):
                self.dhdt[void_data] = np.nan

        if median_filter_width:
            self.dhdt = median_filter(self.dhdt, size=median_filter_width)

    def load(
        self,
    ):
        """Read the dhdt file, setting up required variables

        Raises:
            ValueError: if self.name not found in allowed list
        """
        if self.name == "grn_is2_is1_smith":
            self.filename = "gris_dhdt.tif"  # or gris_dhdt_filt.tif
            self.default_dir = (
                f'{os.environ["CPDATA_DIR"]}/RESOURCES/dhdt_data/smith2020_is2_is1'
            )
            filename = self.get_filename(self.default_dir, self.filename)
            self.crs_wgs = CRS("epsg:4326")  #  WGS84
            self.crs_bng = CRS(
                "epsg:3413"
            )  # Polar Stereo - North -lat of origin 70N, 45
            self.void_value = -9999
            self.dtype = np.float32

            self.load_geotiff(
                filename, flip_y=False, median_filter_width=3, abs_filter=10.0
            )
        elif self.name == "ais_is2_is1_smith":
            self.filename = (
                "ais_dhdt_grounded_filt.tif"  # or ais_dhdt_grounded_filt.tif
            )
            self.default_dir = (
                f'{os.environ["CPDATA_DIR"]}/RESOURCES/dhdt_data/smith2020_is2_is1'
            )
            filename = self.get_filename(self.default_dir, self.filename)
            self.crs_wgs = CRS("epsg:4326")  #  WGS84
            self.crs_bng = CRS("epsg:3031")  # Polar Stereo - South -71S
            self.void_value = -9999
            self.dtype = np.float32

            self.load_geotiff(
                filename, flip_y=False, median_filter_width=3, abs_filter=10.0
            )

        elif self.name == "grn_2010_2021":
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
            self.log.error("%s : file not found", this_path)
            raise OSError(f"{this_path} not found")

        return this_path
