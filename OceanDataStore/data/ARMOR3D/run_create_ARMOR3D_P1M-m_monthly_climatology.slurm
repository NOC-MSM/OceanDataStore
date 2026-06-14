#!/bin/bash
#SBATCH --job-name=armor3d_monthly_climatology
#SBATCH --partition=compute
#SBATCH --time=04:00:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ==============================================================
# run_create_ARMOR3D_P1M-m_monthly_climatology.slurm
#
# Description: SLURM script to create ARMOR3D REP monthly 
# climatology datasets.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# Created On: 2026-06-09
#
# ==============================================================
set -euo pipefail

# -- Python Environment -- #
# Activate miniconda environment:
source .../miniforge3/bin/activate
conda activate env_ods

# -- Create ARMOR3D REP monthly climatology datasets -- #
echo "In Progress: Creating ARMOR3D REP monthly climatology datasets..."

python3 create_ARMOR3D_P1M-m_monthly_climatology.py

echo "Completed: Created ARMOR3D REP monthly climatology datasets."
