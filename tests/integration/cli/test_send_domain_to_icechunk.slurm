#!/bin/bash
#SBATCH --job-name=test_send_to_icechunk
#SBATCH --partition=test
#SBATCH --time=00:20:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ==============================================================
# test_send_domain_to_icechunk.slurm
#
# Description: SLURM script to test send_to_icechunk using the
# eORCA1 ERA-5 v1 monthly-mean output variables.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# Created On: 2025-09-16
#
# ==============================================================
# -- Input arguments to msm-os -- #
# Filepath to eORCA1 ancillary file:
filepath_domain=/dssgfs01/scratch/npd/simulations/Domains/eORCA1/subbasins_CMIP6.nc

# Filepath to JASMIN OS credentials:
store_credentials_json=.../credentials/jasmin_os_credentials.json

# Filepath to Dask Configuration file:
dask_config_json=.../OceanDataStore/tests/dask_config.json

# Bucket and object prefix:
bucket=npd-eorca1-era5v1

# -- Python Environment -- #
# Activate miniconda environment:
source /home/otooth/miniconda3/etc/profile.d/conda.sh
conda activate env_jasmin_os

# -- Send eORCA1 ERA-5 v1 subbasins to JASMIN OS -- #
prefix=test/domain_icechunk

echo "In Progress: Sending eORCA1 ERA-5 v1 subbasins to JASMIN object store without Dask..."
ods send_to_icechunk -f $filepath_domain -c $store_credentials_json -b $bucket -p $prefix \
                     -cs '{"x":360,"y":331}' || { echo "Error: ods send_to_icechunk failed."; exit 1; }

echo "Completed: Sent eORCA1 ERA-5 v1 subbasins to JASMIN object store without Dask."

# -- Send eORCA1 ERA-5 v1 subbasins to JASMIN OS -- #
prefix=test/domain_icechunk_dask

echo "In Progress: Sending eORCA1 ERA-5 v1 subbasins to JASMIN object store with Dask..."
ods send_to_icechunk -f $filepath_domain -c $store_credentials_json -b $bucket -p $prefix \
                     -cs '{"x":360,"y":331}' -dc $dask_config_json || { echo "Error: ods send_to_icechunk failed."; exit 1; }

echo "Completed: Sent eORCA1 ERA-5 v1 subbasins to JASMIN object store with Dask."
