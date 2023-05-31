"""pytests for masks.py: Mask class
"""
import numpy as np
import pytest

from clev2er.utils.masks.masks import Mask


@pytest.mark.parametrize(
    "mask_name,indices_inside,lats,lons,grid_values",
    [
        (
            "greenland_area_xylimits_mask",
            [0],  # indices of points inside
            [75.0, 34],  # lats
            [-38, 16],  # lons
            None,  # grid values in mask to indicate inside,, xylimits have no values
        ),
        (
            "greenland_area_xylimits_mask",
            [],  # indices of points inside
            [72.0],  # lats
            [-10],  # lons
            None,  # grid values in mask to indicate inside, xylimits have no values
        ),
        (
            "greenland_bedmachine_v3_grid_mask",
            [0],  # indices of points inside
            [75.0, 34],  # lats
            [-38, 16],  # lons
            [1, 2],  # grid values in mask to indicate inside
        ),
        ("greenland_bedmachine_v3_grid_mask", [], [72.0], [-10], [1, 2]),
        (
            "antarctica_iceandland_dilated_10km_grid_mask",
            [0, 1],  # indices of points inside
            [-76.82, -70.65, -59.493],  # lats
            [55, -64.057, 98.364],  # lons
            [1],  # grid values in mask to indicate inside
        ),
        (
            "greenland_iceandland_dilated_10km_grid_mask",
            [0],  # indices of points inside
            [78.657, -70.65, -59.493],  # lats
            [-36.33, -64.057, 98.364],  # lons
            [1],  # grid values in mask to indicate inside
        ),
    ],
)
def test_mask_points_inside(  # too-many-arguments, pylint: disable=R0913
    mask_name, indices_inside, lats, lons, grid_values
):
    """test of Mask.points_inside()

    Args:
        mask_name (str): name of Mask
        indices_inside (list[int]): list of indices inside mask, or empty list []
        num_inside (int): number of points inside mask
        lats (_type_): _description_
        lons (_type_): _description_
        grid_values (_type_): _description_
    """
    thismask = Mask(mask_name)

    true_inside, _, _ = thismask.points_inside(lats, lons, basin_numbers=grid_values)

    expected_number_inside = len(indices_inside)

    # Check number of points inside mask is expected
    assert np.count_nonzero(true_inside) == expected_number_inside, (
        f"number of points inside mask should be {expected_number_inside},"
        f"for lats: {lats}, lons: {lons}"
    )

    if expected_number_inside > 0:
        for index_inside in indices_inside:
            assert true_inside[
                index_inside
            ], f"Index {index_inside} should be inside mask"


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
