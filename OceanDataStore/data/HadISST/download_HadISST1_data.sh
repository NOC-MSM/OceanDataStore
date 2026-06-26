#!/bin/bash

# ----------------------------------------------------------------
# download_HadISST1_data.sh
#
# This script downloads the HadISST1 dataset from the Met Office
# Hadley Centre HadISST website. The files to be downloaded are
# HadISST1_sst.nc.gz & HadISST_ice.nc.gz.
#
# Files will be downloaded into the current directory.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# Created On: 2026-05-27
# ----------------------------------------------------------------
set -euo pipefail

# --- Inputs --- #
# Output directory for downloaded files:
output_dir="/dssgfs01/scratch/otooth/npd_data/observations/HadISST"

# Define base URL to HadISST1 dataset:
url=https://www.metoffice.gov.uk/hadobs/hadisst/data

# --- Main Script --- #
echo "==================================================="
echo "          Downloading HadISST1 Dataset"
echo "                     v0.1.0"
echo "               Oliver J. Tooth, NOC"
echo "==================================================="
echo "In Progress: Downloading HadISST1 dataset..."

# Download the HadISST1 dataset:
echo "-> Downloading HadISST1_sst.nc.gz & HadISST_ice.nc.gz..."
wget -P $output_dir $url/HadISST_sst.nc.gz
wget -P $output_dir $url/HadISST_ice.nc.gz

# Unzip the files:
echo "-> Unzipping HadISST1 dataset..."
gunzip $output_dir/HadISST_sst.nc.gz
gunzip $output_dir/HadISST_ice.nc.gz

# Update users via stdout:
echo "...Completed: HadISST1 dataset downloaded and unzipped."
