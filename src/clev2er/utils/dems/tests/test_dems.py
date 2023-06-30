"""pytests for Dem class
"""
import logging

import numpy as np
import pytest

from clev2er.utils.dems.dems import Dem

log = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "dem_name,lats,lons,elevs",
    [
        (
            "arcticdem_1km",
            [79.3280254299693],
            [-34.42389],
            [1983.98],
        ),  # GIS location, elevations from CS2 CryoTEMPO Baseline-B
        ("rema_ant_1km", [-77], [106], [3516]),  # Vostok
        ("rema_ant_1km_v2", [-77], [106], [3516]),  # Vostok
    ],
)
def test_dems(dem_name, lats, lons, elevs):
    """load DEMs and test interpolated elevations to tolerance of 1m

    Args:
        dem_name (str): _description_
        lats (np.ndarray): latitude values
        lons (np.ndarray): longitude values
        elevs (np.ndarray: expected elevation values
    """
    thisdem = Dem(dem_name)

    if len(lats) > 0:
        dem_elevs = thisdem.interp_dem(lats, lons, xy_is_latlon=True)
        np.testing.assert_allclose(elevs, dem_elevs, atol=1.0)
