#!/bin/bash

# ----------------------------------------------------------------
# download_NSIDC_monthly_1979_2025_data.sh
#
# Description: Download the National Snow & Ice Data Centre (NSIDC)
# Sea Ice Index version 4 sea ice extent & concentration GeoTiff
# files from 1979 to 2025.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# Created On: 2026-05-27
# ----------------------------------------------------------------
set -euo pipefail

# --- Inputs --- #
# Define hemisphere to download data for (options: "north" or "south"):
hemisphere="north"

# Define output directory for downloaded files:
output_dir="/dssgfs01/scratch/otooth/npd_data/observations/NSIDC/"$hemisphere"/"

# Single year download:
single_year=True
# Define year to download if single_year is True:
year=2025

# -- Defaults -- #
# Default URL prefix:
url_prefix="https://noaadata.apps.nsidc.org/NOAA/G02135/"$hemisphere"/monthly/geotiff"

# -- Main Script -- #
echo "==================================================="
echo "          Downloading NSIDC Sea Ice Index"
echo "                     v4.0"
echo "               Oliver J. Tooth, NOC"
echo "==================================================="
echo "In Progress: Downloading NSIDC Sea Ice Index dataset..."

mkdir -p $output_dir
cd $output_dir

# Download monthly sea ice extent & concentration files from 1979 to 2025:
for month in 01_Jan 02_Feb 03_Mar 04_Apr 05_May 06_Jun 07_Jul 08_Aug 09_Sep 10_Oct 11_Nov 12_Dec
do 
    if [ "$single_year" = True ]; then
        echo "Downloading NSIDC $year Sea Ice Conc. GeoTiffs for: $month"
        wget -r -nd --no-check-certificate --reject "index.html*" -np -e robots=off $url_prefix/$month/ -A "*_${year}*_v4.0.tif"
    else
        echo "Downloading NSIDC 1979-2025 Sea Ice Conc. GeoTiffs for: $month"
        wget -r -nd --no-check-certificate --reject "index.html*" -np -e robots=off $url_prefix/$month/
    fi
done

echo "-> Completed: Downloaded NSIDC" $hemisphere "Sea Ice Extent & Concentration GeoTiffs"
