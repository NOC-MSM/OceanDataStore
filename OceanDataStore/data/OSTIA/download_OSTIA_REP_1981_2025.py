"""
Download North Atlantic subdomain of OSTIA Global SST dataset from Copernicus Marine.
This script downloads the monthly reprocessed files from 1981 to 2025.

Subdomain is defined as: (-45 degE, 14 degE, 31 degN, 85 degN)

Created By: Ollie Tooth
Created On: 2026-06-27
Contact: oliver.tooth@noc.ac.uk

Virtual Environment: env_ods.
"""

# Import the Copernicus Marine API toolbox:
import copernicusmarine

# Define filepath to credentials:
credentials_fpath = "~/.copernicusmarine/.copernicusmarine-credentials"
# Define output directory:
out_fdir = "/dssgfs01/working/otooth/data/observations/OSTIA/"

# Define start and end years:
year_start = 2000
year_end = 2025

# Download the OSTIA Global SST dataset for North Atlantic subdomain:
print(f"In Progress: Downloading OSTIA Global SST dataset for: {year_start} to {year_end}...")
copernicusmarine.subset(
    dataset_id="METOFFICE-GLO-SST-L4-REP-OBS-SST",
    variables=["analysed_sst", "analysis_error", "mask", "sea_ice_fraction"],
    start_datetime=f"{year_start}-01-01T00:00:00",
    end_datetime=f"{year_end}-12-31T23:59:59",
    minimum_longitude=-45,
    maximum_longitude=14,
    minimum_latitude=31,
    maximum_latitude=85,
    credentials_file=credentials_fpath,
    output_directory=out_fdir,
    file_format="zarr",
    output_filename=f"ostia_global_sst_daily_NA_rep_{year_start}_{year_end}.zarr",
)
print(f"Completed: downloading OSTIA Global SST dataset for: {year_start} to {year_end}.")
