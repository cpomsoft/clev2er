"""pytest of clev2er.utils.areas.area_plot
"""
import os

import numpy as np
import pytest

from clev2er.utils.areas.area_plot import Annotation, Polarplot
from clev2er.utils.areas.areas import Area

# pylint: disable=R0801


@pytest.mark.parametrize(
    "area",
    [
        # ("antarctica"),
        # ("antarctica_is"),
        # ("antarctica_fi"),
        # ("antarctica_hs"),
        # ("antarctica_hs_is"),
        # ("antarctica_hs_fi"),
        # ("greenland"),
        # ("greenland_hs"),
        # ("greenland_hs_fi"),
        # ("greenland_hs_is"),
        # ("greenland_is"),
        ("greenland_fi"),
        # ("arctic"),
        # ("arctic_cpy"),  # cartopy background
        # arctic ocean?
    ],
)
def test_area_plot_by_name(area):
    """_summary_

    Args:
        area (str): area name
        southern_hemisphere (bool): True is area is in southern hemisphere
    """

    thisarea = Area(area)

    if thisarea.hemisphere == "south":
        # Latitude range from -90 to -60 and longitude range from -180 to 180
        latitudes = np.linspace(-90, -60, 30)  # 100 points from -90 to -60
        longitudes = np.linspace(0, 360, 30)  # 100 points from -180 to 180

        # Create a grid of latitude and longitude values
        lats, lons = np.meshgrid(latitudes, longitudes)

        # Create a grid of values for these coordinates
        # For simplicity, let's just use a function of latitudes and longitudes
        vals = np.full_like(lats, 1)
        vals = lats * lons
    else:
        # Latitude range from -90 to -60 and longitude range from -180 to 180
        latitudes = np.linspace(40, 90, 100)  # 100 points from -90 to -60
        longitudes = np.linspace(0, 360, 100)  # 100 points from -180 to 180

        # Create a grid of latitude and longitude values
        lats, lons = np.meshgrid(latitudes, longitudes)

        # Create a grid of values for these coordinates
        # For simplicity, let's just use a function of latitudes and longitudes
        vals = np.full_like(lats, 1)
        vals = lats * lons

    # Creating the dataset
    dataset = {
        "name": "mydata_grid",
        "units": "m",
        "lats": lats,
        "lons": lons,
        "vals": vals,
        # "flag_colors": ["b"],
        # "flag_names": [
        #     "1",
        # ],
        # "flag_values": [
        #     1,
        # ],
    }

    Polarplot(area).plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            f"test_plots/test_{area}.png"
        ),
    )
    Polarplot(area).plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            f"test_plots/test_{area}_simple.png"
        ),
        map_only=True,
    )


def test_area_plot_bad_latlon_data():
    """test of clev2er.utils.areas.area_plot with bad lat/lon data
    latitude values set to Nan, None
    """
    config = {}
    dataset = {
        "name": "mydata_1",
        "units": "m",
        "lats": np.linspace(-80, -70, 100),
        "lons": np.linspace(0, 2, 100),
        "vals": np.linspace(0, 100, 100),
    }

    # Test with some Nan values in the latitude array
    dataset["lats"][0:20] = np.nan

    Polarplot("antarctica_basic", config).plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_latsnan.png"
        ),
    )

    # Test with some None values in the latitude array
    dataset["lats"][0:20] = None

    Polarplot("antarctica", config).plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_latsnone.png"
        ),
    )

    # Test with some out of range values in the latitude array
    dataset["lats"][0:20] = 100.0

    Polarplot("antarctica_basic", config).plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_lats_outofrange.png"
        ),
    )

    # Test with all lats set to Nan
    dataset["lats"][:] = np.nan

    Polarplot("antarctica", config).plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/test_plots/"
            "test_lats_allnan.png"
        ),
    )


def test_area_plot_bad_vals():
    """test of clev2er.utils.areas.area_plot with bad lat/lon data"""

    config = {}
    dataset = {
        "name": "mydata_1",
        "units": "m",
        "lats": np.linspace(-80, -75, 100),
        "lons": np.linspace(0, 2, 100),
        "vals": np.linspace(0, 100, 100),
    }

    # test with some values set to Nan
    dataset["vals"][0:20] = np.nan

    Polarplot("antarctica_basic", config).plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_valsnan.png"
        ),
    )

    # test with some FillValues set
    fill_value = 99999
    dataset["vals"][10:20] = fill_value
    dataset["fill_value"] = fill_value

    Polarplot("antarctica_basic", config).plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_fillvalue.png"
        ),
    )

    # test with all values set to Nan
    dataset["vals"][:] = np.nan

    Polarplot("antarctica_basic", config).plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_allvalsnan.png"
        ),
    )


def test_area_plot_annotation():
    """pytests for clev2er.utils.areas.area_plot"""

    config = {}

    dataset = {
        "name": "mydata_1",
        "units": "m",
        "lats": np.linspace(-85, -75, 10),
        "lons": np.linspace(0, 2, 10),
        "vals": np.linspace(0, 100, 10),
    }

    # Test with Annotation

    annotation_list = []

    annot = Annotation(0.02, 0.86, "Area: ", fontsize=14)
    annotation_list.append(annot)

    Polarplot("antarctica_basic", config).plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_with_annot.png"
        ),
        annotation_list=annotation_list,
    )

    annot = Annotation(
        0.32,
        0.86,
        "Area: ",
        fontsize=14,
        bbox={
            "boxstyle": "round",
            "facecolor": "aliceblue",
            "alpha": 1.0,
            "edgecolor": "lightgrey",
        },
    )
    annotation_list.append(annot)

    Polarplot("antarctica_basic", config).plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_with_annot2.png"
        ),
        annotation_list=annotation_list,
    )


def test_area_plot_good():
    """pytests for clev2er.utils.areas.area_plot"""

    config = {
        "background_image": [
            "ibcso_bathymetry",
            "hillshade",
        ],
        "background_image_alpha": [0.4, 0.1],
        "background_color": "white",
    }

    dataset = {
        "name": "mydata_1",
        "units": "m",
        "lats": np.linspace(-85, -75, 10),
        "lons": np.linspace(0, 2, 10),
        "vals": np.linspace(100000, 200000, 10),
    }

    Polarplot("antarctica_basic", config).plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_allvalsgood.png"
        ),
    )


def test_area_plot_flags():
    """pytests for clev2er.utils.areas.area_plot"""

    config = {}

    dataset = {
        "name": "mydata_1",
        "units": "m",
        "lats": np.linspace(-85, -75, 13),
        "lons": np.linspace(0, 2, 13),
        "vals": [0, 0, 0, 1, 1, 1, 2, 1, 2, 0, 4, 4, 4],
        "flag_names": ["lrm", "sin", "sar"],
        "flag_colors": ["red", "blue", "green"],
        "flag_values": [0, 1, 2],
    }

    Polarplot("antarctica_basic", config).plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_flags.png"
        ),
    )


def test_area_plot_grn():
    """pytest to test plotting over the 'greenland' area"""
    config = {
        "background_image": [
            "ibcao_bathymetry",
            "hillshade",
        ],
        "background_image_alpha": [0.14, 0.18],
        "background_color": "white",
        "use_cartopy_coastline": "medium",
    }

    dataset = {
        "name": "mydata_1",
        "units": "m",
        "lats": np.linspace(60, 85, 100),
        "lons": np.linspace(-42, -40, 100),
        "vals": np.linspace(10000, 20000, 100),
        "fill_value": 99999,
    }

    dataset["vals"][0:50] = np.nan
    dataset["vals"][51:70] = 99999

    Polarplot("greenland", config).plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_greenland.png"
        ),
    )


def test_area_plot_ais():
    """pytest to test plotting over the 'antarctica' area"""
    config = {
        "background_image": [
            "ibcso_bathymetry",
            "hillshade",
        ],
        "background_image_alpha": [0.14, 0.18],
        "background_color": "white",
        "use_cartopy_coastline": "medium",
        "mapscale": [
            -178.0,  # longitude to position scale bar
            -65.0,  # latitide to position scale bar
            0.0,  # longitude of true scale (ie centre of area)
            -90.0,  # latitude of true scale (ie centre of area)
            1000,  # width of scale bar (km)
            "black",  # color of scale bar
            70,  # size of scale bar
        ],
        "inner_gridlabel_color": "black",
        "gridlabel_color": "black",
    }

    dataset = {
        "name": "mydata_1",
        "units": "m",
        "lats": np.linspace(-85, -75, 100),
        "lons": np.linspace(0, 2, 100),
        "vals": np.linspace(10000, 20000, 100),
        "fill_value": 99999,
    }

    dataset["vals"][0:50] = np.nan
    dataset["vals"][51:70] = 99999

    Polarplot("antarctica", config).plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_antarctica.png"
        ),
    )


def test_map_only_ais():
    """pytest to test plotting over the 'antarctica' area"""
    config = {
        "background_image": [
            "basic_land",
        ],
    }

    dataset = {
        "name": "mydata_1",
        "units": "m",
        "lats": np.linspace(-85, -75, 100),
        "lons": np.linspace(0, 2, 100),
        "vals": np.linspace(10000, 20000, 100),
        "fill_value": 99999,
    }

    dataset["vals"][0:50] = np.nan
    dataset["vals"][51:70] = 99999

    Polarplot("antarctica", config).plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_map_only_ais.png"
        ),
        map_only=True,
    )


def test_map_only_gis():
    """pytest to test plotting over the 'greenland' area"""
    config = {
        "background_image": [
            "basic_land",
        ],
    }
    config = {
        "background_image": [
            "ibcao_bathymetry",
            "hillshade",
        ],
        "background_image_alpha": [0.14, 0.18],
        "background_color": "white",
        "use_cartopy_coastline": "medium",
    }

    dataset = {
        "name": "mydata_1",
        "units": "m",
        "lats": np.linspace(60, 82, 100),
        "lons": np.linspace(320, 325, 100),
        "vals": np.linspace(10000, 20000, 100),
        "fill_value": 99999,
    }

    dataset["vals"][0:50] = np.nan
    dataset["vals"][51:70] = 99999

    Polarplot("greenland", config).plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_map_only_gis.png"
        ),
        map_only=False,
    )
