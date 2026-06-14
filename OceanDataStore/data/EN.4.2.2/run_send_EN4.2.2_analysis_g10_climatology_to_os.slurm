#!/bin/bash
#SBATCH --job-name=en4.2.2_analysis_g10_climatology
#SBATCH --partition=test
#SBATCH --time=00:20:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ==============================================================
# run_send_EN4.2.2_analysis_g10_climatology_to_os.slurm
#
# Description: SLURM script to send the EN.4.2.2 analysis g10 
# climatology datasets to Icechunk repository.
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

# -- Send EN.4.2.2.analysis.g10 climatology datasets to JASMIN OS -- #
echo "In Progress: Sending EN.4.2.2.analysis.g10 climatology to Icechunk..."

python3 send_EN4.2.2_analysis_g10_monthly_climatology_to_os.py

echo "Completed: Sent EN.4.2.2.analysis.g10 climatology to Icechunk."
