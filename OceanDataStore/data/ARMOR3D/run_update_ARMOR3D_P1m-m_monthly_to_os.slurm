#!/bin/bash
#SBATCH --job-name=armor3d_monthly_update
#SBATCH --partition=compute
#SBATCH --time=01:00:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ==============================================================
# run_update_ARMOR3D_P1m-m_monthly_to_os.slurm
#
# Description: SLURM script to update the ARMOR3D P1m-m 
# monthly dataset in Icechunk repository.
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

# -- Update ARMOR3D P1m-m monthly in JASMIN OS -- #
echo "In Progress: Updating ARMOR3D P1m-m monthly in Icechunk..."

python3 update_ARMOR3D_P1m-m_monthly_to_os.py

echo "Completed: Updated ARMOR3D P1m-m monthly in Icechunk."
