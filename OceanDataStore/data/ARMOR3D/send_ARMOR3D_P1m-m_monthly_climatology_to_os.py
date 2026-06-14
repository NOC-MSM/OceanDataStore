# =========================================================
# send_ARMOR3D_P1m-m_monthly_climatology_to_os.py
#
# Script to write ARMOR3D monthly climatologies to
# Icechunk repositories in JASMIN cloud object storage.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# =========================================================
import logging

import xarray as xr
import zarr

from OceanDataStore.cli import send_to_icechunk, initialise_logging

logger = logging.getLogger(__name__)


def main():
    # ========== Initialise OceanDataStore Logging ========== #
    initialise_logging()

    # ========== Prepare Data ========== #
    # Open ARMOR3D monthly climatology datasets:
    filepaths = [
        "/dssgfs01/scratch/otooth/npd_data/observations/ARMOR3D/climatology/ARMOR3D_global_1971_2000_monthly_climatology.zarr",
        "/dssgfs01/scratch/otooth/npd_data/observations/ARMOR3D/climatology/ARMOR3D_global_1981_2010_monthly_climatology.zarr",
        "/dssgfs01/scratch/otooth/npd_data/observations/ARMOR3D/climatology/ARMOR3D_global_1991_2020_monthly_climatology.zarr"
        ]
    
    # Define start & end years of climatology periods:
    start_years = [1971, 1981, 1991]
    end_years = [2000, 2010, 2020]

    # ========== Send to Icechunk Repository ========== #
    bucket = "armor3d"
    exists = False
    store_credentials_json = ".../credentials/jasmin_os_credentials.json"
    branch = "main"
    variable_commits = True
    config_kwargs = {
            "temporary_directory":".../OceanDataStore/OceanDataStore/data/ARMOR3D/",
            "local_directory":".../OceanDataStore/OceanDataStore/data/ARMOR3D/"
        }
    cluster_kwargs = {
            "n_workers" : 30,
            "threads_per_worker" : 1,
            "memory_limit":"3GB"
        }
    
    for filepath, start_yr, end_yr in zip(filepaths, start_years, end_years):
        # Open ARMOR3D monthly climatology dataset:
        ds = xr.open_dataset(filepath, engine='zarr')

        # Optimise chunk sizes for spatial analysis:
        for var in ds.data_vars:
            if ds[var].ndim == 4:
                ds[var] = ds[var].chunk({'month': 1, 'depth': 3, 'latitude': 689, 'longitude': 1440})
                ds[var].encoding['chunks'] = (1, 3, 689, 1440)
            elif ds[var].ndim == 3:
                if "month" in ds[var].dims:
                    ds[var] = ds[var].chunk({'month': 1, 'latitude': 1378, 'longitude': 2880})
                    ds[var].encoding['chunks'] = (1, 1378, 2880)
                elif "depth" in ds[var].dims:
                    ds[var] = ds[var].chunk({'depth': 10, 'latitude': 1378, 'longitude': 2880})
                    ds[var].encoding['chunks'] = (10, 1378, 2880)
            elif (ds[var].ndim == 2):
                if "latitude" in ds[var].dims and "longitude" in ds[var].dims:
                    ds[var] = ds[var].chunk({'latitude': 1378, 'longitude': 2880})
                    ds[var].encoding['chunks'] = (1378, 2880)
            elif ds[var].ndim == 1:
                ds[var] = ds[var].chunk({'depth': 50})
                ds[var].encoding['chunks'] = (50,)

        # Update variable encodings:
        blosccodec = zarr.codecs.BloscCodec(cname="zstd", clevel=5, shuffle=zarr.codecs.BloscShuffle.shuffle)
        for var in list(ds.data_vars) + list(ds.coords):
            ds[var].encoding['compressors'] = [blosccodec]

        # Define prefix and commit message based on climatology period:
        prefix = f"armor3d_global_my_{start_yr}_{end_yr}_monthly_climatology"
        commit_message = f"Added ARMOR3D Global monthly climatology ({start_yr}-{end_yr})."

        send_to_icechunk(
            file=ds.drop_vars("time"),
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
