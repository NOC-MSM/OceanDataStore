#!/bin/bash
# Example script to send a update file in the object store using msm_os
# update() function.
# Originally created by:
# - Ollie Tooth (27/03/2025)

# ----------------------------------------------------------------------------- #
#                                                                               #
#     Example: Using update() to create a zarr store from a batch of files      #
#                                                                               #
# ----------------------------------------------------------------------------- #

# -- Input arguments to msm-os -- #
# Filepath to example model domain file:
filepath_grid=/path/to/model/domain_cfg.nc

# Filepath to example output file(s):
filedir=/path/to/npd/model/data
filepath_gridT=$filedir/eORCA1_ERA5_1y_grid_T_1977-1977.nc

# Filepath to JASMIN OS credentials:
store_credentials_json=.../jasmin_os_credentials.json

# Bucket and object prefix:
bucket=npd-eorca1-era5

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
echo "In Progress: Sending example eORCA1 ERA-5 T1y file to object store..."
msm_os update -f "$filepath_gridT" -c "$store_credentials_json" -b "$bucket" -p T1y \
              -gf "$filepath_grid" -uc '{"nav_lon":"glamt", "nav_lat":"gphit"}' \
              -a $append_dim \
              -cs '{"x":360,"y":331,"deptht":25}' || { echo "Error: msm_os update command failed."; exit 1; }

echo "Success: File sent to object store."
