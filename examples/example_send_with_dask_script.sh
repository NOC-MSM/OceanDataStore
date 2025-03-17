#!/bin/bash
# Example script to send a batch of files to the object store using msm_os
# send_with_dask() function.
# Originally created by:
# - Ollie Tooth (17/03/2025)

# ----------------------------------------------------------------------------- #
#                                                                               #
# Example: Using send_with_dask() to create a zarr store from a batch of files  #
#                                                                               #
# ----------------------------------------------------------------------------- #
# -- Input arguments to msm-os -- #
# Filepath to eORCA1 ancillary file:
filepath_grid=/dssgfs01/scratch/npd/simulations/Domains/eORCA1/domain_cfg.nc

# Filepath to eORCA1 annual mean output files:
filedir=/dssgfs01/scratch/npd/simulations/eORCA1_ERA5_v1
filepath_gridT=$filedir/eORCA1_ERA5_1y_grid_T_*.nc

# Filepath to JASMIN OS credentials:
store_credentials_json=.../jasmin_os_credentials.json

# Bucket and object prefix:
bucket=npd-eorca1-era5

# -- Python Environment -- #
# Activate miniconda environment:
source ~/miniforge3/bin/activate
conda activate env_jasmin_os

# -- Send eORCA1 ERA-5 annual mean outputs to JASMIN OS -- # 
echo "In Progress: Sending eORCA1 ERA-5 T1y variables to JASMIN object store..."
msm_os send_with_dask -f $filepath_gridT -c $store_credentials_json -b $bucket -p T1y \
                      -gf $filepath_grid -uc '{"nav_lon":"glamt", "nav_lat":"gphit"}' \
                      -cs '{"x":360,"y":331,"deptht":25}' \
                      -dco '{"temporary_directory":"/temporary/directory","local_directory":"/local/directory/"}' \
                      -dlc '{"n_workers":30,"threads_per_worker":1,"memory_limit":"2GB"}'