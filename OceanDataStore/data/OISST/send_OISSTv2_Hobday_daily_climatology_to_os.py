# =========================================================
# send_OISSTv2_Hobday_daily_climatology_to_os.py
#
# Script to write OISSTv2.1 Hobday daily climatologies
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


def cyclic_moving_average(da: xr.DataArray,
                          dim: str = "clim_day",
                          window: int=31
                          ) -> xr.DataArray:
    """
    Compute a cyclic moving average of a DataArray using a
    rolling mean with cyclic padding along dimension 'clim_day'.

    Default window size is 31-day window (±15 days) for
    daily climatology smoothing following Hobday et al. (2016)
    methodology.

    Parameters
    ----------
    da : xr.DataArray
        Input DataArray to be smoothed.
    dim : str, optional
        Dimension along which to compute the moving average.
        Default is 'day'.
    window : int, optional
        Window size for the moving average. Default is 31.

    Returns
    -------
    xr.DataArray
        Smoothed DataArray with the same dimensions as the input.
    """
    # Define padding size -> half window size:
    pad = window // 2

    # Define extended DataArray with cyclic padding:
    extended = xr.concat(
        [
            da.isel({dim: slice(-pad, None)}),
            da,
            da.isel({dim: slice(0, pad)}),
        ],
        dim=dim,
    )

    # Define smoothed DataArray using rolling mean with cyclic padding:
    smoothed = (
        extended
        .rolling({dim: window}, center=True)
        .mean()
        .isel({dim: slice(pad, -pad)})
    )

    smoothed[dim] = da[dim]

    return smoothed


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
    start_yr = 1996
    end_yr = 2025
    
    logger.info(msg=f"In Progress: Sending OISSTv2.1 Hobday daily climatology for {start_yr}-{end_yr} to Icechunk...")
    # Open OISSTv2.1 dataset:
    filepath = f"/dssgfs01/scratch/otooth/npd_data/observations/OISST/climatology/oisstv2_hobday_sst_climatology_{start_yr}-{end_yr}.zarr"
    ds = xr.open_dataset(filename_or_obj=filepath, engine='zarr')

    # Open OISSTv2 land-sea mask dataset:
    ds_mask = xr.open_dataset(filename_or_obj="http://psl.noaa.gov/thredds/dodsC/Datasets/noaa.oisst.v2.highres/lsmask.oisst.nc", decode_times=False)
    ds_mask = ds_mask.squeeze(drop=True).rename({"lon": "longitude", "lat": "latitude", "lsmask": "mask"})
    ds_mask = ds_mask.assign_coords(
        longitude=((ds_mask["longitude"] + 180) % 360) - 180
    )

    # Standardise coordinate dimension names:
    ds = ds.rename(name_dict={"lon": "longitude", "lat": "latitude"})

    # Update longitude coordinates to be in the range [-180, 180]:
    ds = ds.assign_coords(
        longitude=((ds["longitude"] + 180) % 360) - 180
    )
    ds = ds.sortby("longitude")

    # Add day of year coordinate (1-366):
    ds = ds.assign_coords(
        day=np.arange(1, 367)
    )

    # Add OISSTv2 land mask:
    ds["mask"] = ds_mask["mask"]
    ds["mask"].attrs.clear()
    ds["mask"] = ds["mask"].assign_attrs({'long_name': "Land-Sea Binary Mask",
                                          "standard_name": "sea_binary_mask",
                                          "comment": "1 = sea, 0 = land"
                                          })

    # Add horizontal grid cell area:
    ds['dx'] = compute_dx(ds)
    ds['dy'] = compute_dy(ds)
    ds['cell_area'] = compute_cell_area(ds)

    # Update time bounds to reflect climatological period:
    ds['time_bnds'] = xr.DataArray(
        np.zeros(shape=(ds['clim_day'].size, 2), dtype='datetime64[ns]'),
        dims=('clim_day', 'bnds'),
        coords={'clim_day': ds['clim_day']},
    )
    ds['time_bnds'].data[:, 0] = (np.datetime64(f'{start_yr}-01-01', 'D') + (np.timedelta64(1, 'D') * np.arange(ds['clim_day'].size))).astype('datetime64[ns]')
    ds['time_bnds'].data[:, 1] = (np.datetime64(f'{end_yr}-01-01', 'D') + (np.timedelta64(1, 'D') * np.arange(ds['clim_day'].size))).astype('datetime64[ns]')

    # Update variable names, units, and attributes:
    if "quantile" in ds.coords:
        ds = ds.drop_vars(names=["quantile"])

    # Add 31-day moving average smoothed variables:
    ds["tos_mean_ma"] = cyclic_moving_average(da=ds["tos_mean"], window=31)
    ds["tos_p10_ma"] = cyclic_moving_average(da=ds["tos_p10"], window=31)
    ds["tos_p90_ma"] = cyclic_moving_average(da=ds["tos_p90"], window=31)

    # Update variable long names:
    ds["tos_mean"].attrs["long_name"] = "Daily Mean Sea Surface Temperature Climatology"
    ds["tos_p10"].attrs["long_name"] = "Daily 10th Percentile Sea Surface Temperature Climatology"
    ds["tos_p90"].attrs["long_name"] = "Daily 90th Percentile Sea Surface Temperature Climatology"
    ds["tos_mean_ma"].attrs["long_name"] = "31-Day Moving Average of Daily Mean Sea Surface Temperature Climatology"
    ds["tos_p10_ma"].attrs["long_name"] = "31-Day Moving Average of Daily 10th Percentile Sea Surface Temperature Climatology"
    ds["tos_p90_ma"].attrs["long_name"] = "31-Day Moving Average of Daily 90th Percentile Sea Surface Temperature Climatology"

    # Update global attributes:
    ds.attrs.clear()
    ds = ds.assign_attrs({
        "Conventions": "CF-1.5",
        "title": f"NOAA OISSTv2.1 Daily Climatology ({start_yr}-{end_yr})",
        "description": f"NOAA 1/4° Daily Optimum Interpolation Sea Surface Temperature (OISST) version 2.1 daily sea surface temperature climatology ({start_yr}-{end_yr}). Climatology is defined following Hobday et al. (2016) methodology, where a ± 5-day pooling is used to calculate daily climatological mean and percentiles.",
        "source": "Numerical models: Optimal Interpolation. In-situ observations: ICOADS-D R3.0.2, Argo GDAC. Satellite observations: Advanced Very High Resolution Radiometer (AVHRR).",
        "dataset_type": "observation",
        "product_type": "climatology",
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
        "aggregation": "mean, 10th percentile, 90th percentile",
        "aggregation_frequency": "daily",
        "status": "completed",
        "update_frequency": "None",
        "bbox": "[-180.0, 180.0, -90.0, 90.0]",
    })

    # Optimise chunk sizes for spatial analysis:
    ds = ds.chunk({'clim_day': 5, 'latitude': 720, 'longitude': 1440})

    # Update variable encodings:
    blosccodec = zarr.codecs.BloscCodec(cname="zstd", clevel=3, shuffle="shuffle")
    for var in list(ds.data_vars) + list(ds.coords):
        ds[var].encoding['compressors'] = [blosccodec]

    # Define prefix and commit message based on climatology period:
    prefix = f"oisst_v2.1_{start_yr}_{end_yr}_hobday_daily_climatology"
    commit_message = f"Added OISSTv2.1 Hobday Daily Sea Surface Temperature Climatology ({start_yr}-{end_yr})."

    # Dask LocalCluster configuration:
    config_kwargs = {
            "temporary_directory":"/dssgfs01/working/otooth/Software/OceanDataStore/OceanDataStore/data/OISST/",
            "local_directory":"/dssgfs01/working/otooth/Software/OceanDataStore/OceanDataStore/data/OISST/"
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
        append_dim='clim_day',
        branch=branch,
        commit_message=commit_message,
        variable_commits=variable_commits,
        dask_config_kwargs=config_kwargs,
        dask_cluster_kwargs=cluster_kwargs,
        )

if __name__ == "__main__":
    main()
