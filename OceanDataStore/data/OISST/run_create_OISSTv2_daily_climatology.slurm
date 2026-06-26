#!/bin/bash
#SBATCH --job-name=oisstv2_daily_climatology
#SBATCH --partition=compute
#SBATCH --time=05:00:00
#SBATCH --ntasks-per-core=1
#SBATCH --ntasks-per-node=64
#SBATCH --ntasks-per-socket=32
#SBATCH --nodes=1

# ==============================================================
# run_create_OISSTv2_daily_climatology.slurm
#
# Description: SLURM script to create the OISSTv2.1 daily 
# climatology datasets.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# Created On: 2026-06-25
#
# ==============================================================
set -euo pipefail
TIME1=`date +%s`

# -- Python Environment -- #
# Activate miniconda environment:
source /dssgfs01/working/otooth/miniforge3/bin/activate
conda activate env_ods

# -- Create OISSTv2.1 daily climatology datasets -- #
dpath="/dssgfs01/scratch/otooth/npd_data/observations/OISST/daily/"
opath="/dssgfs01/scratch/otooth/npd_data/observations/OISST/climatology"
year_start=1996
year_end=2025

echo "Start year  : " $year_start
echo "End year    : " $year_end
echo "Output file : " $opath/OISST_v2.1_sst_climatology_${year_start}-${year_end}.nc

python3 create_OISSTv2_daily_climatology.py --year_start $year_start --year_end $year_end --data_path $dpath --output $opath/oisst_climatology_${year_start}-${year_end}.nc

# -- Report Job Timing -- #
TIME2=`date +%s`
DIFFSEC=`expr ${TIME2} - ${TIME1}`
echo Job Completed in: ${DIFFSEC} seconds.
echo Job Took: `date +%H:%M:%S -ud @${DIFFSEC}`
