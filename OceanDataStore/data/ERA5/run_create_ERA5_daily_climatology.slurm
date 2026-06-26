#!/bin/bash
#SBATCH --job-name=era5_daily_climatology
#SBATCH --time=12:00:00
#SBATCH --partition=compute
#SBATCH --nodes=1
#SBATCH --mem=0
#SBATCH --exclusive
##SBATCH --mem-per-cpu=4G
##SBATCH --ntasks-per-node=64
##SBATCH --ntasks-per-socket=32
##SBATCH --ntasks-per-core=1

module load NEMO/prg-env
#============================
export I_MPI_SHM=icx

source /dssgfs01/working/atb299/miniforge3/bin/activate
conda activate Sci

# ==============================================================
# run_create_ERA5_daily_climatology.slurm
#
# Description: SLURM script to create the ERA5 daily 
# climatology datasets.
#
# Created By: Adam Blaker (atb299@noc.ac.uk)
# Created On: 2026-06-25
#
# ==============================================================

#============================
TIME1=`date +%s`

dpath="/dssgfs01/scratch/atb299/ERA5_daily/ERA5_daily_fields/"

Ystart=1996
Yend=$((Ystart+29))

ofile="/dssgfs01/scratch/otooth/npd_data/observations/ERA5/climatology/ERA5_sst_climatology_${Ystart}-${Yend}.nc"

echo "Start year  : " $Ystart
echo "End year    : " $Yend
echo "Output file : " $ofile

python create_ERA5_daily_climatology.py $Ystart $Yend --data_path $dpath --output $ofile

#============================
# Job timing

TIME2=`date +%s`
DIFFSEC=`expr ${TIME2} - ${TIME1}`
echo Took ${DIFFSEC} seconds.
echo Took `date +%H:%M:%S -ud @${DIFFSEC}`

