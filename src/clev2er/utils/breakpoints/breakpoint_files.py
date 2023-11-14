"""clev2er.utils.breakpoints.breakpoint_files.py

Functions to support writing of breakpoint files
"""

import numpy as np
from netCDF4 import Dataset  # pylint: disable=E0611

# pylint: disable=too-many-arguments
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements


def create_netcdf_file(file_path, data_dict):
    """Create a NetCDF4 file from contents of a dictionary

    Args:
        file_path (str): _description_
        data_dict (dict): dictionary containing 1 or more levels
    Returns:
        None
    """

    def create_variables(ncfile, parent_key, data, dim_sizes, dim_names, dims):
        """Create NetCDF variables

        Args:
            ncfile (Dataset): NetCDF4 Dataset instance
            parent_key (_type_): _description_
            data (_type_): _description_
            dim_sizes (list): _description_
            dim_names (list): _description_
            dims (list): _description_

        Raises:
            ValueError: _description_
        """
        for key, value in data.items():
            current_key = (
                f"{parent_key}_{key}" if parent_key else key
            )  # Include parent_key in the
            # variable name for nested levels
            if isinstance(value, dict):
                # If the value is a dictionary, create a group for nested variables
                subgroup = ncfile.createGroup(current_key)
                create_variables(subgroup, "", value, dim_sizes, dim_names, dims)
            elif isinstance(value, np.ndarray):
                if value.dtype == "bool":
                    # Convert boolean arrays to integers (0 for False, 1 for True)
                    value = value.astype(int)
                dim_size = len(value)
                if dim_size not in dim_sizes:
                    dim_sizes.append(dim_size)
                    dim_names.append(f"dim{len(dim_sizes)}")
                    dim = ncfile.createDimension(f"dim{len(dim_sizes)}", dim_size)
                    dims.append(dim)
                else:
                    dim = dims[dim_sizes.index(dim_size)]

                # Create a new dimension
                var = ncfile.createVariable(
                    current_key, str(value.dtype), dimensions=(dim,)
                )
                var[:] = value
            elif isinstance(value, list):
                # Convert lists to NumPy arrays before creating variables
                value = np.array(value)
                if value.dtype == "bool":
                    # Convert boolean arrays to integers (0 for False, 1 for True)
                    value = value.astype(int)
                dim_size = len(value)
                if dim_size not in dim_sizes:
                    dim_sizes.append(dim_size)
                    dim_names.append(f"dim{len(dim_sizes)}")
                    dim = ncfile.createDimension(f"dim{len(dim_sizes)}", dim_size)
                    dims.append(dim)
                else:
                    dim = dims[dim_sizes.index(dim_size)]

                var = ncfile.createVariable(
                    current_key, str(value.dtype), dimensions=(dim,)
                )
                var[:] = value
            else:
                # For other data types, create dimensions and variables as usual
                if isinstance(value, bool):
                    # For a single boolean value, create a scalar variable with a dimension of
                    # size 1
                    dim = ncfile.createDimension(current_key, 1)
                    var = ncfile.createVariable(current_key, "i1", dimensions=(dim,))
                    var[0] = int(value)
                elif isinstance(value, (int, float, np.integer, np.floating)):
                    # For scalar numerical values, create a dimension and a variable
                    # if not already existing

                    # Create a new dimension
                    dim = ncfile.createDimension(current_key, 1)
                    dtype = str(type(value).__name__)
                    var = ncfile.createVariable(current_key, dtype, dimensions=(dim,))
                    var[0] = value

                elif isinstance(value, str):
                    # For string values, create a dimension and a variable if not already existing

                    # Create a new dimension
                    dim = ncfile.createDimension(current_key, len(value))

                    var = ncfile.createVariable(current_key, "S1", dimensions=(dim,))
                    var[:] = np.array(list(value), dtype="S1")
                else:
                    raise ValueError(
                        f"Unsupported data type for variable '{current_key}': {type(value)}"
                    )

    with Dataset(file_path, "w") as ncfile:
        dim_sizes = []
        dim_names = []
        dims = []
        create_variables(ncfile, "", data_dict, dim_sizes, dim_names, dims)


def write_breakpoint_file(config: dict, shared_dict: dict):
    """write a netcdf breakpoint file containing contents of
       shared dictionary

    Args:
        config (dict): chain config file
        shared_dict (dict): shared working dictionary
    """

    # form breakpoint file name

    if not config:  # temporary, as config fields not yet used to set path
        filename = "/tmp/breakpoint.nc"

    create_netcdf_file(filename, shared_dict)
