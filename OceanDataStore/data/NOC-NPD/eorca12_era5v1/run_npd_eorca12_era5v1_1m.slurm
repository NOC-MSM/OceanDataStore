#!/bin/bash
#SBATCH --job-name=xfer_npd_eorca12_era5v1_1m
#SBATCH --partition=compute
#SBATCH --time=20:00:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ===================================================================
# run_npd_eorca12_era5v1_1m.slurm
#
# Description: SLURM script to send the eORCA12 ERA5v1 monthly-mean
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

# -- Send eORCA12 monthly-mean outputs to JASMIN OS -- #
echo "In Progress: Sending eORCA12 ERA5v1 monthly-mean outputs to Icechunk..."

python3 send_npd_eorca12_era5v1.py \
    --credentials .../credentials/jasmin_os_credentials.json \
    --datestr 202 \
    --frequency 1m \
    --group_list gridT gridU gridV gridW \
    --mode update \
    --source os \

echo "Completed: Sent eORCA12 ERA5v1 monthly-mean outputs to Icechunk."