""" ----------------------------------------------------------------------------------
  pytest unit tests for : cpom/altimetry/level2/cs2/retrackers/cs2_tcog_retracker:
  retrack_tcog_waveforms_cs2()
"""
import os

import numpy as np
import pytest

from clev2er.utils.cs2.retrackers.cs2_tcog_retracker import (
    retrack_tcog_waveforms_cs2,
)

# pylint: disable=too-many-arguments
# pylint: disable=R0801

pytestmark = [pytest.mark.lrm, pytest.mark.tcog]


@pytest.fixture
def lrm_file():
    """fixture

    Returns:
        str: path of LRM L1b file
    """
    return (
        os.environ["CPDATA_DIR"]
        + "/SATS/RA/CRY/L1B/LRM/2019/05/CS_OFFL_SIR_LRM_1B_20190504T122726_20190504T123244_D001.nc"
    )


@pytest.fixture
def sin_file():
    """fixture

    Returns:
        str: path of SIN L1b file
    """
    return (
        os.environ["CPDATA_DIR"] + "/SATS/RA/CRY/L1B/SARIN/SARIN_ESA_BaselineD/201905/"
        "CS_OFFL_SIR_SIN_1B_20190504T122546_20190504T122726_D001.nc"
    )


# ------------------------------------------------------------------------------------


# Test the TCOG retracker runs without error with a sample SIN file on all waveforms
def test_retrack_tcog_waveforms_cs2_sin(
    sin_file,
):  # pylint: disable=redefined-outer-name
    """test of retrack_tcog_waveforms_cs2_sin

    Args:
        sin_file (str): L1b SIN file path
    """
    # Run the Retracker
    (
        _,  # dr_bin_tcog,
        _,  # dr_meters_tcog,
        _,  # leading_edge_start,
        _,  # leading_edge_stop,
        _,  # pwr_at_rtrk_point,
        n_retracker_failures,
        _,  # retrack_flags,
    ) = retrack_tcog_waveforms_cs2(
        sin_file  # ,plot_flag=True \
        # ,debug_flag=True
    )

    assert n_retracker_failures == 0


# -----------------------------------------------------------------------------------
# LRM Retracker Tests
# -----------------------------------------------------------------------------------


# Test the TCOG retracker runs without error with a sample LRM file on all waveforms
def test_retrack_tcog_waveforms_cs2(lrm_file):  # pylint: disable=redefined-outer-name
    """test of retrack_tcog_waveforms_cs2

    Args:
        lrm_file (str): L1b LRM file path
    """
    # Run the Retrackers
    (
        dr_bin_tcog,
        _,  # dr_meters_tcog,
        _,  # leading_edge_start,
        _,  # leading_edge_stop,
        pwr_at_rtrk_point,
        n_retracker_failures,
        _,  # retrack_flags,
    ) = retrack_tcog_waveforms_cs2(lrm_file)

    assert n_retracker_failures == 5

    # Test that exactly 5 of the returned retracking points are set to Nan
    assert len(np.where(np.isnan(dr_bin_tcog))[0]) == 5
    # Test that exactly 5 of the returned pwr_at_rtrk_point_tcog points are set to Nan
    assert len(np.where(np.isnan(pwr_at_rtrk_point))[0]) == 5


# Test retracking of LRM waveforms which should fail: index [713,714,715,717] where noise floor
# is exceeded
#   - test returned n_retracker_failures should be 1
#   -  retrack_flags[measurement_index][0] should be 1 to indicate noise floor exceeded


# Test is repeated for each index
@pytest.mark.parametrize(
    "measurement_index, expected_success, expected_retracking_bin, expected_leading_edge_start,"
    " expected_leading_edge_end",
    [
        (0, 1, 38.46, 37.04, 60.99),
        (1, 1, 37.507, 35.99, 42.01),
        (713, 0, np.nan, np.nan, np.nan),
        (714, 0, np.nan, np.nan, np.nan),
        (715, 0, np.nan, np.nan, np.nan),
        (717, 0, np.nan, np.nan, np.nan),
    ],
)
def test_retrack_tcog_waveforms_cs2_at_index(
    lrm_file,  # pylint: disable=redefined-outer-name
    measurement_index,
    expected_success,
    expected_retracking_bin,
    expected_leading_edge_start,
    expected_leading_edge_end,
):
    """test of retrack_tcog_waveforms_cs2 at specific indices

    Args:
        lrm_file (str): path of LRM 1b file
        measurement_index (int): _description_
        expected_success (int): _description_
        expected_retracking_bin (float): _description_
        expected_leading_edge_start (float): _description_
        expected_leading_edge_end (float): _description_
    """
    ref_bin_ind_lrm = 64

    # Run the Retrackers
    (
        dr_bin_tcog,
        _,  # dr_meters_tcog,
        leading_edge_start,
        leading_edge_stop,
        _,  # pwr_at_rtrk_point_tcog,
        n_retracker_failures,
        retrack_flags,
    ) = retrack_tcog_waveforms_cs2(
        lrm_file,
        measurement_index=measurement_index,
        retrack_threshold_lrm=0.2
        # ,plot_flag=True,
        # ,debug_flag=True
    )

    if expected_success:
        # Test that retracking was successful
        assert n_retracker_failures == 0
        # Check that the retracking point is at the expected bin index
        assert np.isclose(
            dr_bin_tcog[measurement_index] + ref_bin_ind_lrm,
            expected_retracking_bin,
            0.01,
        )
        # Check the leading edge start is at expected bin, to 2 decimal places
        assert np.isclose(
            leading_edge_start[measurement_index][0],
            expected_leading_edge_start,
            atol=0.01,
        )
        # Check the leading edge stop is at expected bin, to 2 decimal places
        assert np.isclose(
            leading_edge_stop[measurement_index][0],
            expected_leading_edge_end,
            atol=0.01,
        )

        #
    else:
        # Test that retracking failed
        assert n_retracker_failures == 1
        # Test that retracking failed due to noise threshold being exceeded
        assert retrack_flags[measurement_index][0] == 1
        # Retracking bin should be Nan
        assert np.isnan(dr_bin_tcog[measurement_index])
        # Leadinge Edge start bin should be Nan
        assert np.isnan(leading_edge_start[measurement_index][0])
