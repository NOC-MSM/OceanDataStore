#!/bin/bash
#SBATCH --job-name=era5_daily_climatology
#SBATCH --partition=compute
#SBATCH --time=02:00:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ==============================================================
# run_send_ERA5_daily_climatology_to_os.slurm
#
# Description: SLURM script to send the ERA5 daily 
# climatology datasets to Icechunk repository.
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

# -- Send ERA5 daily climatology datasets to JASMIN OS -- #
echo "In Progress: Sending ERA5 daily climatology to Icechunk..."

python3 send_ERA5_daily_climatology_to_os.py

echo "Completed: Sent ERA5 daily climatology to Icechunk."
