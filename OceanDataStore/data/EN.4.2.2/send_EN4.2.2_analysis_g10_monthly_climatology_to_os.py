# =========================================================
# send_EN4.2.2_analysis_g10_climatology_to_os.py
#
# Script to write EN.4.2.2 analysis climatologies to
# Icechunk repositories in JASMIN cloud object storage.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# =========================================================
import logging

import xarray as xr

from OceanDataStore.cli import send_to_icechunk, initialise_logging

logger = logging.getLogger(__name__)


def main():
    # ========== Initialise OceanDataStore Logging ========== #
    initialise_logging()

    # ========== Prepare Data ========== #
    # Open EN.4.2.2 analysis climatology datasets:
    filepaths = [
        "/dssgfs01/scratch/otooth/npd_data/observations/EN.4.2.2/climatology/EN.4.2.2.f.analysis.g10.1971_2000_monthly_climatology.nc",
        "/dssgfs01/scratch/otooth/npd_data/observations/EN.4.2.2/climatology/EN.4.2.2.f.analysis.g10.1981_2010_monthly_climatology.nc",
        "/dssgfs01/scratch/otooth/npd_data/observations/EN.4.2.2/climatology/EN.4.2.2.f.analysis.g10.1991_2020_monthly_climatology.nc"
        ]
    
    # Define start & end years of climatology periods:
    start_years = [1971, 1981, 1991]
    end_years = [2000, 2010, 2020]

    # ========== Send to Icechunk Repository ========== #
    bucket = "en4.2.2"
    exists = False
    store_credentials_json = ".../credentials/jasmin_os_credentials.json"
    branch = "main"
    variable_commits = True
    config_kwargs = {
            "temporary_directory":".../OceanDataStore/OceanDataStore/data/EN.4.2.2/",
            "local_directory":".../OceanDataStore/OceanDataStore/data/EN.4.2.2/"
        }
    cluster_kwargs = {
            "n_workers" : 10,
            "threads_per_worker" : 1,
            "memory_limit":"3GB"
        }
    
    for filepath, start_yr, end_yr in zip(filepaths, start_years, end_years):
        # Open EN.4.2.2 analysis climatology dataset:
        ds = xr.open_dataset(filepath, engine='netcdf4')

        # Optimise chunk sizes for spatial analysis:
        ds = ds.chunk({'month': 1, 'depth': 20, 'latitude': 173, 'longitude': 360})

        # Define prefix and commit message based on climatology period:
        prefix = f"en4.2.2_analysis_g10_{start_yr}_{end_yr}_monthly_climatology"
        commit_message = f"Added EN.4.2.2.analysis.g10 climatology ({start_yr}-{end_yr})."

        send_to_icechunk(
            file=ds,
            bucket=bucket,
            object_prefix=prefix,
            store_credentials_json=store_credentials_json,
            exists=exists,
            append_dim='month',
            branch=branch,
            commit_message=commit_message,
            variable_commits=variable_commits,
            dask_config_kwargs=config_kwargs,
            dask_cluster_kwargs=cluster_kwargs,
            )

if __name__ == "__main__":
    main()
