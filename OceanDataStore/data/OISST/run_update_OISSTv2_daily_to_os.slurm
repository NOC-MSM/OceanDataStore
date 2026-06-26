#!/bin/bash
#SBATCH --job-name=update_oisstv2_daily
#SBATCH --partition=compute
#SBATCH --time=03:00:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ==============================================================
# run_update_OISSTv2_daily_to_os.slurm
#
# Description: SLURM script to update the OISSTv2.1 daily 
# time-series dataset in Icechunk repository.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# Created On: 2026-06-09
#
# ==============================================================
set -euo pipefail

# -- Python Environment -- #
# Activate miniconda environment:
source /dssgfs01/working/otooth/miniforge3/bin/activate
conda activate env_ods

# -- Update OISSTv2.1 daily time-series datasets in JASMIN OS -- #
echo "In Progress: Updating OISSTv2.1 Daily time-series in Icechunk..."

python3 update_OISSTv2_daily_to_os.py

echo "Completed: Updated OISSTv2.1 Daily time-series in Icechunk."
