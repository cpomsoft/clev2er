"""
Cryo-TEMPO land ice elevation uncertainty functions

calc_uncertainty()  : maps input slope values -> elevation uncertainty, using a table of

uncertainty values per slope band

Author: Alan Muir , DTU (initial design, coding)
Date: 2021
Copyright: UCL/MSSL/CPOM. Not to be used outside CPOM/MSSL without permission of author

"""

import numpy as np
from scipy.interpolate import interp1d

# pylint: disable=R0801


def calc_uncertainty(
    slopes: np.ndarray,
    uncertainty_table: np.ndarray,
    min_slope: float,
    max_slope: float,
) -> np.ndarray:
    """
    Purpose:
        return the corresponding interpolated uncertainties for a list of input slope values
        from an uncertainty table, which contains the uncertainty values calculated for a
        range of slope bands

    Parameters:
        slopes: list of input slope values, type ndarray of float
        uncertainty_table: list of uncertainty values for each band of slope, the table corresponds
        to n slope bands between min_slope and max_slope, where n is
        (max_slope - min_slope) / len(uncertainty_table), type ndarray of float
        min_slope:  minimum slope value of uncertainty_table
        max_slope:  maximum slope value of uncertainty_table

    Returns:
        uncertainty: list of uncertainty values corresponding to each input slope value,
        type ndarray
    """
    table_size = len(uncertainty_table)
    band = (max_slope - min_slope) / (table_size)

    x = min_slope + np.arange(0, table_size + 1) * band
    y = uncertainty_table
    y = np.append(
        y, y[-1]
    )  # Add an extra point to make the interpolator happy, so that len(x) == len(y)
    interp_func = interp1d(x, y)

    uncertainty = np.full(len(slopes), np.nan)
    slope_ok = np.where((slopes >= min_slope) & (slopes <= max_slope))[0]
    if slope_ok.size > 0:
        uncertainty[slope_ok] = interp_func(slopes[slope_ok])
    # if slope exceeds max_slope use final value in uncertainty table
    slope_ok = np.where(slopes >= max_slope)[0]
    if slope_ok.size > 0:
        uncertainty[slope_ok] = uncertainty_table[-1]
    # if slope is < min_slope use initial value in uncertainty table
    slope_ok = np.where(slopes <= min_slope)[0]
    if slope_ok.size > 0:
        uncertainty[slope_ok] = uncertainty_table[0]
    return uncertainty


# #-------------------------------------------------------------------------------
# #  Module Unit tests
# #-------------------------------------------------------------------------------
# if __name__ == '__main__' :

#     min_slope=0.0 # minimum slope in degrees
#     max_slope=2.0 # maximum slope in degrees

#     # Define some input slope values, including values out of range of min_slope, max_slope
#     slopes = np.array([-1.,0.,0.1,1.0,2.0,3.0])

#     # Define an uncertainty table
#     number_of_slope_bands=20
#     # Create a dummy uncertainty table [1,...20]
#     uncertainty_table = list(np.arange(1., number_of_slope_bands+1))

#     uncertainties = calc_uncertainty(slopes, uncertainty_table, min_slope, max_slope)

#     for i,slope in enumerate(slopes):
#         print('slope: ', slope,' -> uncertainty : ',uncertainties[i])
