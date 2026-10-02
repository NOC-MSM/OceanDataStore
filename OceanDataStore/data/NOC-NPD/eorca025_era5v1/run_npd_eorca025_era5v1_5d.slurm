#!/bin/bash
#SBATCH --job-name=xfer_npd_eorca025_era5v1_5d
#SBATCH --partition=compute
#SBATCH --time=12:00:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ===================================================================
# run_npd_eorca025_era5v1_5d.slurm
#
# Description: SLURM script to send the eORCA025 ERA5v1 5-day mean
# netCDF outputs to Icechunk repository.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# Created On: 2026-08-12
#
# ===================================================================
# -- Python Environment -- #
# Activate miniconda environment:
source /dssgfs01/working/otooth/miniforge3/bin/activate
conda activate env_ods

# -- Send eORCA025 5-day mean outputs to JASMIN OS -- #
echo "In Progress: Sending eORCA025 ERA5v1 5-day mean outputs to Icechunk..."

python3 send_npd_eorca025_era5v1.py \
    --credentials .../credentials/jasmin_os_credentials.json \
    --datestr 202 \
    --frequency 5d \
    --group_list gridV gridW \
    --mode update \

echo "Completed: Sent eORCA025 ERA5v1 5-day mean outputs to Icechunk."