#!/bin/bash
# Example script to send a single file to the object store using msm_os
# send() function.
# Originally created by:
# - Ollie Tooth (17/03/2025)

# ----------------------------------------------------------------------------- #
#                                                                               #
#     Example: Using send() to create a zarr store from a batch of files        #
#                                                                               #
# ----------------------------------------------------------------------------- #
# -- Input arguments to msm-os -- #
# Filepath to eORCA1 ancillary file:
filepath_grid=/dssgfs01/scratch/npd/simulations/Domains/eORCA1/domain_cfg.nc

# Filepath to eORCA1 annual mean output files:
filedir=/dssgfs01/scratch/npd/simulations/eORCA1_ERA5_v1
filepath_gridT=$filedir/eORCA1_ERA5_1y_grid_T_1976-1976.nc

# Filepath to JASMIN OS credentials:
store_credentials_json=.../jasmin_os_credentials.json

# Bucket and object prefix:
bucket=npd-eorca1-era5

# -- Python Environment -- #
# Activate miniconda environment:
source ~/miniforge3/bin/activate
conda activate env_jasmin_os

# -- Send eORCA1 ERA-5 annual mean outputs to JASMIN OS -- # 
echo "In Progress: Sending eORCA1 ERA-5 T1y file to JASMIN object store..."
msm_os send -f $filepath_gridT -c $store_credentials_json -b $bucket -p T1y \
            -gf $filepath_grid -uc '{"nav_lon":"glamt", "nav_lat":"gphit"}' \
            -cs '{"x":360,"y":331,"deptht":25}'
