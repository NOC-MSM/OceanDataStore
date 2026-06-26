#!/bin/bash
#SBATCH --job-name=hadisst1_monthly
#SBATCH --partition=test
#SBATCH --time=00:20:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ==============================================================
# run_send_HadISST1_monthly_to_os.slurm
#
# Description: SLURM script to send the HadISST1 monthly 
# time-series dataset to Icechunk repository.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# Created On: 2026-06-24
#
# ==============================================================
set -euo pipefail

# -- Python Environment -- #
# Activate miniconda environment:
source /dssgfs01/working/otooth/miniforge3/bin/activate
conda activate env_ods

# -- Send HadISST1 monthly time-series datasets to JASMIN OS -- #
echo "In Progress: Sending HadISST1 monthly time-series to Icechunk..."

python3 send_HadISST1_monthly_to_os.py

echo "Completed: Sent HadISST1 monthly time-series to Icechunk."
