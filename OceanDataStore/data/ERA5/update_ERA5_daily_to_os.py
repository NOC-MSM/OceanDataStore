# =========================================================
# send_ERA5_daily_to_os.py
#
# Script to write ERA5 daily data to Icechunk repositories
# in JASMIN cloud object storage.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# =========================================================
import logging
from pathlib import Path

import xarray as xr
import zarr

from OceanDataStore.cli import initialise_logging, update_icechunk
from OceanDataStore.data.utils import (
    compute_cell_area,
    compute_dx,
    compute_dy,
    compute_land_sea_mask,
)

logger = logging.getLogger(__name__)


def main():
    # ========== Initialise OceanDataStore Logging ========== #
    initialise_logging()

    # ========== Send to Icechunk Repository ========== #
    bucket = "era5"
    store_credentials_json = ".../credentials/jasmin_os_credentials.json"
    branch = "main"
    
    logging.info("In Progress: Sending ERA5 daily data to Icechunk...")
    # Open ERA5 dataset:
    filepath = []
    base = Path("/dssgfs01/scratch/otooth/npd_data/observations/ERA5/daily")
    for year in range(2026, 2027):
        filepath.extend(sorted(base.glob(f"sst_y{year}m??_daily.nc")))
    ds = xr.open_mfdataset(filepath,
                           combine="by_coords",
                           data_vars="all",
                           engine="h5netcdf",
                           chunks={"time": -1, "latitude": -1, "longitude": -1}
                           )

    # Update longitude coordinates to be in the range [-180, 180]:
    ds = ds.assign_coords(
        longitude=((ds["longitude"] + 180) % 360) - 180
    )
    ds = ds.sortby("longitude")

    # Update variable names, units, and attributes:
    if "number" in ds.data_vars:
        ds = ds.drop_vars(["number"])
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
    ds["tos"].attrs["long_name"] = "Daily Mean Sea Surface Temperature"
    ds["tos_var"].attrs["long_name"] = "Daily Variance Sea Surface Temperature"
    ds["tos_min"].attrs["long_name"] = "Daily Minimum Sea Surface Temperature"
    ds["tos_max"].attrs["long_name"] = "Daily Maximum Sea Surface Temperature"

    # Add ancillary variables:
    ds['mask'] = compute_land_sea_mask(ds['tos'].isel(time=0))
    ds['dx'] = compute_dx(ds)
    ds['dy'] = compute_dy(ds)
    ds['cell_area'] = compute_cell_area(ds)

    # Update global attributes:
    ds.attrs.clear()
    ds = ds.assign_attrs({
        "Conventions": "CF-1.7",
        "title": "ERA5 Sea Surface Daily Timeseries",
        "description": "ERA5 daily sea surface temperature timeseries.",
        "source": "Numerical models: IFS Cy41r2 and 4D-Var data assimilation with prescribed sea surface temperature and sea ice concentration. Satellite observations: HadISST2.1.1.0, OSTIA, OSI SAF.",
        "dataset_type": "reanalysis",
        "product_type": "timeseries",
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
        "aggregation": "mean, variance, min, max",
        "aggregation_frequency": "daily",
        "status": "completed",
        "update_frequency": "None",
        "bbox": "[-180.0, 180.0, -90.0, 90.0]",
    })

    # Optimise chunk sizes for time-series analysis:
    ds = ds.chunk({'time': ds['time'].size, 'latitude': 50, 'longitude': 50})

    # Update variable encodings:
    blosccodec = zarr.codecs.BloscCodec(cname="zstd", clevel=3, shuffle=zarr.codecs.BloscShuffle.shuffle)
    for var in list(ds.data_vars) + list(ds.coords):
        ds[var].encoding['compressors'] = [blosccodec]

    # Define prefix and commit message based on climatology period:
    prefix = "era5_daily_timeseries"
    commit_message = "Added ERA5 Sea Surface Daily Timeseries (2026-01-2026-06)."

    # Dask LocalCluster configuration:
    config_kwargs = {
            "temporary_directory":"/dssgfs01/working/otooth/Software/OceanDataStore/OceanDataStore/data/ERA5/",
            "local_directory":"/dssgfs01/working/otooth/Software/OceanDataStore/OceanDataStore/data/ERA5/"
        }
    cluster_kwargs = {
            "n_workers" : 20,
            "threads_per_worker" : 1,
            "memory_limit":"5GB"
        }

    update_icechunk(
        file=ds,
        bucket=bucket,
        object_prefix=prefix,
        store_credentials_json=store_credentials_json,
        append_dim='time',
        branch=branch,
        commit_message=commit_message,
        dask_config_kwargs=config_kwargs,
        dask_cluster_kwargs=cluster_kwargs,
        )

if __name__ == "__main__":
    main()
