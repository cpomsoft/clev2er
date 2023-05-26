"""pytests for masks.py: Mask class
"""
import numpy as np
import pytest

from clev2er.utils.masks.masks import Mask


@pytest.mark.parametrize(
    "mask_name,index_inside,num_inside,lats,lons,grid_values",
    [
        (
            "greenland_area_xylimits_mask",
            0,  # index of point inside
            1,  # number inside
            [75.0, 34],  # lats
            [-38, 16],  # lons
            None,  # grid values in mask to indicate inside,, xylimits have no values
        ),
        (
            "greenland_area_xylimits_mask",
            None,  # index of point inside
            0,  # number inside
            [72.0],  # lats
            [-10],  # lons
            None,  # grid values in mask to indicate inside, xylimits have no values
        ),
        (
            "greenland_bedmachine_v3_grid_mask",
            0,  # index of point inside
            1,  # number inside
            [75.0, 34],  # lats
            [-38, 16],  # lons
            [1, 2],  # grid values in mask to indicate inside
        ),
        ("greenland_bedmachine_v3_grid_mask", None, 0, [72.0], [-10], [1, 2]),
    ],
)
def test_mask_points_inside(  # too-many-arguments, pylint: disable=R0913
    mask_name, index_inside, num_inside, lats, lons, grid_values
):
    """test of Mask.points_inside()

    Args:
        mask_name (str): _description_
        index_inside (_type_): _description_
        num_inside (_type_): _description_
        lats (_type_): _description_
        lons (_type_): _description_
        grid_values (_type_): _description_
    """
    thismask = Mask(mask_name)

    true_inside, _, _ = thismask.points_inside(lats, lons, basin_numbers=grid_values)

    # Check number of points inside mask is expected
    assert (
        np.count_nonzero(true_inside) == num_inside
    ), f"number of points inside mask should be {num_inside}, lats: {lats}, lons: {lons}"

    if num_inside > 0:
        # Check index inside is expected
        assert np.where(true_inside)[0][0] == index_inside


@pytest.mark.parametrize(
    "mask_name,lats,lons, expected_surface_type",
    [
        (
            "greenland_bedmachine_v3_grid_mask",
            [75.0, 34, 74],  # lats
            [-38, 16, -58],  # lons
            [
                2,
                np.NaN,
                0,
            ],  # expected surface type, grounded ice (2), out of mask (Nan), ocean(0)
        ),
    ],
)
def test_mask_grid_mask_values(mask_name, lats, lons, expected_surface_type) -> None:
    """test of Mask.grid_mask_values()

    Args:
        mask_name (str): mask name
        lats (np.ndarray): array of latitude N values in degs
        lons (np.ndarray): array of longitude E values in degs
        expected_surface_type (list[int or nan]): list of expected surface type values
    Returns:
        None
    """
    thismask = Mask(mask_name)

    mask_values = thismask.grid_mask_values(lats, lons)

    assert len(mask_values) == len(
        lats
    ), "length of returned mask_values should equal number of lat values"

    for index, expected in enumerate(expected_surface_type):
        if np.isnan(expected):
            assert np.isnan(
                mask_values[index]
            ), f"Surface type at {lats[index]},{lons[index]} should be {expected}"
        else:
            assert (
                expected == mask_values[index]
            ), f"Surface type at {lats[index]},{lons[index]} should be {expected}"


def test_mask_loading():
    """test loading mask file using non-default path"""
    try:
        _ = Mask("greenland_bedmachine_v3_grid_mask", mask_path="/tmp/none")
    except FileNotFoundError as exc:
        assert True, f"{exc} raised"
    else:
        assert False, "mask_path is invalid so should fail"
