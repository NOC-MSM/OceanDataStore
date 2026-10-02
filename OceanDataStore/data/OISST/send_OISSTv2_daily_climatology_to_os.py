# =========================================================
# send_OISSTv2_daily_climatology_to_os.py
#
# Script to write OISST v2.1 long-term daily climatologies
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
    compute_cell_area,
    compute_dx,
    compute_dy,
)

logger = logging.getLogger(__name__)


def main():
    # ========== Initialise OceanDataStore Logging ========== #
    initialise_logging()

    # ========== Send to Icechunk Repository ========== #
    bucket = "oisst"
    exists = False
    store_credentials_json = ".../credentials/jasmin_os_credentials.json"
    branch = "main"
    variable_commits = True

    # Define climatology period:
    start_yr = 1991
    end_yr = 2020
    
    logger.info(f"In Progress: Sending OISSTv2.1 daily climatology for {start_yr}-{end_yr} to Icechunk...")
    # Open OISSTv2 dataset:
    filepath = f"/dssgfs01/scratch/otooth/npd_data/observations/OISST/climatology/oisst_climatology_{start_yr}-{end_yr}.nc"
    ds = xr.open_dataset(filepath, engine="h5netcdf")

    # Open OISSTv2 land-sea mask dataset:
    ds_mask = xr.open_dataset("http://psl.noaa.gov/thredds/dodsC/Datasets/noaa.oisst.v2.highres/lsmask.oisst.nc", decode_times=False)
    ds_mask = ds_mask.squeeze(drop=True).rename({"lon": "longitude", "lat": "latitude", "lsmask": "mask"})
    ds_mask = ds_mask.assign_coords(
        longitude=((ds_mask["longitude"] + 180) % 360) - 180
    )

    # Standardise coordinate dimension names:
    ds = ds.rename({"lon": "longitude", "lat": "latitude", "dayofyear": "day"})

    # Update longitude coordinates to be in the range [-180, 180]:
    ds = ds.assign_coords(
        longitude=((ds["longitude"] + 180) % 360) - 180
    )
    ds = ds.sortby("longitude")

    # Add day of year coordinate (1-366):
    ds = ds.assign_coords(
        day=np.arange(1, 367)
    )

    # Rename variables to standard names:
    ds = ds.rename({"sst_mean": "tos_mean",
                    "sst_p10": "tos_p10",
                    "sst_p90": "tos_p90",
                    })

    # Add standard names and units:
    ds["tos_mean"].attrs["long_name"] = "Daily Mean Sea Surface Temperature Climatology"
    ds["tos_p10"].attrs["long_name"] = "Daily 10th Percentile Sea Surface Temperature Climatology"
    ds["tos_p90"].attrs["long_name"] = "Daily 90th Percentile Sea Surface Temperature Climatology"

    # Add OISSTv2 land mask:
    ds["mask"] = ds_mask["mask"]
    ds["mask"].attrs.clear()
    ds["mask"] = ds["mask"].assign_attrs({'long_name': "Land-Sea Binary Mask",
                                          "standard_name": "sea_binary_mask",
                                          "comment": "1 = sea, 0 = land"
                                          })

    # Add climatological day coordinate:
    doy = ds['time'].dt.dayofyear
    is_leap = ds['time'].dt.is_leap_year
    after_feb28 = (~is_leap) & (doy >= 60)
    clim_day = xr.where(after_feb28, doy + 1, doy)
    ds = ds.assign_coords(clim_day=("time", clim_day.data))
    ds["clim_day"].attrs["long_name"] = "Climatological Day of Year"
    ds["clim_day"].attrs["description"] = "Climatological calendar day of year (1-366) with leap-year alignment for daily climatology calculations."

    # Add horizontal grid cell area:
    ds['dx'] = compute_dx(ds)
    ds['dy'] = compute_dy(ds)
    ds['cell_area'] = compute_cell_area(ds)

    # Update time bounds to reflect climatological period:
    ds['time_bnds'] = xr.DataArray(
        np.zeros((ds['day'].size, 2), dtype='datetime64[ns]'),
        dims=('day', 'bnds'),
        coords={'day': ds['day']},
    )
    ds['time_bnds'].data[:, 0] = (np.datetime64(f'{start_yr}-01', 'M') + (np.timedelta64(1, 'D') * np.arange(ds['day'].size))).astype('datetime64[ns]')
    ds['time_bnds'].data[:, 1] = (np.datetime64(f'{end_yr}-01', 'M') + (np.timedelta64(1, 'D') * np.arange(ds['day'].size))).astype('datetime64[ns]')
    ds.time_bnds.attrs.clear()

    # Update global attributes:
    ds.attrs.clear()
    ds = ds.assign_attrs({
        "Conventions": "CF-1.5",
        "title": "NOAA OISSTv2.1 Daily Timeseries",
        "description": "NOAA 1/4° Daily Optimum Interpolation Sea Surface Temperature (OISST) version 2.1 daily sea surface temperature timeseries.",
        "source": "Numerical models: Optimal Interpolation. In-situ observations: ICOADS-D R3.0.2, Argo GDAC. Satellite observations: Advanced Very High Resolution Radiometer (AVHRR).",
        "dataset_type": "observation",
        "product_type": "timeseries",
        "product_version": "2.1",
        "institution": "NOAA National Centers for Environmental Information (NCEI)",
        "citation": "Huang, B., C. Liu, V. Banzon, E. Freeman, G. Graham, B. Hankins, T. Smith, and H.-M. Zhang, 2021: Improvements of the Daily Optimum Interpolation Sea Surface Temperature (DOISST) Version 2.1, Journal of Climate, 34, 2923-2939. doi: 10.1175/JCLI-D-20-0166.1",
        "references": "Huang, B., C. Liu, V. Banzon, E. Freeman, G. Graham, B. Hankins, T. Smith, and H.-M. Zhang, 2020: Improvements of the Daily Optimum Interpolation Sea Surface Temperature (DOISST) Version 2.1, Journal of Climate, 34, 2923-2939. doi: 10.1175/JCLI-D-20-0166.1. Banzon, V., Smith, T. M., Chin, T. M., Liu, C., and Hankins, W., 2016: A long-term record of blended satellite and in situ sea-surface temperature for climate monitoring, modeling and environmental studies. Earth Syst. Sci. Data, 8, 165-176, doi:10.5194/essd-8-165-2016. Reynolds, R. W., T. M. Smith, C. Liu, D. B. Chelton, K. S. Casey, and M. G. Schlax, 2007: Daily high-resolution-blended analyses for sea surface temperature. Journal of Climate, 20, 5473-5496, doi:10.1175/JCLI-D-14-00293.1",
        "acknowledgement": "NOAA OI SST V2 High Resolution Dataset data provided by the NOAA PSL, Boulder, Colorado, USA, from their website at https://psl.noaa.gov.",
        "license": "OISST v2.1 data were obtained from https://psl.noaa.gov/data/gridded/data.noaa.oisst.v2.highres.html and are provided under a Creative Commons CC0 1.0 Universal License https://creativecommons.org/publicdomain/zero/1.0/",
        "doi": "10.1175/JCLI-D-20-0166.1",
        "platform": "gr",
        "horizontal_grid_type": "regular rectilinear",
        "horizontal_grid_resolution": "0.25 degree",
        "aggregation": "mean",
        "aggregation_frequency": "daily",
        "status": "ongoing",
        "update_frequency": "quarterly",
        "bbox": "[-180.0, 180.0, -90.0, 90.0]",
    })

    # Optimise chunk sizes for spatial analysis:
    ds = ds.chunk({'day': 5, 'latitude': 720, 'longitude': 1440})

    # Update variable encodings:
    blosccodec = zarr.codecs.BloscCodec(cname="zstd", clevel=3, shuffle=zarr.codecs.BloscShuffle.shuffle)
    for var in list(ds.data_vars) + list(ds.coords):
        ds[var].encoding['compressors'] = [blosccodec]

    # Define prefix and commit message based on climatology period:
    prefix = f"oisst_v2.1_{start_yr}_{end_yr}_daily_climatology"
    commit_message = f"Added OISSTv2.1 Sea Surface Temperature Climatology ({start_yr}-{end_yr})."

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
        dask_config_kwargs=None,
        dask_cluster_kwargs=None,
        )

if __name__ == "__main__":
    main()
