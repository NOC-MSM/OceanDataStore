#!/bin/bash
#SBATCH --job-name=test_update_icechunk
#SBATCH --partition=test
#SBATCH --time=00:20:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ==============================================================
# test_update_vc_icechunk.slurm
#
# Description: SLURM script to test update_icechunk using the
# eORCA1 ERA-5 v1 monthly-mean output variables.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# Created On: 2025-05-15
#
# ==============================================================
# -- Input arguments to msm-os -- #
# Filepath to eORCA1 ancillary file:
filepath_domain=/dssgfs01/scratch/npd/simulations/Domains/eORCA1/domain_cfg.nc
# Filepath to eORCA1 monthly mean output files:
filedir=/dssgfs01/scratch/npd/simulations/eORCA1_ERA5_v1

# Filepath to JASMIN OS credentials:
store_credentials_json=.../credentials/jasmin_os_credentials.json

# Filepath to Dask Configuration file:
dask_config_json=.../OceanDataStore/tests/dask_config.json

# Bucket and object prefix:
bucket=npd-eorca1-era5v1
prefix=test/U1m

# Define the append dimension:
append_dim=time_counter

# Define variable:
variables="time_counter_bounds uo"

# -- Python Environment -- #
# Activate miniconda environment:
source /home/otooth/miniconda3/etc/profile.d/conda.sh
conda activate env_testing

# -- Send eORCA1 ERA-5 v1 monthly mean outputs to JASMIN OS -- #
echo "In Progress: Sending eORCA1 ERA-5 v1 U1m variables to JASMIN object store..."
filepath_gridU=$filedir/eORCA1_ERA5_1m_grid_U_197601-197601.nc
ods send_to_icechunk -f $filepath_gridU -c $store_credentials_json -b $bucket -p $prefix \
                     -gf $filepath_domain -uc '{"nav_lon":"glamu", "nav_lat":"gphiu"}' \
                     -cs '{"x":360,"y":331,"depthu":25}' -v $variables \
                     -dc $dask_config_json -vc || { echo "Error: ods send_to_icechunk failed."; exit 1; }

echo "Completed: Sent eORCA1 ERA-5 v1 monthly mean fields to JASMIN object store."

echo "In Progress: Updating eORCA1 ERA-5 v1 U1m variables to JASMIN object store..."
variables="umo"
ods update_icechunk -f $filepath_gridU -c $store_credentials_json -b $bucket -p $prefix \
                    -gf $filepath_domain -uc '{"nav_lon":"glamu", "nav_lat":"gphiu"}' \
                    -ad $append_dim -cs '{"x":360,"y":331,"depthu":25}' -v $variables \
                    -dc $dask_config_json -vc || { echo "Error: ods update_icechunk failed."; exit 1; }

echo "Completed: Updated eORCA1 ERA-5 v1 monthly mean fields in JASMIN object store."
