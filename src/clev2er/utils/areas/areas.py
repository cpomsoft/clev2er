"""clev2er.utils.areas.areas.py: Area class to define areas for polar plotting
"""

import importlib
import logging

import numpy as np
from pyproj import CRS  # Transformer transforms between projections
from pyproj import Transformer  # Transformer transforms between projections

from clev2er.utils.masks.masks import Mask

# pylint: disable=too-many-statements
# pylint: disable=too-many-instance-attributes

log = logging.getLogger(__name__)


class Area:
    """class to define polar areas for plotting etc"""

    def __init__(self, name: str):
        """class initialization

        Args:
            name (str): area name. Must be in all_areas
        """

        self.name = name

        try:
            self.load_area()
        except ImportError as exc:
            raise ImportError(f"{name} not in supported area list") from exc

        if self.apply_area_mask_to_data:
            if self.masktype is not None:
                if self.masktype == "grid" and self.grid_polygon_overlay_mask:
                    self.mask = Mask(self.grid_polygon_overlay_mask, self.basin_numbers)
                else:
                    self.mask = Mask(self.maskname, self.basin_numbers)

    def load_area(self):
        """Load area settings for current area name"""

        try:
            module = importlib.import_module(f"clev2er.utils.areas.definitions.{self.name}")
        except ImportError as exc:
            raise ImportError(f"Could not load area definition: {self.name}") from exc

        area_definition = module.area_definition

        secondary_area_name = area_definition.get("use_definitions_from", None)
        if secondary_area_name is not None:
            log.info("loading secondary area %s", secondary_area_name)
            try:
                module2 = importlib.import_module(
                    f"clev2er.utils.areas.definitions.{secondary_area_name}"
                )
            except ImportError as exc:
                raise ImportError(f"Could not load area definition: {secondary_area_name}") from exc
            area_definition2 = module2.area_definition
            area_definition2.update(area_definition)
            area_definition = area_definition2

        # store parameters from the area definition dict in class variables
        self.long_name = area_definition["long_name"]
        # Area spec.
        self.hemisphere = area_definition["hemisphere"]
        self.centre_lon = area_definition.get("centre_lon")
        self.centre_lat = area_definition.get("centre_lat")
        self.lon_0 = area_definition.get("lon_0")
        self.width_km = area_definition.get("width_km")
        self.height_km = area_definition.get("height_km")
        self.crs_number = area_definition.get("crs_number")
        self.specify_by_centre = area_definition.get("specify_by_centre", False)
        self.specify_by_bounding_lat = area_definition.get("specify_by_bounding_lat", False)
        self.specify_plot_area_by_lowerleft_corner = area_definition.get(
            "specify_plot_area_by_lowerleft_corner", False
        )
        self.llcorner_lat = area_definition.get("llcorner_lat")
        self.llcorner_lon = area_definition.get("llcorner_lon")
        self.epsg_number = area_definition.get("epsg_number")
        self.round = area_definition.get("round", False)
        self.bounding_lat = area_definition.get("bounding_lat")
        self.min_elevation = area_definition.get("min_elevation", 0)
        self.max_elevation = area_definition.get("max_elevation", 5000)
        self.max_elevation_dem = area_definition.get("max_elevation_dem", 5000)

        # Data filtering
        self.apply_area_mask_to_data = area_definition.get("apply_area_mask_to_data", True)
        self.minlon = area_definition.get("minlon")
        self.maxlon = area_definition.get("maxlon")
        self.minlat = area_definition.get("minlat")
        self.maxlat = area_definition.get("maxlat")
        self.maskname = area_definition.get("maskname")
        self.masktype = area_definition.get("masktype")
        self.basin_numbers = area_definition.get("basin_numbers", None)
        self.show_polygon_mask = area_definition.get("show_polygon_mask", False)
        self.polygon_mask_color = area_definition.get("polygon_mask_color", "red")

        # Plot parameters
        self.axes = area_definition.get("axes")
        self.background_color = area_definition.get("background_color", None)
        self.background_image = area_definition.get("background_image", None)
        self.background_image_alpha = area_definition.get("background_image_alpha", 1.0)
        self.background_image_resolution = area_definition.get("background_image_alpha", "medium")
        self.hillshade_params = area_definition.get("hillshade_params", None)
        self.draw_axis_frame = area_definition.get("draw_axis_frame")
        self.add_lakes_feature = area_definition.get("add_lakes_feature", None)
        self.add_rivers_feature = area_definition.get("add_rivers_feature", None)
        self.add_country_boundaries = area_definition.get("add_country_boundaries", None)
        self.add_province_boundaries = area_definition.get("add_province_boundaries", None)
        self.show_polygon_overlay_in_main_map = area_definition.get(
            "show_polygon_overlay_in_main_map", True
        )
        self.grid_polygon_overlay_mask = area_definition.get("grid_polygon_overlay_mask", None)
        self.apply_hillshade_to_vals = area_definition.get("apply_hillshade_to_vals", False)
        self.draw_coastlines = area_definition.get("draw_coastlines", True)
        self.coastline_color = area_definition.get("coastline_color", "grey")
        self.use_antarctica_medium_coastline = area_definition.get(
            "use_antarctica_medium_coastline", False
        )
        self.use_cartopy_coastline = area_definition.get("use_cartopy_coastline", None)
        self.show_gridlines: bool = area_definition.get("show_gridlines", True)
        # Colormap
        self.cmap_name = area_definition.get("cmap_name", "RdYlBu_r")
        self.cmap_over_color = area_definition.get("cmap_over_color", "#A85754")
        self.cmap_under_color = area_definition.get("cmap_under_color", "#3E4371")
        self.cmap_extend = area_definition.get("cmap_extend", "both")
        # Colour bar
        self.draw_colorbar = area_definition.get("draw_colorbar", True)
        self.colorbar_orientation = area_definition.get("colorbar_orientation", "vertical")
        self.vertical_colorbar_axes = area_definition.get(
            "vertical_colorbar_axes",
            [
                0.04,
                0.05,
                0.02,
                0.55,
            ],
        )
        self.horizontal_colorbar_axes = area_definition.get(
            "horizontal_colorbar_axes",
            [
                0.08,
                0.05,
                0.55,
                0.02,
            ],
        )

        # Grid lines
        self.longitude_gridlines = np.asarray(area_definition.get("longitude_gridlines")).astype(
            "float"
        )
        self.longitude_gridlines[self.longitude_gridlines > 180.0] -= 360.0

        self.latitude_gridlines = area_definition.get("latitude_gridlines")
        self.gridline_color: str = area_definition.get("gridline_color", "lightgrey")
        self.gridlabel_color = area_definition.get("gridlabel_color", "darkgrey")
        self.gridlabel_size = area_definition.get("gridlabel_size", 9)
        self.inner_gridlabel_color = area_definition.get("inner_gridlabel_color", "k")
        self.inner_gridlabel_size = area_definition.get("inner_gridlabel_size", 9)
        self.latitude_of_radial_labels = area_definition.get("latitude_of_radial_labels", None)
        self.latline_label_axis_positions = area_definition.get("latline_label_axis_positions")
        self.lonline_label_axis_positions = area_definition.get("lonline_label_axis_positions")

        # Mini-map
        self.show_minimap = area_definition.get("show_minimap")
        self.minimap_axes = area_definition.get("minimap_axes")
        self.minimap_bounding_lat = area_definition.get("minimap_bounding_lat")
        self.minimap_circle = area_definition.get("minimap_circle", None)
        self.minimap_draw_gridlines = area_definition.get("minimap_draw_gridlines", True)
        self.minimap_val_scalefactor = area_definition.get("minimap_val_scalefactor", 1.0)
        self.minimap_legend_pos = area_definition.get("minimap_legend_pos", (1.0, 1.0))
        # Scale bar
        self.show_scalebar = area_definition.get("show_scalebar")
        self.mapscale = area_definition.get("mapscale")

        self.crs_wgs = CRS("epsg:4326")  # assuming you're using WGS84 geographic
        self.crs_bng = CRS(f"epsg:{self.epsg_number}")
        # Histograms
        self.histogram_plotrange_axes = area_definition.get(
            "histogram_plotrange_axes",
            [
                0.735,  # left
                0.3,  # bottom
                0.08,  # width (axes fraction)
                0.35,  # height (axes fraction)
            ],
        )
        self.histogram_fullrange_axes = area_definition.get(
            "histogram_fullrange_axes",
            [
                0.89,  # left
                0.3,  # bottom
                0.08,  # width (axes fraction)
                0.35,  # height (axes fraction)
            ],
        )
        self.latvals_axes = area_definition.get(
            "latvals_axes",
            [
                0.77,  # left
                0.05,  # bottom
                0.17,  # width (axes fraction)
                0.2,  # height (axes fraction)
            ],
        )

        # Setup the Transforms
        self.xy_to_lonlat_transformer = Transformer.from_proj(
            self.crs_bng, self.crs_wgs, always_xy=True
        )
        self.lonlat_to_xy_transformer = Transformer.from_proj(
            self.crs_wgs, self.crs_bng, always_xy=True
        )

    def latlon_to_xy(self, lats: np.ndarray | float, lons: np.ndarray | float):
        """convert latitude and longitude to x,y in area's projection

        Args:
            lats (np.ndarray): latitude values
            lons (np.ndarray): longitude values

        Returns:
            (np.ndarray,np.ndarray): x,y
        """
        return self.lonlat_to_xy_transformer.transform(lons, lats)

    def xy_to_latlon(self, x, y):
        """convert from x,y to latitide, longitiude in area's projection

        Args:
            x (np.ndarray): x coordinates
            y (np.ndarray): y coordinates

        Returns:
            (np.ndarray,np.ndarray): latitude values, longitude values
        """
        return self.xy_to_lonlat_transformer.transform(x, y)

    def inside_latlon_bounds(self, lats, lons):
        """
        find the locations inside the area's bounding box (note this is not the area mask,
        but a quick filter to reduce the number of points that require masking (which can be slow))

        returns: [latitude values in bounding box] [longitude values in bounding box]
        [indices in box] number_in_box

        """

        in_lat_area = np.logical_and(lats >= self.minlat, lats <= self.maxlat)
        in_lon_area = np.logical_and(lons >= self.minlon, lons <= self.maxlon)
        bounded_indices = np.flatnonzero(in_lat_area & in_lon_area)
        if bounded_indices.size > 0:
            bounded_lats = lats[bounded_indices]
            bounded_lons = lons[bounded_indices]
            return bounded_lats, bounded_lons, bounded_indices, bounded_indices.size

        return None, None, None, 0

    def inside_mask(self, lats, lons):
        """
        Find indices inside the area's data mask (if there is one). If there is no area data mask
        return all indices
        :param lats:
        :param lons:
        :return latitudes inside mask, longitudes inside mask,indices in mask, number inside mask
        """

        # Check the type of lats, lons. they needs to be np.array

        if not isinstance(lats, np.ndarray):
            lats = np.array(lats)
        if not isinstance(lons, np.ndarray):
            lons = np.array(lons)

        if self.mask is None:
            # Check if there is no mask specified for this area
            # if so, return all the locations
            if self.masktype is None:
                # No mask so return all locations
                return lats, lons, list(range(lats.size)), lats.size
            # No mask class is currently loaded so we need to load it now
            self.mask = Mask(self.maskname, self.basin_numbers)

        if self.mask.nomask:
            return lats, lons, list(range(lats.size)), lats.size

        # Mask the lat,lon locations
        inmask, _, _ = self.mask.points_inside(
            lats, lons, self.basin_numbers
        )  # returns (1s for inside, 0s outside), x,y locations of all lat/lon points
        indices_in_maskarea = np.flatnonzero(inmask)

        if indices_in_maskarea.size == 0:
            return None, None, None, 0

        return (
            lats[indices_in_maskarea],
            lons[indices_in_maskarea],
            indices_in_maskarea,
            indices_in_maskarea.size,
        )

    def inside_area(
        self, lats: np.ndarray, lons: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
        """Find indices of lat, lon values inside area's mask
           This function combines self.inside_latlon_bounds() and self.inside_mask
           The purpose of self.inside_latlon_bounds() is to do a quick rectangular area clip
           to make the slower inside_mask() run faster

        Args:
            lats (np.ndarray): _description_
            lons (np.ndarray): _description_

        Returns:
            Tuple[np.ndarray, np.ndarray,np.ndarray,int]: (array of latitude values inside area,
                                                           array of longitude values inside area,
                                                           array of indices of orginal arrays
                                                           inside area,
                                                           number of values inside area)
            or if no values inside area
            (np.array([]),np.array([]),np.array([]),0)
        """
        indices = []
        _, _, bounded_indices, num_bounded = self.inside_latlon_bounds(lats, lons)
        if num_bounded > 0:
            _, _, masked_indices, num_masked = self.inside_mask(
                lats[bounded_indices], lons[bounded_indices]
            )
            if num_masked > 0:
                indices = bounded_indices[masked_indices]
        if len(indices) > 0:
            return (lats[indices], lons[indices], indices, len(indices))

        return (np.array([]), np.array([]), np.array([]), 0)
