#!/bin/bash
#SBATCH --job-name=send_oisstv2_daily
#SBATCH --partition=compute
#SBATCH --time=03:00:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ==============================================================
# run_send_OISSTv2_daily_to_os.slurm
#
# Description: SLURM script to send the OISSTv2.1 daily 
# time-series dataset to Icechunk repository.
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

# -- Send OISSTv2.1 daily time-series datasets to JASMIN OS -- #
echo "In Progress: Sending OISSTv2.1 Daily time-series to Icechunk..."

python3 send_OISSTv2_daily_to_os.py

echo "Completed: Sent OISSTv2.1 Daily time-series to Icechunk."
