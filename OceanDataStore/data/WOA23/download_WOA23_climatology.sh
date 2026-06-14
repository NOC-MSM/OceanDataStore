#!/bin/bash

# ----------------------------------------------------------------
# download_WOA23_climatology.sh
#
# Description: Download the World Ocean Atlas 2023 30-year climatologies
# using URLs provided by the National Centers for Environmental Information.
# WOA23 provides Climate Normals for temperature and salinity at 0.25 degree
# resolution as 30-year averages for validating models.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# Created On: 2026-05-27
# ----------------------------------------------------------------
set -euo pipefail

echo "==================================================="
echo "          Downloading WOA23 Climatologies"
echo "                     v0.1.0"
echo "               Oliver J. Tooth, NOC"
echo "==================================================="
echo "In Progress: Downloading WOA23 Upper 1500m Climatologies..."
for i in {00..16}; do echo $i; wget https://www.ncei.noaa.gov/data/oceans/woa/WOA23/DATA/temperature/netcdf/decav71A0/0.25/woa23_decav71A0_t${i}_04.nc ; done

for i in {00..16}; do echo $i; wget https://www.ncei.noaa.gov/data/oceans/woa/WOA23/DATA/temperature/netcdf/decav81B0/0.25/woa23_decav81B0_t${i}_04.nc ; done

for i in {00..16}; do echo $i; wget https://www.ncei.noaa.gov/data/oceans/woa/WOA23/DATA/temperature/netcdf/decav91C0/0.25/woa23_decav91C0_t${i}_04.nc ; done
echo "Completed: Downloaded Upper 1500m WOA23 temperature climatologies"

echo "In Progress: Downloading WOA23 Upper 1500m Salinity Climatologies..."
for i in {00..16}; do echo $i; wget https://www.ncei.noaa.gov/data/oceans/woa/WOA23/DATA/salinity/netcdf/decav71A0/0.25/woa23_decav71A0_s${i}_04.nc ; done

for i in {00..16}; do echo $i; wget https://www.ncei.noaa.gov/data/oceans/woa/WOA23/DATA/salinity/netcdf/decav81B0/0.25/woa23_decav81B0_s${i}_04.nc ; done

for i in {00..16}; do echo $i; wget https://www.ncei.noaa.gov/data/oceans/woa/WOA23/DATA/salinity/netcdf/decav91C0/0.25/woa23_decav91C0_s${i}_04.nc ; done
echo "Completed: Downloaded Upper 1500m WOA23 salinity climatologies"

# Winter average of full time period, covering full ocean depth:
echo "In Progress: Downloading WOA23 Full Depth Climatologies..."
wget https://www.ncei.noaa.gov/data/oceans/woa/WOA23/DATA/temperature/netcdf/decav/0.25/woa23_decav_t13_04.nc
wget https://www.ncei.noaa.gov/data/oceans/woa/WOA23/DATA/salinity/netcdf/decav/0.25/woa23_decav_s13_04.nc
echo "Completed: Downloaded WOA23 Full Depth Climatologies"
