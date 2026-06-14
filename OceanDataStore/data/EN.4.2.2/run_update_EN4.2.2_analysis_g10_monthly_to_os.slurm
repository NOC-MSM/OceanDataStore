#!/bin/bash
#SBATCH --job-name=en4.2.2_analysis_g10_monthly
#SBATCH --partition=compute
#SBATCH --time=01:00:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ==============================================================
# run_update_EN4.2.2_analysis_g10_monthly_to_os.slurm
#
# Description: SLURM script to update the EN.4.2.2 analysis g10 
# monthly datasets in Icechunk repository.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# Created On: 2026-05-29
#
# ==============================================================
set -euo pipefail

# -- Python Environment -- #
# Activate miniconda environment:
source .../miniforge3/bin/activate
conda activate env_ods

# -- Update EN.4.2.2.analysis.g10 monthly in JASMIN OS -- #
echo "In Progress: Updating EN.4.2.2.analysis.g10 monthly in Icechunk..."

python3 update_EN4.2.2_analysis_g10_monthly_to_os.py

echo "Completed: Updated EN.4.2.2.analysis.g10 monthly in Icechunk."
