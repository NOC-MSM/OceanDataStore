#!/bin/bash
#SBATCH --job-name=xfer_npd_eorca12_era5v1
#SBATCH --partition=compute
#SBATCH --time=18:00:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ==============================================================
# run_earthmover_npd_eorca12_era5v1.slurm
#
# Description: SLURM script to send the eORCA12 5-day mean 
# variables to Icechunk repository.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# Created On: 2026-04-21
#
# ==============================================================
# -- Python Environment -- #
# Activate miniconda environment:
source /dssgfs01/working/otooth/miniforge3/bin/activate
conda activate env_nemo

# -- Send eORCA12 5-day mean outputs to JASMIN OS -- #
echo "In Progress: Sending eORCA12 ERA5v1 variables to Icechunk..."

# python3 earthmover_send_npd_eorca12_era5v1.py
python3 earthmover_update_npd_eorca12_era5v1.py

echo "Completed: Sent eORCA12 ERAA5v1 5-day mean fields to Icechunk."