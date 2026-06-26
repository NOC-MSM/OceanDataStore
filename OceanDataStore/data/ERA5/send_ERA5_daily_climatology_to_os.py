# =========================================================
# send_ERA5_daily_climatology_to_os.py
#
# Script to write ERA5 long-term daily climatologies
# to Icechunk repositories in JASMIN cloud object storage.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# =========================================================
import logging

import numpy as np
import xarray as xr
import zarr

from OceanDataStore.cli import initialise_logging, send_to_icechunk
from OceanDataStore.data.utils import (
    compute_land_sea_mask,
    compute_cell_area,
    compute_dx,
    compute_dy,
)

logger = logging.getLogger(__name__)


def main():
    # ========== Initialise OceanDataStore Logging ========== #
    initialise_logging()

    # ========== Send to Icechunk Repository ========== #
    bucket = "era5"
    exists = False
    store_credentials_json = ".../credentials/jasmin_os_credentials.json"
    branch = "main"
    variable_commits = True

    # Define climatology period:
    start_yr = 1996
    end_yr = 2025
    
    logging.info(f"In Progress: Sending ERA5 daily climatology for {start_yr}-{end_yr} to Icechunk...")
    # Open ERA5 dataset:
    filepath = f"/dssgfs01/scratch/otooth/npd_data/observations/ERA5/climatology/ERA5_sst_climatology_{start_yr}-{end_yr}.nc"
    ds = xr.open_dataset(filepath)

    # Standardise coordinate dimension names:
    ds = ds.rename({"dayofyear": "day"})

    # Update longitude coordinates to be in the range [-180, 180]:
    ds = ds.assign_coords(
        longitude=((ds["longitude"] + 180) % 360) - 180
    )
    ds = ds.sortby("longitude")

    # Add day of year coordinate (1-366):
    ds = ds.assign_coords(
        day=np.arange(1, 367)
    )

    # Update variable names, units, and attributes:
    ds = ds.drop_vars(["quantile"])
    for var in ds.data_vars:
        if "sst" in var:
            # Transform units degK -> degC:
            ds[var] = ds[var] - 273.15
            # Add standard names and units:
            ds[var].attrs["standard_name"] = "sea_surface_temperature"
            ds[var].attrs["units"] = "degC"
            # Rename variables to standard names:
            ds = ds.rename({var: var.replace("sst", "tos")})

    # Update variable long names:
    ds["tos_mean"].attrs["long_name"] = "Daily Mean Sea Surface Temperature Climatology"
    ds["tos_variance"].attrs["long_name"] = "Daily Variance Sea Surface Temperature Climatology"
    ds["tos_p10"].attrs["long_name"] = "Daily 10th Percentile Sea Surface Temperature Climatology"
    ds["tos_p90"].attrs["long_name"] = "Daily 90th Percentile Sea Surface Temperature Climatology"
    ds["tos_minimum"].attrs["long_name"] = "Daily Minimum Sea Surface Temperature Climatology"
    ds["tos_maximum"].attrs["long_name"] = "Daily Maximum Sea Surface Temperature Climatology"

    # Add ancillary variables:
    ds['mask'] = compute_land_sea_mask(ds['tos_mean'].isel(day=0))
    ds['dx'] = compute_dx(ds)
    ds['dy'] = compute_dy(ds)
    ds['cell_area'] = compute_cell_area(ds)

    # Update time bounds to reflect climatological period:
    ds['time_bnds'] = xr.DataArray(
        np.zeros((ds['day'].size, 2), dtype='datetime64[ns]'),
        dims=('day', 'bnds'),
        coords={'day': ds['day']},
    )
    ds['time_bnds'].data[:, 0] = (np.datetime64(f'{start_yr}-01-01', 'D') + (np.timedelta64(1, 'D') * np.arange(ds['day'].size))).astype('datetime64[ns]')
    ds['time_bnds'].data[:, 1] = (np.datetime64(f'{end_yr}-01-01', 'D') + (np.timedelta64(1, 'D') * np.arange(ds['day'].size))).astype('datetime64[ns]')

    # Update global attributes:
    ds.attrs.clear()
    ds = ds.assign_attrs({
        "Conventions": "CF-1.7",
        "title": f"ERA-5 Daily Climatology ({start_yr}-{end_yr})",
        "description": f"ERA-5 Sea Surface Temperature Daily Climatology ({start_yr}-{end_yr}).",
        "source": "Numerical models: IFS Cy41r2 and 4D-Var data assimilation with prescribed sea surface temperature and sea ice concentration. Satellite observations: HadISST2.1.1.0, OSTIA, OSI SAF.",
        "dataset_type": "reanalysis",
        "product_type": "climatology",
        "product_version": "1.0",
        "institution": "European Centre for Medium-Range Weather Forecasts (ECMWF)",
        "citation": "Copernicus Climate Change Service, Climate Data Store, (2023): ERA5 hourly data on single levels from 1940 to present. Copernicus Climate Change Service (C3S) Climate Data Store (CDS). DOI: 10.24381/cds.adbb2d47 (Accessed on 20-05-2026).",
        "references": "Hersbach, H., Bell, B., Berrisford, P., Biavati, G., Horányi, A., Muñoz Sabater, J., Nicolas, J., Peubey, C., Radu, R., Rozum, I., Schepers, D., Simmons, A., Soci, C., Dee, D., Thépaut, J-N. (2023): ERA5 hourly data on single levels from 1940 to present. Copernicus Climate Change Service (C3S) Climate Data Store (CDS), DOI: 10.24381/cds.adbb2d47.",
        "acknowledgement": "Generated using or contains modified Copernicus Climate Change Service information . Neither the European Commission nor ECMWF is responsible for any use that may be made of the Copernicus information or data it contains.",
        "license": "ERA5 data were obtained from https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels and are provided under a Creative Commons CC-BY-4.0 License https://creativecommons.org/licenses/by/4.0/",
        "doi": "10.24381/cds.adbb2d47",
        "platform": "gr",
        "horizontal_grid_type": "regular rectilinear",
        "horizontal_grid_resolution": "31 km",
        "aggregation": "mean",
        "aggregation_frequency": "daily",
        "status": "completed",
        "update_frequency": "None",
        "bbox": "[-180.0, 180.0, -90.0, 90.0]",
    })

    # Optimise chunk sizes for spatial analysis:
    ds = ds.chunk({'day': 5, 'latitude': 721, 'longitude': 1440})

    # Update variable encodings:
    blosccodec = zarr.codecs.BloscCodec(cname="zstd", clevel=3, shuffle=zarr.codecs.BloscShuffle.shuffle)
    for var in list(ds.data_vars) + list(ds.coords):
        ds[var].encoding['compressors'] = [blosccodec]

    # Define prefix and commit message based on climatology period:
    prefix = f"era5_{start_yr}_{end_yr}_daily_climatology"
    commit_message = f"Added ERA5 SST Daily Climatology ({start_yr}-{end_yr})."

    # Dask LocalCluster configuration:
    config_kwargs = {
            "temporary_directory":"/dssgfs01/working/otooth/Software/OceanDataStore/OceanDataStore/data/ERA5/",
            "local_directory":"/dssgfs01/working/otooth/Software/OceanDataStore/OceanDataStore/data/ERA5/"
        }
    cluster_kwargs = {
            "n_workers" : 20,
            "threads_per_worker" : 1,
            "memory_limit":"2GB"
        }

    send_to_icechunk(
        file=ds,
        bucket=bucket,
        object_prefix=prefix,
        store_credentials_json=store_credentials_json,
        exists=exists,
        append_dim='day',
        branch=branch,
        commit_message=commit_message,
        variable_commits=variable_commits,
        dask_config_kwargs=config_kwargs,
        dask_cluster_kwargs=cluster_kwargs,
        )

if __name__ == "__main__":
    main()
