#!/bin/bash

# ----------------------------------------------------------------------------- #
#
# Example 1: Using send_to_zarr() to create a zarr store from a single file.
#
# Description: Example script to send a single file to the object store using
# send_to_zarr() function.
#
# Created by: Ollie Tooth (oliver.tooth@noc.ac.uk) on 17/03/2025
#
# ----------------------------------------------------------------------------- #

# -- Input arguments to msm-os -- #
# Filepath to example model domain file:
filepath_grid=/path/to/model/domain_cfg.nc

# Filepath to example output file(s):
filedir=/path/to/npd/model/data
filepath_gridT=$filedir/eORCA1_ERA5_1y_grid_T_1976-1976.nc

# Filepath to JASMIN OS credentials:
store_credentials_json=.../jasmin_os_credentials.json

# Bucket and object prefix:
bucket=npd-eorca1-era5
prefix=T1y

# Define append dimension:
append_dim=time_counter

# -- Python Environment -- #
# Activate miniconda environment:
if [ ! -d "/path/to/miniconda3" ]; then
    echo "Error: Miniconda directory not found. Exiting."
    exit 1
fi

source /path/to/miniconda3/bin/activate || { echo "Error: Failed to activate Miniconda."; exit 1; }
conda activate my_env || { echo "Error: Failed to activate Conda environment."; exit 1; }

if [ ! -f "$filepath_grid" ]; then
    echo "Error: Model domain file not found: $filepath_grid"
    exit 1
fi

if [ ! -f "$filepath_gridT" ]; then
    echo "Error: Output file not found: $filepath_gridT"
    exit 1
fi

if [ ! -f "$store_credentials_json" ]; then
    echo "Error: Credentials file not found: $store_credentials_json"
    exit 1
fi

# -- Send eORCA1 ERA-5 annual mean outputs to object store -- # 
echo "In Progress: Sending example eORCA1 ERA-5 T1y variables to independent stores..."
ods send_to_zarr -f "$filepath_gridT" -c "$store_credentials_json" -b "$bucket" -p $prefix \
                 -gf "$filepath_grid" -uc '{"nav_lon":"glamt", "nav_lat":"gphit"}' \
                 -ad $append_dim -vs \
                 -cs '{"x":360,"y":331,"deptht":25}' || { echo "Error: ods send_to_zarr command failed."; exit 1; }

echo "Success: Sent file to eORCA1 ERA-5 T1y zarr stores."
