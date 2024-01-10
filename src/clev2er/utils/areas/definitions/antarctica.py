"""Area definition"""

area_definition = {
    "long_name": "Antarctica",
    # --------------------------------------------
    # Area definition
    # --------------------------------------------
    "hemisphere": "south",  # area is in  'south' or 'north'
    "specify_by_bounding_lat": True,  # for round hemisphere views
    "bounding_lat": -63.0,  # limiting latitude for round areas or None
    "specify_by_centre": False,  # specify plot area by centre lat/lon, width, height (km)
    "centre_lon": 0.0,  # degrees E
    "centre_lat": -90.0,  # degrees N
    "specify_plot_area_by_lowerleft_corner": False,  # specify by lower left corner, w,h
    "llcorner_lat": None,  # lower left corner latitude
    "llcorner_lon": None,  # lower left corner longitude
    "lon_0": None,  # None or projection y-axis longitude (used for mercator)
    "width_km": 6600,  # width in km of plot area (x direction)
    "height_km": 6100,  # height in km of plot area (y direction)
    "epsg_number": 3031,  # EPSG number for area's projection
    "round": True,  # False=rectangular, True = round map area
    "min_elevation": -50,  # minimum expected elevation in area (m)
    "max_elevation": 4200,  # maximum expected elevation in area (m)
    "max_elevation_dem": 4200,  # maximum expected elevation in area (m) used for DEM backgrounds
    # --------------------------------------------
    # Data filtering
    # --------------------------------------------
    "apply_area_mask_to_data": True,  # filter data using areas mask
    #   Area min/max lat/lon for initial data filtering
    "minlon": 0.0,  # minimum longitude to initially filter records for area (0..360E)
    "maxlon": 360.0,  # maximum longitude to initially filter records for area (0..360E)
    "minlat": -89.0,  # minimum latitude to initially filter records for area
    "maxlat": -62.0,  # maximum latitude to initially filter records for area
    # --------------------------------------------
    #    mask from clev2er.utils.masks.Mask
    # --------------------------------------------
    "maskname": "antarctica_bedmachine_v2_grid_mask",  # from  clev2er.utils.masks.Mask
    # antarctic_icesheet_2km_grid_mask
    "masktype": "grid",  # mask is a polar stereo grid of Nkm resolution
    "basin_numbers": [2, 4],  # [n1,n2,..] if mask allows basin numbers
    # for bedmachine v2, 2=grounded ice, 3=floating, 4=vostok
    "show_polygon_mask": False,  # show mask polygon
    "polygon_mask_color": "red",  # color to draw mask polygon
    # --------------------------------------------
    # Plot parameters for this area
    # --------------------------------------------
    "axes": [  # define plot axis position
        -0.02,  # left
        0.1,  # bottom
        0.74,  # width (axes fraction)
        0.74,  # height (axes fraction)
    ],
    "draw_axis_frame": True,
    "background_color": None,  # background color of map
    "background_image": "natural_earth_cbh",  # background image. see clev2er.utils.backgrounds
    "background_image_alpha": 1.0,  # 0..1.0, default is 1.0, image transparency
    "background_image_resolution": None,  # None, 'low','medium', 'high'
    "hillshade_params": None,  # hill shade parameter dict or None
    "show_polygon_overlay_in_main_map": True,  # Overlay the area polygon outline in the main map
    "grid_polygon_overlay_mask": None,
    "apply_hillshade_to_vals": False,  # Apply a hillshade to plotted vals (True or False)
    "draw_coastlines": True,  # Draw coastlines
    "coastline_color": "grey",  # Colour to draw coastlines
    "use_antarctica_medium_coastline": True,  # True,False: Antarctic coastline including iceshelves
    "use_cartopy_coastline": None,  # None, 'low','medium', 'high' resolution
    "show_gridlines": True,  # True|False, display lat/lon grid lines
    # ------------------------------------------------------
    # Flag plot settings
    # ------------------------------------------------------
    "include_flag_legend": False,  # include or not the flag legend
    "flag_legend_xylocation": [
        None,
        None,
    ],  # x, y of flag legend lower right bbox
    "flag_legend_location": "upper right",  # position of flag legend bbox
    "include_flag_percents": True,  # include or not the flag percentage sub-plot
    "flag_perc_axis": [
        0.74,
        0.25,
        0.10,
    ],  # [left,bottom, width] of axis. Note height is auto set
    # ------------------------------------------------------
    # Default colormap for primary dataset (can be overridden in dataset dicts)
    # ------------------------------------------------------
    "cmap_name": "RdYlBu_r",  # colormap name to use for this dataset
    "cmap_over_color": "#A85754",  # or None
    "cmap_under_color": "#3E4371",  # or None
    "cmap_extend": "both",  # 'neither','min', 'max','both'
    # ------------------------------------------------------
    # Colour bar
    # ------------------------------------------------------
    "draw_colorbar": True,
    "colorbar_orientation": "horizontal",  # vertical, horizontal
    "vertical_colorbar_axes": [
        0.04,
        0.05,
        0.02,
        0.55,
    ],  # [ left, bottom, width, height (fractions of axes)]
    "horizontal_colorbar_axes": [
        0.08,
        0.05,
        0.55,
        0.02,
    ],  # [ left, bottom, width, height (fractions of axes)]
    # ------------------------------------------------------
    #       Lat/lon grid lines to show in main area
    #           - use empty lists to not include
    # ------------------------------------------------------
    "longitude_gridlines": range(0, 360 + 20, 20),  # deg E
    "latitude_gridlines": list(range(-82, -66 + 4, 4)) + [-88],  # deg N
    "gridline_color": "lightgrey",  # color to use for lat/lon grid lines
    "gridlabel_color": "darkgrey",  # color of grid labels
    "gridlabel_size": 8,  # size of grid labels
    "inner_gridlabel_color": "white",  # color of grid labels
    "inner_gridlabel_size": 8,  # size of grid labels
    "latitude_of_radial_labels": -58.3,  # latitude for radial grid line labels for circular plots
    "latline_label_axis_positions": [
        True,
        False,
        True,
        False,
    ],  # [left,right,top,bot] for rect plots
    "lonline_label_axis_positions": [
        False,
        True,
        False,
        True,
    ],  # [left,right,top,bot] for rect plots
    # ------------------------------------------------------
    #       Optional Mini-map (with box showing actual area)
    # ------------------------------------------------------
    "show_minimap": True,  # show the overview minmap
    "minimap_axes": [  # define minimap axis position
        0.64,  # left
        0.67,  # bottom
        0.29,  # width (axes fraction)
        0.29,  # height (axes fraction)
    ],
    "minimap_bounding_lat": None,  # None or bounding latitude if used for mini-map
    # uses 40N for northern hemisphere or 50N for southern.
    # Override with this parameter
    "minimap_circle": None,  # None or [lat,lon,circle_radius_m,color_str]
    "minimap_draw_gridlines": False,
    "minimap_val_scalefactor": 1.0,  # scale factor for plotting bad values on minimap
    "minimap_legend_pos": (1.38, 1.1),  # position of minimap legend (upper right) in minimap axis
    # ------------------------------------------------------
    #       Show a scale bar in km
    # ------------------------------------------------------
    "show_scalebar": True,
    "mapscale": [
        -178.0,  # longitude to position scale bar
        -65.0,  # latitide to position scale bar
        0.0,  # longitude of true scale (ie centre of area)
        -90.0,  # latitude of true scale (ie centre of area)
        1000,  # width of scale bar (km)
        "white",  # color of scale bar
        70,  # size of scale bar
    ],
    # --------------------------------------------------------
    # Histograms
    # --------------------------------------------------------
    "histogram_plotrange_axes": [
        0.735,  # left
        0.3,  # bottom
        0.08,  # width (axes fraction)
        0.35,  # height (axes fraction)
    ],  # axis location of plot range histogram for Polarplot.plot_points()
    "histogram_fullrange_axes": [
        0.89,  # left
        0.3,  # bottom
        0.08,  # width (axes fraction)
        0.35,  # height (axes fraction)
    ],  # axis location of plot range histogram for Polarplot.plot_points()
    # --------------------------------------------------------
    # Latitude vs Values plot
    # --------------------------------------------------------
    "latvals_axes": [
        0.77,  # left
        0.05,  # bottom
        0.17,  # width (axes fraction)
        0.2,  # height (axes fraction)
    ],  # axis location of latitude vs values scatter plot
}
