"""
Download global domain of ARMOR-3D dataset from Copernicus Marine.
This script downloads the monthly reprocessed files from 1993 to 2024.

Created By: Ollie Tooth
Created On: 2026-04-21
Contact: oliver.tooth@noc.ac.uk

Note: This download script should be run using the env_oceandatastore environment.
"""

# Import the Copernicus Marine API toolbox:
import copernicusmarine

# Define filepath to credentials:
credentials_fpath = ".../copernicusmarine-credentials"
# Define output directory:
out_fdir = "/dssgfs01/scratch/otooth/npd_data/observations/ARMOR3D/"

# Download the ARMOR3D analysis dataset for North Atlantic subdomain:
for year in range(2001, 2025):
  print(f"In Progress: Downloading ARMOR3D analysis dataset for: {year}...")
  copernicusmarine.subset(
    dataset_id="cmems_obs-mob_glo_phy_my_0.125deg_P1M-m",
    variables=["mlotst", "so", "to", "ugo", "vgo", "zo"],
      start_datetime=f"{year}-01-01T00:00:00",
      end_datetime=f"{year}-12-01T00:00:00",
      credentials_file=credentials_fpath,
      output_directory=out_fdir,
      file_format="zarr",
      output_filename=f"armor-3d_rep_monthly_NA_{year}.zarr",
  )
  print(f"Completed: downloading ARMOR3D analysis dataset for: {year}.")
