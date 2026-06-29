#!/bin/bash
#SBATCH --job-name=update_ostia_daily
#SBATCH --partition=compute
#SBATCH --time=03:00:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ==============================================================
# run_update_OSTIA_daily_to_os.slurm
#
# Description: SLURM script to update the OSTIA daily 
# time-series dataset in Icechunk repository.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# Created On: 2026-06-28
#
# ==============================================================
set -euo pipefail

# -- Python Environment -- #
# Activate miniconda environment:
source /dssgfs01/working/otooth/miniforge3/bin/activate
conda activate env_ods

# -- Send OSTIA daily time-series datasets to JASMIN OS -- #
echo "In Progress: Updating OSTIA Near-Real-Time Daily time-series in Icechunk..."

# python3 update_OSTIA_nrt_daily_to_os.py
python3 update_OSTIA_copernicus_nrt_daily_to_os.py

echo "Completed: Updated OSTIA Near-Real-Time Daily time-series in Icechunk."
