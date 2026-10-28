#!/bin/bash
#SBATCH --job-name=lops_mld_monthly_climatology
#SBATCH --partition=compute
#SBATCH --time=01:00:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ==============================================================
# run_send_LOPS_MLD_climatology_to_os.slurm
#
# Description: SLURM script to send the LOPS-MLD Monthly Climatology
# datasets to Icechunk repository.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# Created On: 2026-10-27
#
# ==============================================================
set -euo pipefail

# -- Python Environment -- #
# Activate miniconda environment:
source .../miniforge3/bin/activate
conda activate env_ods

# -- Send LOPS-MLD monthly climatology to JASMIN OS -- #
echo "In Progress: Sending LOPS-MLD Monthly Climatologies to Icechunk..."

python3 send_LOPS_MLD_climatology_to_os.py

echo "Completed: Sent LOPS-MLD Monthly Climatologies to Icechunk."
