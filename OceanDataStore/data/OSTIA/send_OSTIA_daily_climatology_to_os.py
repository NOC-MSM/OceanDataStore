# =========================================================
# send_OSTIA_daily_climatology_to_os.py
#
# Script to write OSTIA North Atlantic daily climatologies
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
    bucket = "ostia"
    exists = False
    store_credentials_json = ".../credentials/jasmin_os_credentials.json"
    branch = "main"
    variable_commits = True

    # Define climatology period:
    start_yr = 1991
    end_yr = 2020
    
    logging.info(f"In Progress: Sending OSTIA daily climatology for {start_yr}-{end_yr} to Icechunk...")
    # Open OSTIA dataset:
    filepath = f"/dssgfs01/working/otooth/data/observations/OSTIA/climatology/ostia_sst_climatology_{start_yr}-{end_yr}.zarr"
    ds = xr.open_dataset(filepath, engine='zarr')

    # Update variable names, units, and attributes:
    if "quantile" in ds.coords:
        ds = ds.drop_vars(["quantile"])

    # Add 31-day moving average smoothed variables:
    ds["tos_mean_ma"] = cyclic_moving_average(ds["tos_mean"], window=31)
    ds["tos_p10_ma"] = cyclic_moving_average(ds["tos_p10"], window=31)
    ds["tos_p90_ma"] = cyclic_moving_average(ds["tos_p90"], window=31)

    # Update variable long names:
    ds["tos_mean"].attrs["long_name"] = "Daily Mean Sea Surface Temperature Climatology"
    ds["tos_p10"].attrs["long_name"] = "Daily 10th Percentile Sea Surface Temperature Climatology"
    ds["tos_p90"].attrs["long_name"] = "Daily 90th Percentile Sea Surface Temperature Climatology"
    ds["tos_mean_ma"].attrs["long_name"] = "31-Day Moving Average of Daily Mean Sea Surface Temperature Climatology"
    ds["tos_p10_ma"].attrs["long_name"] = "31-Day Moving Average of Daily 10th Percentile Sea Surface Temperature Climatology"
    ds["tos_p90_ma"].attrs["long_name"] = "31-Day Moving Average of Daily 90th Percentile Sea Surface Temperature Climatology"

    # Add ancillary variables:
    ds['dx'] = compute_dx(ds)
    ds['dy'] = compute_dy(ds)
    ds['cell_area'] = compute_cell_area(ds)

    # Update time bounds to reflect climatological period:
    ds['time_bnds'] = xr.DataArray(
        np.zeros((ds['clim_day'].size, 2), dtype='datetime64[ns]'),
        dims=('clim_day', 'bnds'),
        coords={'clim_day': ds['clim_day']},
    )
    ds['time_bnds'].data[:, 0] = (np.datetime64(f'{start_yr}-01-01', 'D') + (np.timedelta64(1, 'D') * np.arange(ds['clim_day'].size))).astype('datetime64[ns]')
    ds['time_bnds'].data[:, 1] = (np.datetime64(f'{end_yr}-01-01', 'D') + (np.timedelta64(1, 'D') * np.arange(ds['clim_day'].size))).astype('datetime64[ns]')

    # Update global attributes:
    ds.attrs.clear()
    ds = ds.assign_attrs({
        "Conventions": "CF-1.4",
        "title": f"OSTIA Reprocessed North Atlantic Daily Climatology ({start_yr}-{end_yr})",
        "description": f"The Operational Sea Surface Temperature and Ice Analysis (OSTIA) Reprocessed - North Atlantic Sea Surface Temperature Daily Climatology ({start_yr}-{end_yr}). Climatology is defined following Hobday et al. (2016) methodology, where a ± 5-day pooling is used to calculate daily climatological mean and percentiles.",
        "source": "Satellite observations: GCOM-W, AQUA, GOES<13,16>, MetoSat<08,09,10,11>, Sentinel-<3a,3b>, ERS<1,2>, Envisat, NOAA-<07,08,09,11,12,14,15,16,17,18,19,MTA>, GPM-Core, Suomi-NPP, NOAA-20.",
        "dataset_type": "observation",
        "product_type": "climatology",
        "product_version": "3.2",
        "institution": "Met Office, UK",
        "citation": "Ocean OSTIA Sea Surface Temperature and Sea Ice Analysis. E.U. Copernicus Marine Service Information (CMEMS). Marine Data Store (MDS). DOI: 10.48670/moi-00168 (Accessed on 27 06 2026).",
        "references": "Worsfold, M.; Good, S.; Atkinson, C.; Embury, O. Presenting a Long-Term, Reprocessed Dataset of Global Sea Surface Temperature Produced Using the OSTIA System. Remote Sens. 2024, 16, 3358. https://doi.org/10.3390/rs16183358",
        "acknowledgement": "Generated using E.U. Copernicus Marine Service Information; https://doi.org/10.48670/moi-00168. These data were provided by GHRSST, Met Office and CMEMS.",
        "license": "OSTIA data were obtained from https://doi.org/10.48670/moi-00168, and are provided under the Copernicus Marine Environment Monitoring Service Service Level Agreement (SLA) https://marine.copernicus.eu/user-corner/service-commitments-and-licence?pk_vid=42ac3e352be888641780994034c3bb6e",
        "doi": "10.48670/moi-00168",
        "platform": "gr",
        "horizontal_grid_type": "regular rectilinear",
        "horizontal_grid_resolution": "0.05 degree",
        "aggregation": "mean, 10th percentile, 90th percentile",
        "aggregation_frequency": "daily",
        "status": "completed",
        "update_frequency": "None",
        "bbox": "[-44.975, 13.975, 31.025, 84.975]",
    })

    # Optimise chunk sizes for spatial analysis:
    ds = ds.chunk({'clim_day': 2, 'latitude': 1080, 'longitude': 1180})

    # Update variable encodings:
    blosccodec = zarr.codecs.BloscCodec(cname="zstd", clevel=3, shuffle=zarr.codecs.BloscShuffle.shuffle)
    for var in list(ds.data_vars) + list(ds.coords):
        ds[var].encoding.clear()
        ds[var].encoding['compressors'] = [blosccodec]

    # Define prefix and commit message based on climatology period:
    prefix = f"ostia_rep_na_{start_yr}_{end_yr}_daily_climatology"
    commit_message = f"Added OSTIA SST Daily Climatology ({start_yr}-{end_yr})."

    # Dask LocalCluster configuration:
    config_kwargs = {
            "temporary_directory":"/dssgfs01/working/otooth/Software/OceanDataStore/OceanDataStore/data/",
            "local_directory":"/dssgfs01/working/otooth/Software/OceanDataStore/OceanDataStore/data/"
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
