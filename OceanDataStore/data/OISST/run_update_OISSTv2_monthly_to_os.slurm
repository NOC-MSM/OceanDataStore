#!/bin/bash
#SBATCH --job-name=update_oisstv2_monthly
#SBATCH --partition=compute
#SBATCH --time=01:00:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ==============================================================
# run_update_OISSTv2_monthly_to_os.slurm
#
# Description: SLURM script to update the OISSTv2.1 monthly 
# time-series dataset in Icechunk repository.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
#
# ==============================================================
set -euo pipefail

# -- Python Environment -- #
# Activate miniconda environment:
source .../miniforge3/bin/activate
conda activate env_ods

# -- Update OISSTv2.1 monthly time-series datasets in JASMIN OS -- #
echo "In Progress: Updating OISSTv2.1 Monthly time-series in Icechunk..."

python3 update_OISSTv2_monthly_to_os.py

echo "Completed: Updated OISSTv2.1 Monthly time-series in Icechunk."
