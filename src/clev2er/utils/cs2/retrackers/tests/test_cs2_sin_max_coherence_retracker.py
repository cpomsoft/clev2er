"""
 pytest unit tests for : cpom/altimetry/level2/cs2/retrackers/cs2_sin_max_coherence_retracker:
 retrack_cs2_sin_max_coherence_retracker()
"""
import os

import numpy as np
import pytest

from clev2er.utils.cs2.retrackers.cs2_sin_max_coherence_retracker import (
    retrack_cs2_sin_max_coherence,
)

# pylint: disable=R0801
# pylint: disable=too-many-arguments

# Set Markers which apply to whole file
pytestmark = [pytest.mark.sin, pytest.mark.mc]


# Set common inputs used in tests
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


# ---------------------------------------------------------------------------------------------
# SARin Retracker Test
#   - tests that the function runs with a sample SIN file
#   - tests that the number of retracker failures returned == 0 as expected fot this SIN file
# ---------------------------------------------------------------------------------------------

# Test the MC retracker runs without error with a sample SIN file on all waveforms


def test_retrack_cs2_sin_max_coherence(sin_file):  # pylint: disable=W0621
    """test of retrack_cs2_sin_max_coherence

    Args:
        sin_file (str): path
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
    ) = retrack_cs2_sin_max_coherence(
        sin_file  # ,plot_flag=True \
        # ,debug_flag=True
    )

    assert n_retracker_failures == 0


# Test the MC retracker runs without error with a sample LRM file on all waveforms
#   - expected to fail as not a SIN file
@pytest.mark.xfail()
def test_retrack_cs2_sin_max_coherence_with_lrm(lrm_file):  # pylint: disable=W0621
    """_summary_

    Args:
        lrm_file (str): path
    """
    # Run the Retracker
    (
        _,  # dr_bin_tcog,
        _,  # dr_meters_tcog,
        _,  # leading_edge_start,
        _,  # leading_edge_stop,
        _,  # pwr_at_rtrk_point,
        _,  # n_retracker_failures,
        _,  # retrack_flags,
    ) = retrack_cs2_sin_max_coherence(
        lrm_file  # ,plot_flag=True \
        # ,debug_flag=True
    )


# Test retracking of LRM waveforms which should fail: index [713,714,715,717] where noise floor is
#  exceeded
#   - test returned n_retracker_failures should be 1
#   -  retrack_flags[measurement_index][0] should be 1 to indicate noise floor exceeded


# Test is repeated for each index
@pytest.mark.parametrize(
    "measurement_index, expected_success, expected_retracking_bin, expected_leading_edge_start,"
    " expected_leading_edge_end",
    [(0, 1, 204.0, 199.42, 207.99)],
)
def test_retrack_cs2_sin_max_coherence_at_index(
    sin_file,  # pylint: disable=W0621
    measurement_index,
    expected_success,
    expected_retracking_bin,
    expected_leading_edge_start,
    expected_leading_edge_end,
):
    """test of retrack_cs2_sin_max_coherence at index

    Args:
        sin_file (str): path
        measurement_index (int): _description_
        expected_success (int): _description_
        expected_retracking_bin (float): _description_
        expected_leading_edge_start (float): _description_
        expected_leading_edge_end (float): _description_
    """
    ref_bin_ind_sin = 512

    # Run the Retrackers
    (
        dr_bin_mc,
        _,  # dr_meters_mc,
        leading_edge_start,
        leading_edge_stop,
        _,  # pwr_at_rtrk_point,
        n_retracker_failures,
        retrack_flags,
    ) = retrack_cs2_sin_max_coherence(
        sin_file, measurement_index=measurement_index, plot_flag=False
    )

    print(
        "dr_bin_mc[measurement_index]+ref_bin_ind_sin= ",
        dr_bin_mc[measurement_index] + ref_bin_ind_sin,
    )
    print(
        "leading_edge_start[measurement_index][0]= ",
        leading_edge_start[measurement_index][0],
    )
    print(
        "leading_edge_stop[measurement_index][0]= ",
        leading_edge_stop[measurement_index][0],
    )

    if expected_success:
        # Test that retracking was successful
        assert n_retracker_failures == 0
        # Check that the retracking point is at the expected bin index
        assert np.isclose(
            dr_bin_mc[measurement_index] + ref_bin_ind_sin,
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

    else:
        # Test that retracking failed
        assert n_retracker_failures == 1
        # Test that retracking failed due to noise threshold being exceeded
        assert retrack_flags[measurement_index][0] == 1
        # Retracking bin should be Nan
        assert np.isnan(dr_bin_mc[measurement_index])
        # Leadinge Edge start bin should be Nan
        assert np.isnan(leading_edge_start[measurement_index][0])
