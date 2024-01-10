""" pytests for clev2er.utils.dhdt_data.dhdt"""

import numpy as np
import pytest
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.utils.dhdt_data.dhdt import Dhdt

# pylint: disable=too-many-locals


@pytest.mark.parametrize(
    "dhdt_name,limits,width,outfile",
    [
        (
            "ais_is2_is1_smith",
            (-90, -60.0, 0.0, 360.0),
            1400,
            "/tmp/dhdt_ais_smith.nc",
        ),
        (
            "grn_is2_is1_smith",
            (50.0, 90.0, 0.0, 360.0),
            2400,
            "/tmp/dhdt_gis_smith.nc",
        ),
        (
            "grn_2010_2021",
            (50.0, 90.0, 0.0, 360.0),
            2400,
            "/tmp/dhdt_gis_slater.nc",
        ),
    ],
)
def test_dhdt(dhdt_name, limits, width, outfile):
    """pytest function to test Dhdt() class"""
    thisdhdt = Dhdt(dhdt_name)

    latmin, latmax, lonmin, lonmax = limits
    lats, lons = np.meshgrid(np.linspace(latmin, latmax, width), np.linspace(lonmin, lonmax, width))
    lats = lats.flatten()
    lons = lons.flatten()

    dhdt_vals = thisdhdt.interp_dhdt(lats, lons, xy_is_latlon=True)

    # Create a new NetCDF file
    ncfile = Dataset(outfile, "w", format="NETCDF4")

    # Define dimensions
    num_points = len(lats)
    ncfile.createDimension("num_points", num_points)

    # Create variables
    lat_var = ncfile.createVariable("latitude", "f4", ("num_points",))
    lon_var = ncfile.createVariable("longitude", "f4", ("num_points",))
    val_var = ncfile.createVariable("dhdt_vals", "f4", ("num_points",))

    # Fill in the data
    lat_var[:] = lats
    lon_var[:] = lons
    val_var[:] = dhdt_vals

    # Add attributes
    lat_var.units = "degrees_north"
    lon_var.units = "degrees_east"
    val_var.units = "m/yr"

    # Close the NetCDF file
    ncfile.close()

    print(f"test file saved as {outfile}")


def test_grn_diff():
    """pytest to calc diff between slater and smith dh/dt solutions over grn"""
    thisdhdt = Dhdt("grn_is2_is1_smith")
    thisdhdt2 = Dhdt("grn_2010_2021")

    latmin, latmax, lonmin, lonmax = 50.0, 90.0, 0.0, 360.0
    width = 2400
    lats, lons = np.meshgrid(np.linspace(latmin, latmax, width), np.linspace(lonmin, lonmax, width))
    lats = lats.flatten()
    lons = lons.flatten()

    dhdt_vals = thisdhdt.interp_dhdt(lats, lons, xy_is_latlon=True)
    dhdt2_vals = thisdhdt2.interp_dhdt(lats, lons, xy_is_latlon=True)

    # Create a new NetCDF file
    outfile = "/tmp/dhdt_diffs.nc"
    ncfile = Dataset(outfile, "w", format="NETCDF4")

    # Define dimensions
    num_points = len(lats)
    ncfile.createDimension("num_points", num_points)

    # Create variables
    lat_var = ncfile.createVariable("latitude", "f4", ("num_points",))
    lon_var = ncfile.createVariable("longitude", "f4", ("num_points",))
    val_var = ncfile.createVariable("dhdt_vals", "f4", ("num_points",))

    # Fill in the data
    lat_var[:] = lats
    lon_var[:] = lons
    val_var[:] = dhdt2_vals - dhdt_vals

    # Add attributes
    lat_var.units = "degrees_north"
    lon_var.units = "degrees_east"
    val_var.units = "m/yr"

    # Close the NetCDF file
    ncfile.close()

    print(f"test file saved as {outfile}")
