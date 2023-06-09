"""Class for area masking
"""

import logging
from os import environ
from os.path import isfile
from typing import Optional

import numpy as np
from netCDF4 import Dataset  # pylint: disable=E0611
from pyproj import CRS  # CRS definitions
from pyproj import Transformer  # for transforming between projections

log = logging.getLogger(__name__)

# list of all supported mask names
mask_list = [
    "greenland_area_xylimits_mask",  # rectangular mask for Greenland
    "antarctica_bedmachine_v2_grid_mask",  # Antarctic Bedmachine v2 surface type mask
    "greenland_bedmachine_v3_grid_mask",  # Greenland Bedmachine v3 surface type mask
    "antarctica_iceandland_dilated_10km_grid_mask",  # Antarctic ice (grounded+floating) and
    # ice free land mask (source BedMachine v2) ,
    # dilated by 10km out into the ocean
    "greenland_iceandland_dilated_10km_grid_mask",  # Greenland ice (grounded+floating) and ice free
    # land mask  (source BedMachine v3) , dilated by
    # 10km out into the ocean
    "antarctic_grounded_and_floating_2km_grid_mask",
    # Antarctic grounded and floating ice, 2km grid, source: Zwally 2012
    "greenland_icesheet_2km_grid_mask",
    # Greenland ice sheet grounded ice mask, from 2km grid, source: Zwally 2012. Can select basins
    "antarctic_icesheet_2km_grid_mask_rignot2016",
    # Antarctic ice sheet grounded ice mask + islands, from 2km grid, source: Rignot 2016
    "greenland_icesheet_2km_grid_mask_rignot2016",
    # Greenland ice sheet grounded ice mask, from 2km grid, source: Rignot 2016. Can select basins
]

# too-many-instance-attributes, pylint: disable=R0902
# too-many-statements, pylint: disable=R0915
# too-many-branches, pylint: disable=R0912


class Mask:
    """class to handle area masking"""

    def __init__(
        self,
        mask_name: str,
        basin_numbers: Optional[list[int]] = None,
        mask_path: Optional[str] = None,
    ) -> None:
        """class initialization

        Args:
            mask_name (str): mask name, must be in global mask_list
            basin_numbers (list[int], optional): list of grid values to select from grid masks
                                                 def=None
            mask_path (str, optional): override default path of mask data file

        """
        self.mask_name = mask_name
        self.basin_numbers = basin_numbers

        self.mask_type = None  # 'xylimits', 'polygon', 'grid','latlimits'

        self.crs_wgs = CRS("epsg:4326")  # assuming you're using WGS84 geographic

        # ---------------------------------------------------------------------------
        # Define the limits,bounds or polygons of each mask
        # ---------------------------------------------------------------------------

        if mask_name not in mask_list:
            raise ValueError(f"{mask_name} not in supported mask_list")

        log.info("Setting up %s..", mask_name)

        # -----------------------------------------------------------------------------

        if mask_name == "greenland_area_xylimits_mask":
            # Greenland rectangular mask for rapid masking
            self.mask_type = "xylimits"  # 'xylimits', 'polygon', 'grid','latlimits'

            self.xlimits = [
                -630000,
                904658,
            ]  # [minx, maxx] in m, in current  coordinate system
            self.ylimits = [
                -3355844,
                -654853,
            ]  # [miny, maxy] in m, in current  coordinate system
            self.crs_bng = CRS(
                "epsg:3413"
            )  # Polar Stereo - North -latitude of origin 70N, 45W

        # -----------------------------------------------------------------------------

        elif mask_name == "antarctica_bedmachine_v2_grid_mask":
            # Antarctica surface type grid mask from BedMachine v2, 500m resolution
            #    - 0='Ocean', 1='Ice-free land',2='Grounded ice',3='Floating ice',4='Lake Vostok'

            self.mask_type = "grid"  # 'xylimits', 'polygon', 'grid','latlimits'

            if mask_path is None:
                mask_file = (
                    f'{environ["CPDATA_DIR"]}/RESOURCES/surface_discrimination_masks'
                    "/antarctica/bedmachine_v2/BedMachineAntarctica_2020-07-15_v02.nc"
                )
            else:
                mask_file = mask_path

            if not isfile(mask_file):
                log.error("mask file %s does not exist", mask_file)
                raise FileNotFoundError("mask file does not exist")

            # read netcdf file
            nc = Dataset(mask_file)

            self.num_x = nc.dimensions["x"].size
            self.num_y = nc.dimensions["y"].size

            self.minxm = -3333000
            self.minym = -3333000
            self.binsize = 500
            self.mask_grid = np.array(nc.variables["mask"][:]).astype(int)
            self.mask_grid = np.flipud(self.mask_grid)
            nc.close()
            self.crs_bng = CRS("epsg:3031")  # Polar Stereo - South (71S, 0E)
            self.mask_grid_possible_values = [0, 1, 2, 3, 4]  # values in the mask_grid
            self.grid_value_names = [
                "Ocean",
                "Ice-free land",
                "Grounded ice",
                "Floating ice",
                "Lake Vostok",
            ]
            self.grid_colors = ["blue", "brown", "grey", "green", "red"]

        # -----------------------------------------------------------------------------

        elif mask_name == "greenland_bedmachine_v3_grid_mask":
            # Greenland surface type grid mask from BedMachine v3, 150m resolution
            #   - 0='Ocean', 1='Ice-free land',2='Grounded ice',3='Floating ice',
            #     4='non-Greenland land'

            self.mask_type = "grid"  # 'xylimits', 'polygon', 'grid','latlimits'
            # read netcdf file

            if not mask_path:
                mask_file = (
                    f'{environ["CPDATA_DIR"]}/RESOURCES/surface_discrimination_masks'
                    "/greenland/bedmachine_v3/BedMachineGreenland-2017-09-20.nc"
                )
            else:
                mask_file = mask_path

            if not isfile(mask_file):
                log.error("mask file %s does not exist", mask_file)
                raise FileNotFoundError("mask file does not exist")

            # read netcdf file

            nc = Dataset(mask_file)

            self.num_x = nc.dimensions["x"].size
            self.num_y = nc.dimensions["y"].size
            self.binsize = 150
            self.minxm = -652925
            self.minym = -632675 - (self.num_y * self.binsize)
            self.mask_grid = np.array(nc.variables["mask"][:]).astype(int)
            self.mask_grid = np.flipud(self.mask_grid)
            nc.close()
            del nc
            self.crs_bng = CRS("epsg:3413")  # Polar Stereo - South (70N, 45W)
            self.mask_grid_possible_values = [0, 1, 2, 3, 4]  # values in the mask_grid
            self.grid_value_names = [
                "Ocean",  # 0
                "Ice-free land",  # 1
                "Grounded ice",  # 2
                "Floating ice",  # 3
                "Non-Greenland land",  # 4
            ]
            self.grid_colors = ["blue", "brown", "grey", "green", "white"]

        # -----------------------------------------------------------------------------

        # Antarctica surface type grid mask derived from BedMachine v2, 500m resolution
        #    - 0='Other', 1='Ice (grounded+floating)+ice-free land, dilated by 10km in to  ocean'
        elif mask_name == "antarctica_iceandland_dilated_10km_grid_mask":
            self.mask_type = "grid"  # 'xylimits', 'polygon', 'grid','latlimits'

            if not mask_path:
                mask_file = (
                    f'{environ["CPDATA_DIR"]}/RESOURCES/surface_discrimination_masks'
                    "/antarctica/bedmachine_v2/dilated_10km_mask.npz"
                )
            else:
                mask_file = mask_path

            if not isfile(mask_file):
                log.error("mask file %s does not exist", mask_file)
                raise FileNotFoundError("mask file does not exist")

            self.num_x = 13333
            self.num_y = 13333
            self.minxm = -3333000
            self.minym = -3333000
            self.binsize = 500  # meters
            self.crs_bng = CRS("epsg:3031")  # Polar Stereo - South (71S, 0E)
            self.mask_grid = np.load(mask_file, allow_pickle=True).get("mask_grid")
            self.mask_grid_possible_values = [0, 1]  # values in the mask_grid
            self.grid_value_names = ["outside", "inside Antarctic dilated mask"]
            self.grid_colors = ["blue", "darkgrey"]
        # -----------------------------------------------------------------------------

        # Greenland surface type grid mask derived from BedMachine v3, 150m resolution
        #    - 0='Other', 1='Ice (grounded+floating)+ice-free land, dilated by 10km in to  ocean'
        elif mask_name == "greenland_iceandland_dilated_10km_grid_mask":
            self.mask_type = "grid"  # 'xylimits', 'polygon', 'grid','latlimits'

            if not mask_path:
                mask_file = (
                    f'{environ["CPDATA_DIR"]}/RESOURCES/surface_discrimination_masks'
                    "/greenland/bedmachine_v3/dilated_10km_mask.npz"
                )
            else:
                mask_file = mask_path

            if not isfile(mask_file):
                log.error("mask file %s does not exist", mask_file)
                raise FileNotFoundError("mask file does not exist")

            self.num_x = 10218
            self.num_y = 18346
            self.binsize = 150  # meters
            self.minxm = -652925
            self.minym = -632675 - (self.num_y * self.binsize)
            self.crs_bng = CRS("epsg:3413")  # Polar Stereo - South (70N, 45W)

            self.mask_grid = np.load(mask_file, allow_pickle=True).get("mask_grid")
            self.mask_grid_possible_values = [0, 1]  # values in the mask_grid
            self.grid_value_names = ["outside", "inside Greenland dilated mask"]
            self.grid_colors = ["blue", "darkgrey"]
        # -----------------------------------------------------------------------------

        elif mask_name == "antarctic_grounded_and_floating_2km_grid_mask":
            self.mask_type = "grid"  # 'xylimits', 'polygon', 'grid','latlimits'

            if not mask_path:
                mask_file = (
                    f'{environ["CPOM_SOFTWARE_DIR"]}/cpom/resources/drainage_basins/antarctica'
                    "/zwally_2012_imbie1_ant_grounded_and_floating_icesheet_basins/"
                    "basins/zwally_2012_imbie1_ant_grounded_and_floating_icesheet_basins_2km.nc"
                )
            else:
                mask_file = mask_path

            if not isfile(mask_file):
                log.error("mask file %s does not exist", mask_file)
                raise FileNotFoundError("mask file does not exist")

            nc = Dataset(mask_file)

            self.num_x = nc.dimensions["ANT_ZWALLY_BASINMASK_INCFLOATING_ICE_NX"].size
            self.num_y = nc.dimensions["ANT_ZWALLY_BASINMASK_INCFLOATING_ICE_NY"].size

            self.minxm = nc.variables["ANT_ZWALLY_BASINMASK_INCFLOATING_ICE_MINXM"][:]
            self.minym = nc.variables["ANT_ZWALLY_BASINMASK_INCFLOATING_ICE_MINYM"][:]
            self.binsize = nc.variables["binsize"][:]
            self.mask_grid = nc.variables["ANT_ZWALLY_BASINMASK_INCFLOATING_ICE"][:]
            nc.close()

            self.mask_grid_possible_values = list(range(28))  # values in the mask_grid
            self.grid_value_names = [f"Basin-{i}" for i in range(28)]
            self.grid_value_names[0] = "Unknown"

            self.crs_bng = CRS("epsg:3031")  # Polar Stereo - South -71S

        elif mask_name == "greenland_icesheet_2km_grid_mask":
            self.mask_type = "grid"  # 'xylimits', 'polygon', 'grid','latlimits'

            if not mask_path:
                mask_file = (
                    f'{environ["CPOM_SOFTWARE_DIR"]}/cpom/resources/drainage_basins/greenland/'
                    "zwally_2012_grn_icesheet_basins/basins/Zwally_GIS_basins_2km.nc"
                )
            else:
                mask_file = mask_path

            if not isfile(mask_file):
                log.error("mask file %s does not exist", mask_file)
                raise FileNotFoundError("mask file does not exist")

            nc = Dataset(mask_file)

            self.num_x = nc.dimensions["gre_basin_nx"].size
            self.num_y = nc.dimensions["gre_basin_ny"].size

            self.minxm = nc.variables["gre_basin_minxm"][:]
            self.minym = nc.variables["gre_basin_minym"][:]
            self.binsize = nc.variables["gre_basin_binsize"][:]
            self.mask_grid = np.array(nc.variables["gre_basin_mask"][:]).astype(int)
            nc.close()
            self.crs_bng = CRS(
                "epsg:3413"
            )  # Polar Stereo - North -latitude of origin 70N, 45
            self.grid_value_names = [
                "None",
                "1.1",
                "1.2",
                "1.3",
                "1.4",
                "2.1",
                "2.2",
                "3.1",
                "3.2",
                "3.3",
                "4.1",
                "4.2",
                "4.3",
                "5.0",
                "6.1",
                "6.2",
                "7.1",
                "7.2",
                "8.1",
                "8.2",
            ]
            self.mask_grid_possible_values = list(range(20))  # values in the mask_grid
            self.grid_colors = [
                "blue",
                "bisque",
                "darkorange",
                "moccasin",
                "gold",
                "greenyellow",
                "yellowgreen",
                "gray",
                "lightgray",
                "silver",
                "purple",
                "sandybrown",
                "peachpuff",
                "coral",
                "tomato",
                "navy",
                "lavender",
                "olivedrab",
                "lightyellow",
                "sienna",
            ]

        elif mask_name == "antarctic_icesheet_2km_grid_mask_rignot2016":
            # basin mask values are : 0..18, or 999 (unknown)
            #
            self.mask_type = "grid"  # 'xylimits', 'polygon', 'grid','latlimits'

            if not mask_path:
                mask_file = (
                    f'{environ["CPOM_SOFTWARE_DIR"]}/cpom/resources/drainage_basins/antarctica/'
                    "rignot_2016_imbie2_ant_grounded_icesheet_basins/basins/"
                    "rignot_2016_imbie2_ant_grounded_icesheet_basins_2km.nc"
                )
            else:
                mask_file = mask_path

            if not isfile(mask_file):
                log.error("mask file %s does not exist", mask_file)
                raise FileNotFoundError("mask file does not exist")

            nc = Dataset(mask_file)

            self.num_x = 2820
            self.num_y = 2420
            self.minxm = -2820000  # meters
            self.minym = -2420000  # meters
            self.binsize = 2000  # meters
            self.mask_grid = nc.variables["basinmask"][:]
            nc.close()

            self.mask_grid_possible_values = list(range(19))  # values in the mask_grid
            self.grid_value_names = [
                "Islands",
                "West H-Hp",
                "West F-G",
                "East E-Ep",
                "East D-Dp",
                "East Cp-D",
                "East B-C",
                "East A-Ap",
                "East Jpp-K",
                "West G-H",
                "East Dp-E",
                "East Ap-B",
                "East C-Cp",
                "East K-A",
                "West J-Jpp",
                "Peninsula Ipp-J",
                "Peninsula I-Ipp",
                "Peninsula Hp-I",
                "West Ep-F",
            ]

            self.crs_bng = CRS("epsg:3031")  # Polar Stereo - South -71S

        elif mask_name == "greenland_icesheet_2km_grid_mask_rignot2016":
            self.mask_type = "grid"  # 'xylimits', 'polygon', 'grid','latlimits'

            if not mask_path:
                mask_file = (
                    f'{environ["CPOM_SOFTWARE_DIR"]}/cpom/resources/drainage_basins/greenland/'
                    "GRE_Basins_IMBIE2_v1.3/basins/"
                    "rignot_2016_imbie2_grn_grounded_icesheet_basins_2km.nc"
                )
            else:
                mask_file = mask_path

            if not isfile(mask_file):
                log.error("mask file %s does not exist", mask_file)
                raise FileNotFoundError("mask file does not exist")

            nc = Dataset(mask_file)

            self.crs_bng = CRS(
                "epsg:3413"
            )  # Polar Stereo - North -latitude of origin 70N, 45

            self.num_x = 1000
            self.num_y = 1550
            self.minxm = -1000000  # meters
            self.minym = -3500000  # meters
            self.binsize = 2000  # meters
            self.mask_grid = nc.variables["basinmask"][:]
            nc.close()

            self.mask_grid_possible_values = list(range(57))  # values in the mask_grid

            # 0 (unclassified), 1-50 (ice caps), 51 (NW), 52(CW), 53(SW), 54(SE), 55(NE), 56(NO)
            self.grid_value_names = ["Ice cap -" + str(i) for i in range(57)]
            self.grid_value_names[0] = "unclassified"
            self.grid_value_names[51] = "NW"
            self.grid_value_names[52] = "CW"
            self.grid_value_names[53] = "SW"
            self.grid_value_names[54] = "SE"
            self.grid_value_names[55] = "NE"
            self.grid_value_names[56] = "NO"

            self.crs_bng = CRS(
                "epsg:3413"
            )  # Polar Stereo - North -latitude of origin 70N, 45

        else:
            raise ValueError(f"mask name: {mask_name} not supported")

        # -----------------------------------------------------------------------------

        # Setup the Transforms
        self.xy_to_lonlat_transformer = Transformer.from_proj(
            self.crs_bng, self.crs_wgs, always_xy=True
        )
        self.lonlat_to_xy_transformer = Transformer.from_proj(
            self.crs_wgs, self.crs_bng, always_xy=True
        )

    def points_inside(
        self,
        lats: np.ndarray,
        lons: np.ndarray,
        basin_numbers: Optional[list[int]] = None,
        inputs_are_xy: bool = False,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """find points inside mask

        returns array of bool indicating where (lat,lon) or (x,y) points  are inside a mask.
        It also returns (x,y) of all points to save having to transform
        them again.

        Args:
            lats (np.ndarray|list[float]): list of latitude points
            lons (np.ndarray|list[float]): list of longitude points
            basin_numbers (list[int,], optional): list of basin numbers. Defaults to None.
            inputs_are_xy (bool, optional): lats, lons are already transformed to x,y.
                                            Defaults to False.

        Returns:
            inmask(np.ndarray),x(np.ndarray),y(np.ndarray) : true where inside mask,
                                                             transformed x locations, (all points)
                                                             transformed y locations (all points)
        """

        if not self.mask_name:
            inmask = np.zeros(lats.size, np.bool_)
            return inmask, None, None

        if not isinstance(lats, np.ndarray):
            if isinstance(lats, list):
                lats = np.array(lats)
            else:
                raise TypeError("lats is wrong type. Must be np.ndarray or list[float]")

        if not isinstance(lons, np.ndarray):
            if isinstance(lons, list):
                lons = np.array(lons)
            else:
                raise TypeError("lons is wrong type. Must be np.ndarray or list[float]")

        if basin_numbers:  # turn in to a list if a scalar
            if not isinstance(basin_numbers, (list, np.ndarray)):
                basin_numbers = [basin_numbers]

        if self.basin_numbers:
            if not basin_numbers:
                basin_numbers = self.basin_numbers

        if inputs_are_xy:
            x, y = lats, lons
        else:
            x, y = self.latlon_to_xy(lats, lons)  # pylint: disable=E0633

        inmask = np.zeros(lats.size, np.bool_)

        # ---------------------------------------------------------
        # Find points inside a x,y rectangular limits mask
        # ---------------------------------------------------------

        if self.mask_type == "xylimits":
            for i in range(x.size):
                if (x[i] >= self.xlimits[0] and x[i] <= self.xlimits[1]) and (
                    y[i] >= self.ylimits[0] and y[i] <= self.ylimits[1]
                ):
                    inmask[i] = True
            return inmask, x, y

        if self.mask_type == "grid":
            for i in range(x.size):
                # calculate equivalent (ii,jj) in mask array
                ii = int(np.around((x[i] - self.minxm) / self.binsize))
                jj = int(np.around((y[i] - self.minym) / self.binsize))

                # Check bounds of Basin Mask array
                if ii < 0 or ii >= self.num_x:
                    continue
                if jj < 0 or jj >= self.num_y:
                    continue

                if basin_numbers:
                    for basin in basin_numbers:
                        if self.mask_grid[jj, ii] == basin:
                            inmask[i] = True
                else:
                    if self.mask_grid[jj, ii] > 0:
                        inmask[i] = True
        else:
            return inmask, None, None

        return inmask, x, y

    def grid_mask_values(
        self, lats: np.ndarray, lons: np.ndarray, inputs_are_xy=False
    ) -> np.ndarray:
        """Return the grid mask value at each input lats, lons interpolated grid location

        Args:
            lats (np.ndarray): array of latitude (N) values in degrees
            lons (np.ndarray): array of longitude (E) values in degrees
            inputs_are_xy (bool): inputs are x,y values (m) instead of latitude, longitude values

        Returns:
            mask_values (np.ndarray): grid mask value at each input lats, lons interpolated
                                 grid location or np.NaN is outside area

        """

        if self.mask_type != "grid":
            raise ValueError(
                (
                    "grid_mask_values can only be used on grid mask types."
                    " Use points_inside() for other masks"
                )
            )

        if np.isscalar(lats):
            lats = np.asarray([lats])
            lons = np.asarray([lons])
        else:
            lats = np.asarray(lats)
            lons = np.asarray(lons)

        # Convert to x,y (m) in mask coordinate system
        if inputs_are_xy:
            x, y = lats, lons
        else:
            (x, y) = self.latlon_to_xy(lats, lons)  # pylint: disable=E0633

        mask_values = np.full(lats.size, np.NaN)

        for i in range(0, lats.size):
            # check that x,y is not Nan
            if not np.isfinite(x[i]):
                continue

            # calculate equivalent (ii,jj) in mask array
            ii = int(np.around((x[i] - self.minxm) / self.binsize))
            jj = int(np.around((y[i] - self.minym) / self.binsize))

            # Check bounds of Basin Mask array
            if ii < 0 or ii >= self.num_x:
                continue
            if jj < 0 or jj >= self.num_y:
                continue

            mask_values[i] = self.mask_grid[jj, ii]
        return mask_values

    def latlon_to_xy(self, lats: np.ndarray, lons: np.ndarray) -> tuple:
        """
        :param lats: latitude points in degs
        :param lons: longitude points in degrees E
        :return: x,y in polar stereo projection of mask
        """
        return self.lonlat_to_xy_transformer.transform(lons, lats)
