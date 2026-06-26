#!/bin/bash

# ----------------------------------------------------------------
# download_OISSTv2_data.sh
#
# Description: Download the OISSTv2 dataset from the
# NOAA website:
# https://psl.noaa.gov/data/gridded/data.noaa.oisst.v2.highres.html
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# Created On: 2026-06-24
# ----------------------------------------------------------------
set -euo pipefail

# --- Inputs --- #
output_dir="/dssgfs01/scratch/otooth/npd_data/observations/OISST/daily/" 

# -- Defaults -- #
base_url="https://downloads.psl.noaa.gov//Datasets/noaa.oisst.v2.highres"

# --- Main Script --- #
echo "==================================================="
echo "          Downloading OISSTv2 Data"
echo "                     v0.1.0"
echo "               Oliver J. Tooth, NOC"
echo "==================================================="
echo "In Progress: Downloading OISSTv2 dataset..."
# Iterate over years:
for yr in {2012..2026}; do
    # Construct URL for current year:
    url="$base_url/sst.day.mean.${yr}.nc"

    # Download file if not in output directory:
    filepath="$output_dir/$(basename $url)"
    if [ ! -f "$filepath" ]; then
        wget -P $output_dir $url
        echo "-> Completed: Downloaded $filepath."
    else
        echo "-> Skipping Download: NetCDF file for ${yr} already exists in $output_dir."
    fi
done

echo "==================================================="
