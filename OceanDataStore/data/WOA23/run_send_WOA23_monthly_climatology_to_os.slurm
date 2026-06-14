#!/bin/bash
#SBATCH --job-name=woa23_monthly_climatology
#SBATCH --partition=compute
#SBATCH --time=01:00:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ==============================================================
# run_send_WOA23_monthly_climatology_to_os.slurm
#
# Description: SLURM script to send the WOA23 Monthly Climatology
# datasets to Icechunk repository.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# Created On: 2026-06-06
#
# ==============================================================
set -euo pipefail

# -- Python Environment -- #
# Activate miniconda environment:
source .../miniforge3/bin/activate
conda activate env_ods

# -- Send WOA23 monthly climatology to JASMIN OS -- #
echo "In Progress: Sending WOA23 Monthly Climatologies to Icechunk..."

python3 send_WOA23_monthly_climatology_to_os.py

echo "Completed: Sent WOA23 Monthly Climatologies to Icechunk."
