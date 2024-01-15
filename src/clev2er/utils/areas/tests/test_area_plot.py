"""pytest of clev2er.utils.areas.area_plot
"""
import os

import numpy as np

from clev2er.utils.areas.area_plot import Annotation, Polarplot


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

    Polarplot("antarctica_basic").plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_latsnan.png"
        ),
        config=config,
    )

    # Test with some None values in the latitude array
    dataset["lats"][0:20] = None

    Polarplot("antarctica").plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_latsnone.png"
        ),
        config=config,
    )

    # Test with some out of range values in the latitude array
    dataset["lats"][0:20] = 100.0

    Polarplot("antarctica_basic").plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_lats_outofrange.png"
        ),
        config=config,
    )

    # Test with all lats set to Nan
    dataset["lats"][:] = np.nan

    Polarplot("antarctica").plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/test_plots/"
            "test_lats_allnan.png"
        ),
        config=config,
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

    Polarplot("antarctica_basic").plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_valsnan.png"
        ),
        config=config,
    )

    # test with some FillValues set
    fill_value = 99999
    dataset["vals"][10:20] = fill_value
    dataset["fill_value"] = fill_value

    Polarplot("antarctica_basic").plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_fillvalue.png"
        ),
        config=config,
    )

    # test with all values set to Nan
    dataset["vals"][:] = np.nan

    Polarplot("antarctica_basic").plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_allvalsnan.png"
        ),
        config=config,
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

    Polarplot("antarctica_basic").plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_with_annot.png"
        ),
        config=config,
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

    Polarplot("antarctica_basic").plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_with_annot2.png"
        ),
        config=config,
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

    Polarplot("antarctica_basic").plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_allvalsgood.png"
        ),
        config=config,
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

    Polarplot("antarctica_basic").plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_flags.png"
        ),
        config=config,
    )


def test_area_plot_grn():
    """pytest to test plotting over the 'greenland' area"""
    config = {
        "background_image": [
            "ibcao_bathymetry",
            "hillshade",
        ],
        "background_image_alpha": [0.4, 0.1],
        "background_color": "white",
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

    Polarplot("greenland").plot_points(
        dataset,
        output_file=(
            f"{os.environ['CLEV2ER_BASE_DIR']}/src/clev2er/utils/areas/tests/"
            "test_plots/test_greenland.png"
        ),
        config=config,
    )
