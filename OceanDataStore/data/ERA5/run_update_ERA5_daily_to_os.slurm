#!/bin/bash
#SBATCH --job-name=update_era5_daily
#SBATCH --partition=compute
#SBATCH --time=03:00:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ==============================================================
# run_update_ERA5_daily_to_os.slurm
#
# Description: SLURM script to update the ERA5 daily 
# time-series dataset in the Icechunk repository.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# Created On: 2026-06-25
#
# ==============================================================
set -euo pipefail

# -- Python Environment -- #
# Activate miniconda environment:
source /dssgfs01/working/otooth/miniforge3/bin/activate
conda activate env_ods

# -- Update ERA5 daily time-series datasets in JASMIN OS -- #
echo "In Progress: Updating ERA5 daily time-series in Icechunk..."

python3 update_ERA5_daily_to_os.py

echo "Completed: Updated ERA5 daily time-series in Icechunk."
