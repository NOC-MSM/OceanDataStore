#!/bin/bash

# ----------------------------------------------------------------
# download_EN4.2.2_analyses_g10_data.sh
#
# Description: Download the EN.4.2.2 analyses.g10 dataset from the
# Met Office Hadley Centre EN.4.2.2 website:
# http://www.metoffice.gov.uk/hadobs/en4
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# Created On: 2026-05-27
# ----------------------------------------------------------------
set -euo pipefail

# --- Inputs --- #
output_dir="/dssgfs01/scratch/otooth/npd_data/observations/EN.4.2.2/"

# -- Defaults -- #
base_url="http://www.metoffice.gov.uk/hadobs/en4/data/en4-2-1"

# --- Main Script --- #
echo "==================================================="
echo "          Downloading EN.4.2.2 Analyses"
echo "                     v0.1.0"
echo "               Oliver J. Tooth, NOC"
echo "==================================================="
echo "In Progress: Downloading EN.4.2.2 analyses dataset..."
# Iterate over years:
for yr in {1990..2026}; do
    # Construct URL for current year:
    if [ $yr -ge 2021 ]; then
        url="$base_url/EN.4.2.2.analyses.g10.${yr}.zip"
    else 
        url="$base_url/EN.4.2.2/EN.4.2.2.analyses.g10.${yr}.zip"
    fi

    # Download and unzip file if not in output directory:
    nc_files=("${output_dir}/EN.4.2.2.f.analysis.g10.${yr}"*.nc)
    filepath="$output_dir/$(basename $url)"
    if [ ${#nc_files[@]} -ne 12 ]; then
        wget -P $output_dir $url
        echo "-> Completed: Downloaded $filepath."

        unzip "$filepath" -d $output_dir
        echo "-> Completed: Unzipped $filepath."
    else
        echo "-> Skipping Download: NetCDF files for ${yr} already exist in $output_dir."
    fi
done

echo "======================================="
