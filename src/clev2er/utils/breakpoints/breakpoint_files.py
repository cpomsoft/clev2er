"""clev2er.utils.breakpoints.breakpoint_files.py

Functions to support writing of breakpoint files
"""

import logging
import os

import numpy as np
from netCDF4 import Dataset  # pylint: disable=E0611

# pylint: disable=too-many-arguments
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements
# pylint: disable=too-many-locals


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
            current_key = f"{parent_key}_{key}" if parent_key else key  # Include parent_key in the
            # variable name for nested levels
            if isinstance(value, list):
                value = np.array(value)
            if isinstance(value, dict):
                # If the value is a dictionary, create a group for nested variables
                subgroup = ncfile.createGroup(current_key)
                create_variables(subgroup, "", value, dim_sizes, dim_names, dims)
            elif isinstance(value, np.ndarray) and len(value.shape) == 1:
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
                var = ncfile.createVariable(current_key, str(value.dtype), dimensions=(dim,))

                var[:] = value

            elif isinstance(value, np.ndarray) and len(value.shape) == 2:
                if value.dtype == "bool":
                    # Convert boolean arrays to integers (0 for False, 1 for True)
                    value = value.astype(int)

                dim_size1 = value.shape[0]
                dim_size2 = value.shape[1]

                if dim_size1 not in dim_sizes:
                    dim_sizes.append(dim_size1)
                    dim_names.append(f"dim{len(dim_sizes)}")
                    dim1 = ncfile.createDimension(f"dim{len(dim_sizes)}", dim_size1)
                    dims.append(dim1)
                else:
                    dim1 = dims[dim_sizes.index(dim_size1)]

                if dim_size2 not in dim_sizes:
                    dim_sizes.append(dim_size2)
                    dim_names.append(f"dim{len(dim_sizes)}")
                    dim2 = ncfile.createDimension(f"dim{len(dim_sizes)}", dim_size2)
                    dims.append(dim2)
                else:
                    dim2 = dims[dim_sizes.index(dim_size2)]

                # Create a new dimension
                var = ncfile.createVariable(
                    current_key,
                    str(value.dtype),
                    dimensions=(
                        dim1,
                        dim2,
                    ),
                )
                var[:] = value

            elif isinstance(value, np.ndarray) and len(value.shape) == 3:
                if value.dtype == "bool":
                    # Convert boolean arrays to integers (0 for False, 1 for True)
                    value = value.astype(int)

                dim_size1 = value.shape[0]
                dim_size2 = value.shape[1]
                dim_size3 = value.shape[2]

                if dim_size1 not in dim_sizes:
                    dim_sizes.append(dim_size1)
                    dim_names.append(f"dim{len(dim_sizes)}")
                    dim1 = ncfile.createDimension(f"dim{len(dim_sizes)}", dim_size1)
                    dims.append(dim1)
                else:
                    dim1 = dims[dim_sizes.index(dim_size1)]

                if dim_size2 not in dim_sizes:
                    dim_sizes.append(dim_size2)
                    dim_names.append(f"dim{len(dim_sizes)}")
                    dim2 = ncfile.createDimension(f"dim{len(dim_sizes)}", dim_size2)
                    dims.append(dim2)
                else:
                    dim2 = dims[dim_sizes.index(dim_size2)]

                if dim_size3 not in dim_sizes:
                    dim_sizes.append(dim_size3)
                    dim_names.append(f"dim{len(dim_sizes)}")
                    dim3 = ncfile.createDimension(f"dim{len(dim_sizes)}", dim_size3)
                    dims.append(dim3)
                else:
                    dim3 = dims[dim_sizes.index(dim_size3)]

                # Create a new dimension
                var = ncfile.createVariable(
                    current_key, str(value.dtype), dimensions=(dim1, dim2, dim3)
                )
                var[:] = value

            elif isinstance(value, np.ndarray) and len(value.shape) > 2:
                ncfile.setncattr(
                    current_key,
                    (
                        f"{current_key} : data type {type(value)} "
                        f" of array dimensions {len(value.shape)} not supported"
                    ),
                )
            else:
                # For other data types, create dimensions and variables as usual
                if isinstance(value, bool):
                    ncfile.setncattr(current_key, np.array(value, "b"))

                elif isinstance(value, (int, float, np.integer, np.floating)):
                    # For scalar numerical values, create a dimension and a variable
                    # if not already existing

                    ncfile.setncattr(current_key, value)

                elif isinstance(value, str):
                    # For string values, store as an attribute
                    ncfile.setncattr(current_key, value)
                else:
                    raise ValueError(
                        f"Unsupported data type for variable '{current_key}': {type(value)}"
                    )

    with Dataset(file_path, "w") as ncfile:
        dim_sizes = []
        dim_names = []
        dims = []
        create_variables(ncfile, "", data_dict, dim_sizes, dim_names, dims)


def write_breakpoint_file(
    config: dict, shared_dict: dict, log: logging.Logger, breakpoint_alg_name: str
) -> str:
    """write a netcdf breakpoint file containing contents of
       shared dictionary

    Args:
        config (dict): chain config file
        shared_dict (dict): shared working dictionary
        log (logging.Logger): current logger instance to use
        breakpoint_alg_name (str): name of the algorithm after which the bp is set
    Returns:
        (str) : path of breakpoint file
    """

    # form breakpoint dir path

    if not config:  # temporary, as config fields not yet used to set path
        breakpoint_dir = "/tmp"
    else:
        if "breakpoint_files" in config:
            breakpoint_dir = config["breakpoint_files"]["default_dir"]

    if "l1b_file_name" in shared_dict:
        filename = os.path.splitext(os.path.basename(shared_dict["l1b_file_name"]))[0]
        filename = f"{breakpoint_dir}/{filename}_bkp_{breakpoint_alg_name}.nc"
    else:
        filename = f"{breakpoint_dir}/breakpoint_{breakpoint_alg_name}.nc"
    log.info("breakpoint file: %s", filename)
    create_netcdf_file(filename, shared_dict)
    return filename
