#!/bin/bash
#SBATCH --job-name=xfer_npd_eorca1_era5v1_1y
#SBATCH --partition=compute
#SBATCH --time=08:00:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ===================================================================
# run_npd_eorca1_era5v1_medusa_rivers_1y.slurm
#
# Description: SLURM script to send the eORCA1 + MEDUSA RIVER ERA5v1 annual
# -mean netCDF outputs to Icechunk repository.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# Created On: 2026-09-04
#
# ===================================================================
# -- Python Environment -- #
# Activate miniconda environment:
source /dssgfs01/working/otooth/miniforge3/bin/activate
conda activate env_ods

# -- Send eORCA1 annual-mean outputs to JASMIN OS -- #
echo "In Progress: Sending eORCA1 ERA5v1 annual-mean outputs to Icechunk..."

python3 send_npd_eorca1_era5v1_medusa_rivers.py \
    --credentials .../credentials/jasmin_os_credentials.json \
    --datestr '' \
    --frequency 1y \
    --group_list gridT gridU gridV gridW gridF \
    --mode send \

echo "Completed: Sent eORCA1 ERA5v1 annual-mean outputs to Icechunk."