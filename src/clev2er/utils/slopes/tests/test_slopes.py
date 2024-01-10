"""
test of clev2er.utils.slopes.slopes
"""
import numpy as np

from clev2er.utils.slopes.slopes import Slopes, all_slope_scenarios


def test_slopes():
    """test loading all slope scenarios"""
    # Try loading all slope scenarios
    for scenario in all_slope_scenarios:
        _ = Slopes(scenario)


def test_slopes_ant():
    """test Antarctic slop scenarios"""
    this_slope = Slopes("cpom_ant_2018_1km_slopes")

    # Test the slope for locations in Lake Vostok: -77.5, 106

    lats = np.array([-77.5])
    lons = np.array([106])

    slopes = this_slope.interp_slope_from_lat_lon(lats, lons)

    # Test values returned are not nan
    assert np.count_nonzero(~np.isnan(slopes)) == len(lats), "Nan values returned"

    assert (slopes > 0.05).sum() == 0, " Should not have slopes > 0.05 at this Vostok location"
    assert (slopes < 0.0).sum() == 0, " Should not have slopes < 0"


def test_slopes_grn():
    """test Greenland slope scenarios"""
    this_slope = Slopes("awi_grn_2013_1km_slopes")

    # Test the slope for locations in Greenland: -77.5, 106

    lats = np.array([76.41])
    lons = np.array([-39.59])

    slopes = this_slope.interp_slope_from_lat_lon(lats, lons)

    # Test values returned are not nan
    assert np.count_nonzero(~np.isnan(slopes)) == len(lats), "Nan values returned"

    assert (slopes > 0.2).sum() == 0, " Should not have slopes > 0.2 at this Greenland location"
    assert (slopes < 0.0).sum() == 0, " Should not have slopes < 0"
