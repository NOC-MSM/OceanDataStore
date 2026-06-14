#!/bin/bash
#SBATCH --job-name=xfer_NSIDC_sea_ice_index_v4.0
#SBATCH --partition=test
#SBATCH --time=00:20:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ================================================================
# run_send_NSIDC_v4.0_to_OS.slurm
#
# Description: SLURM script to send the NSIDC sea ice observations
# data to the JASMIN Object Store.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# Created On: 2026-06-05
#
# ================================================================
set -euo pipefail

# -- Python Environment -- #
# Activate miniconda environment:
source .../miniforge3/bin/activate
conda activate env_ods

# -- Send NSIDC Sea Ice Index v4.0 to JASMIN OS -- #
echo "In Progress: Sending NSIDC Sea Ice Index v4.0 to Icechunk..."

python3 send_NSIDC_SII_v4.0_to_os.py

echo "Completed: Sent NSIDC Sea Ice Index v4.0 to Icechunk."
