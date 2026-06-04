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
set -euo pipefail

# -- Input arguments to OceanDataStore -- #
# Filepath to eORCA1 ancillary file:
filepath_domain=/dssgfs01/scratch/npd/simulations/Domains/eORCA1/domain_cfg.nc
# Filepath to eORCA1 monthly mean output files:
filedir=/dssgfs01/scratch/npd/simulations/eORCA1_ERA5_v1

# Filepath to JASMIN OS credentials:
store_credentials_json=.../credentials/jasmin_os_credentials.json

# Filepath to Dask Configuration file:
dask_config_json=.../OceanDataStore/tests/integration/cli/dask_config.json

# Bucket and object prefix:
bucket=oceandatastore
prefix=testing/U1m_icechunk_vc_test_dask

# Define the append dimension:
append_dim=time_counter

# Define variable:
variables="time_counter_bounds uo"

# -- Python Environment -- #
# Activate miniconda environment:
source .../miniforge3/bin/activate
conda activate env_ods

# -- Send eORCA1 ERA-5 v1 monthly mean outputs to JASMIN OS -- #
echo "In Progress: Sending eORCA1 ERA-5 v1 U1m variables to JASMIN object store..."
filepath_gridU=$filedir/eORCA1_ERA5_1m_grid_U_197601-197601.nc
ods send_to_icechunk -f $filepath_gridU -c $store_credentials_json -b $bucket -p $prefix \
                     -gf $filepath_domain -uc '{"nav_lon":"glamu", "nav_lat":"gphiu"}' \
                     -cs '{"x":360,"y":331,"depthu":25}' -v $variables \
                     -dc $dask_config_json -vc

echo "Completed: Sent eORCA1 ERA-5 v1 monthly mean fields to JASMIN object store."

echo "In Progress: Updating eORCA1 ERA-5 v1 U1m variables to JASMIN object store..."
filepath_gridU=$filedir/eORCA1_ERA5_1m_grid_U_1976*.nc
ods update_icechunk -f $filepath_gridU -c $store_credentials_json -b $bucket -p $prefix \
                    -gf $filepath_domain -uc '{"nav_lon":"glamu", "nav_lat":"gphiu"}' \
                    -ad $append_dim -cs '{"x":360,"y":331,"depthu":25}' -v $variables \
                    -dc $dask_config_json

echo "Completed: Updated eORCA1 ERA-5 v1 monthly mean fields in JASMIN object store."
