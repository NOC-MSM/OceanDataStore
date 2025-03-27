#!/bin/bash
# Example script to send a batch of files to the object store using msm_os
# update_with_dask() function.
# Originally created by:
# - Ollie Tooth (17/03/2025)

# --------------------------------------------------------------------------------- #
#                                                                                   #
# Example: Using update_with_dask() to create a zarr store from a batch of files    #
#                                                                                   #
# --------------------------------------------------------------------------------- #

# -- Input arguments to msm-os -- #
# Filepath to eORCA1 ancillary file:
filepath_grid=/dssgfs01/scratch/npd/simulations/Domains/eORCA1/domain_cfg.nc

# Filepath to eORCA1 annual mean output files:
filedir=/dssgfs01/scratch/npd/simulations/eORCA1_ERA5_v1
filepath_gridT=$filedir/eORCA1_ERA5_1y_grid_T_*.nc

# Filepath to JASMIN OS credentials:
store_credentials_json=..../jasmin_os_credentials.json

# Filepath to Dask cluster configuration:
dask_config_json=..../dask_config.json

# Bucket and object prefix:
bucket=npd-eorca1-era5

# -- Python Environment -- #
# Activate miniconda environment:
if [ ! -d "~/miniforge3" ]; then
    echo "Error: Miniforge directory not found. Exiting."
    exit 1
fi

source /path/to/miniconda3/bin/activate || { echo "Error: Failed to activate Miniforge."; exit 1; }
conda activate my_env || { echo "Error: Failed to activate Conda environment."; exit 1; }

if [ ! -f "$filepath_grid" ]; then
    echo "Error: Ancillary file not found: $filepath_grid"
    exit 1
fi

if [ -z "$( ls -A $filepath_gridT )" ]; then
    echo "Error: No matching output files found: $filepath_gridT"
    exit 1
fi

if [ ! -f "$store_credentials_json" ]; then
    echo "Error: Credentials file not found: $store_credentials_json"
    exit 1
fi

if [ ! -f "$dask_config_json" ]; then
    echo "Error: Dask configuration file not found: $dask_config_json"
    exit 1
fi

# -- Send eORCA1 ERA-5 annual mean outputs to JASMIN OS -- # 
echo "In Progress: Sending eORCA1 ERA-5 T1y variables to JASMIN object store..."
msm_os update_with_dask -f $filepath_gridT -c $store_credentials_json -b $bucket -p T1y \
                       -gf $filepath_grid -uc '{"nav_lon":"glamt", "nav_lat":"gphit"}' \
                       -cs '{"x":360,"y":331,"deptht":25}' \
                       -dc $dask_config_json || { echo "Error: msm_os update_with_dask command failed."; exit 1; }

echo "Success: Files sent to object store."
