""" pytests for clev2er.utils.dhdt_data.dhdt"""

import numpy as np
from netCDF4 import Dataset  # pylint:disable=E0611

from clev2er.utils.dhdt_data.dhdt import Dhdt

# pylint: disable=too-many-locals


def test_grn_diff():
    """pytest to calc diff between slater and smith dh/dt solutions over grn"""
    thisdhdt = Dhdt("grn_is2_is1_smith")
    thisdhdt2 = Dhdt("grn_2010_2021")

    latmin, latmax, lonmin, lonmax = 50.0, 90.0, 0.0, 360.0
    width = 2400
    lats, lons = np.meshgrid(
        np.linspace(latmin, latmax, width), np.linspace(lonmin, lonmax, width)
    )
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


def test_smith_ais_dhdt():
    """pytest function to test Dhdt() class"""
    thisdhdt = Dhdt("ais_is2_is1_smith")
    print(f"binsize={thisdhdt.binsize}")

    latmin, latmax, lonmin, lonmax = -90, -60.0, 0.0, 360.0
    width = 1400
    lats, lons = np.meshgrid(
        np.linspace(latmin, latmax, width), np.linspace(lonmin, lonmax, width)
    )
    lats = lats.flatten()
    lons = lons.flatten()

    dhdt_vals = thisdhdt.interp_dhdt(lats, lons, xy_is_latlon=True)

    # Create a new NetCDF file
    ncfile = Dataset("/tmp/test2.nc", "w", format="NETCDF4")

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

    print("test file saved as /tmp/test2.nc")


def test_smith_dhdt():
    """pytest function to test Dhdt() class"""
    thisdhdt = Dhdt("grn_is2_is1_smith")

    latmin, latmax, lonmin, lonmax = 50.0, 90.0, 0.0, 360.0
    width = 2400
    lats, lons = np.meshgrid(
        np.linspace(latmin, latmax, width), np.linspace(lonmin, lonmax, width)
    )
    lats = lats.flatten()
    lons = lons.flatten()

    dhdt_vals = thisdhdt.interp_dhdt(lats, lons, xy_is_latlon=True)

    # Create a new NetCDF file
    ncfile = Dataset("/tmp/test2.nc", "w", format="NETCDF4")

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

    print("test file saved as /tmp/test2.nc")


def test_slater_grn_dhdt():
    """pytest function to test Dhdt() class"""
    thisdhdt = Dhdt("grn_2010_2021")
    print(f"binsize={thisdhdt.binsize}")

    config = {}
    config["dhdt_data_dir"] = {}
    config["dhdt_data_dir"]["grn_2010_2021"] = "/cpdata/RESOURCES/dhdt_data"

    thisdhdt = Dhdt("grn_2010_2021", config=config)

    lats = [70.29, 78.83, 79.54]
    lons = [-48.09, -40.79, -68.21]
    latmin, latmax, lonmin, lonmax = 50.0, 90.0, 0.0, 360.0
    width = 2400
    lats, lons = np.meshgrid(
        np.linspace(latmin, latmax, width), np.linspace(lonmin, lonmax, width)
    )
    lats = lats.flatten()
    lons = lons.flatten()

    dhdt_vals = thisdhdt.interp_dhdt(lats, lons, xy_is_latlon=True)

    # Create a new NetCDF file
    ncfile = Dataset("/tmp/test.nc", "w", format="NETCDF4")

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

    print("test file saved as /tmp/test.nc")
