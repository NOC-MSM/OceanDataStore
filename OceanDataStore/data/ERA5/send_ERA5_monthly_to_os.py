# =========================================================
# send_ERA5_monthly_to_os.py
#
# Script to write ERA5 monthly data to Icechunk repositories
# in JASMIN cloud object storage.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# =========================================================
import logging

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
    
    logging.info("In Progress: Sending ERA5 monthly data to Icechunk...")
    # Open ERA5 dataset:
    filepath = "/dssgfs01/scratch/otooth/npd_data/observations/ERA5/monthly/sst_y198?m??_monthly.nc"
    ds_sst = xr.open_mfdataset(filepath,
                               combine="by_coords",
                               data_vars="all",
                               engine="h5netcdf",
                               chunks={"time": -1, "latitude": -1, "longitude": -1}
                               )
    
    filepath = "/dssgfs01/scratch/otooth/npd_data/observations/ERA5/monthly/siconc_y198?m??_monthly.nc"
    ds_si = xr.open_mfdataset(filepath,
                              combine="by_coords",
                              data_vars="all",
                              engine="h5netcdf",
                              chunks={"time": -1, "latitude": -1, "longitude": -1}
                              )

    # SST: Update longitude coordinates to be in the range [-180, 180]:
    ds_sst = ds_sst.assign_coords(
        longitude=((ds_sst["longitude"] + 180) % 360) - 180
    )
    ds_sst = ds_sst.sortby("longitude")

    # SIC: Update longitude coordinates to be in the range [-180, 180]:
    ds_si = ds_si.assign_coords(
        longitude=((ds_si["longitude"] + 180) % 360) - 180
    )
    ds_si = ds_si.sortby("longitude")

    # SST: Update variable names, units, and attributes:
    if "number" in ds_sst.data_vars:
        ds_sst = ds_sst.drop_vars(["number"])
    for var in ds_sst.data_vars:
        if "sst" in var:
            # Transform units degK -> degC:
            ds_sst[var] = ds_sst[var] - 273.15
            # Add standard names and units:
            ds_sst[var].attrs["standard_name"] = "sea_surface_temperature"
            ds_sst[var].attrs["units"] = "degC"
            # Rename variables to standard names:
            ds_sst = ds_sst.rename({var: var.replace("sst", "tos")})

    # SIC: Update variable names, units, and attributes:
    if "number" in ds_si.data_vars:
        ds_si = ds_si.drop_vars(["number"])
    for var in ds_si.data_vars:
        if "siconc" in var:
            # Add standard names and units:
            ds_si[var].attrs["standard_name"] = "sea_ice_area_fraction"
            ds_si[var].attrs["units"] = "1"

    # SST: Update variable long names:
    ds_sst["tos"].attrs["long_name"] = "Daily Mean Sea Surface Temperature"
    ds_sst["tos_var"].attrs["long_name"] = "Daily Variance Sea Surface Temperature"
    ds_sst["tos_min"].attrs["long_name"] = "Daily Minimum Sea Surface Temperature"
    ds_sst["tos_max"].attrs["long_name"] = "Daily Maximum Sea Surface Temperature"

    # SIC: Update variable long names:
    ds_si["siconc"].attrs["long_name"] = "Daily Mean Sea Ice Area Fraction"
    ds_si["siconc_var"].attrs["long_name"] = "Daily Variance Sea Ice Area Fraction"
    ds_si["siconc_min"].attrs["long_name"] = "Daily Minimum Sea Ice Area Fraction"
    ds_si["siconc_max"].attrs["long_name"] = "Daily Maximum Sea Ice Area Fraction"

    # Merge SST and SIC datasets:
    ds = xr.merge([ds_sst, ds_si], compat="override", join="override")

    # Add ancillary variables:
    ds['mask'] = compute_land_sea_mask(ds['tos'].isel(time=0))
    ds['dx'] = compute_dx(ds)
    ds['dy'] = compute_dy(ds)
    ds['cell_area'] = compute_cell_area(ds)

    # Update global attributes:
    ds.attrs.clear()
    ds = ds.assign_attrs({
        "Conventions": "CF-1.7",
        "title": "ERA5 Sea Surface Monthly Timeseries",
        "description": "ERA5 monthly sea surface temperature and sea ice area fraction timeseries.",
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
        "aggregation_frequency": "monthly",
        "status": "completed",
        "update_frequency": "None",
        "bbox": "[-180.0, 180.0, -90.0, 90.0]",
    })

    # Optimise chunk sizes for spatial analysis:
    ds = ds.chunk({'time': 1, 'latitude': 721, 'longitude': 1440})

    # Update variable encodings:
    blosccodec = zarr.codecs.BloscCodec(cname="zstd", clevel=3, shuffle=zarr.codecs.BloscShuffle.shuffle)
    for var in list(ds.data_vars) + list(ds.coords):
        ds[var].encoding['compressors'] = [blosccodec]

    # Define prefix and commit message based on climatology period:
    prefix = "era5_monthly_timeseries"
    commit_message = "Added ERA5 Sea Surface Monthly Timeseries (1980-01-1989-12)."

    # Dask LocalCluster configuration:
    config_kwargs = {
            "temporary_directory":"/dssgfs01/working/otooth/Software/OceanDataStore/OceanDataStore/data/ERA5/",
            "local_directory":"/dssgfs01/working/otooth/Software/OceanDataStore/OceanDataStore/data/ERA5/"
        }
    cluster_kwargs = {
            "n_workers" : 25,
            "threads_per_worker" : 1,
            "memory_limit":"4GB"
        }

    send_to_icechunk(
        file=ds,
        bucket=bucket,
        object_prefix=prefix,
        store_credentials_json=store_credentials_json,
        exists=exists,
        append_dim='time',
        branch=branch,
        commit_message=commit_message,
        variable_commits=variable_commits,
        dask_config_kwargs=config_kwargs,
        dask_cluster_kwargs=cluster_kwargs,
        )

if __name__ == "__main__":
    main()
