#!/bin/bash
#SBATCH --job-name=send_armor3d_my_climatology
#SBATCH --partition=compute
#SBATCH --time=04:00:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ==============================================================
# run_send_ARMOR3D_P1M-m_climatology_to_os.slurm
#
# Description: SLURM script to send the ARMOR3D P1M-m monthly 
# climatology datasets to Icechunk repository.
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

# -- Send ARMOR3D P1M-m monthly climatology datasets to JASMIN OS -- #
echo "In Progress: Sending ARMOR3D P1M-m monthly climatology to Icechunk..."

python3 send_ARMOR3D_P1m-m_monthly_climatology_to_os.py

echo "Completed: Sent ARMOR3D P1M-m monthly climatology to Icechunk."
