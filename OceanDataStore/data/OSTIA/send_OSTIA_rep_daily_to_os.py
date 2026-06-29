# =========================================================
# send_OSTIA_rep_daily_to_os.py
#
# Script to write OSTIA reprocessed daily data to Icechunk
# repositories in JASMIN cloud object storage.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# =========================================================
import logging

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
    bucket = "ostia"
    exists = False
    store_credentials_json = ".../credentials/jasmin_os_credentials.json"
    branch = "main"
    variable_commits = True
    
    logging.info("In Progress: Sending OSTIA daily data to Icechunk...")
    # Open OSTIA dataset:
    data_path = "/dssgfs01/working/otooth/data/observations/OSTIA"
    ds = xr.open_mfdataset([f"{data_path}/ostia_global_sst_daily_NA_1981_1989.zarr",
                            f"{data_path}/ostia_global_sst_daily_NA_1990_1999.zarr",
                            f"{data_path}/ostia_global_sst_daily_NA_2000_2025.zarr"],
                            engine="zarr",
                            parallel=True
                            )


    # Update variable units and attributes:
    for var in ds.data_vars:
        if "sst" in var:
            # Transform units degK -> degC:
            ds[var] = ds[var] - 273.15
            ds[var].attrs["units"] = "degC"

    # Rename variables:
    ds = ds.rename({"analysed_sst": "tos",
                    "analysis_error": "tos_error",
                    "sea_ice_fraction": "siconc",
                    })

    # Update variable long names:
    ds["tos"].attrs["long_name"] = "Daily Mean Sea Surface Temperature"
    ds["tos_error"].attrs["long_name"] = "Daily Standard Deviation Error Sea Surface Temperature"
    ds["siconc"].attrs["long_name"] = "Daily Sea Ice Area Fraction"

    # Add climatological day coordinate:
    doy = ds['time'].dt.dayofyear
    is_leap = ds['time'].dt.is_leap_year
    after_feb28 = (~is_leap) & (doy >= 60)
    clim_day = xr.where(after_feb28, doy + 1, doy)
    ds = ds.assign_coords(clim_day=("time", clim_day.data))
    ds["clim_day"].attrs["long_name"] = "Climatological Day of Year"
    ds["clim_day"].attrs["description"] = "Climatological calendar day of year (1-366) with leap-year alignment for daily climatology calculations."

    # Add ancillary variables:
    ds['dx'] = compute_dx(ds)
    ds['dy'] = compute_dy(ds)
    ds['cell_area'] = compute_cell_area(ds)

    # Update global attributes:
    ds.attrs.clear()
    ds = ds.assign_attrs({
        "Conventions": "CF-1.4",
        "title": "OSTIA Reprocessed North Atlantic Daily Timeseries",
        "description": "The Operational Sea Surface Temperature and Ice Analysis (OSTIA) Reprocessed - North Atlantic Sea Surface Temperature & Sea Ice Area Fraction Daily Timeseries.",
        "source": "Satellite observations: GCOM-W, AQUA, GOES<13,16>, MetoSat<08,09,10,11>, Sentinel-<3a,3b>, ERS<1,2>, Envisat, NOAA-<07,08,09,11,12,14,15,16,17,18,19,MTA>, GPM-Core, Suomi-NPP, NOAA-20.",
        "dataset_type": "observation",
        "product_type": "timeseries",
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
        "aggregation": "mean",
        "aggregation_frequency": "daily",
        "status": "ongoing",
        "update_frequency": "biannually",
        "bbox": "[-44.975, 13.975, 31.025, 84.975]",
    })

    # Optimise chunk sizes for time-series analysis:
    # ds = ds.chunk({'time': 3660, 'latitude': 50, 'longitude': 50})
    ds = ds.chunk({'time': 2, 'latitude': 1080, 'longitude': 1180})

    # Update variable encodings:
    blosccodec = zarr.codecs.BloscCodec(cname="zstd", clevel=3, shuffle=zarr.codecs.BloscShuffle.shuffle)
    for var in list(ds.data_vars) + list(ds.coords):
        ds[var].encoding.clear()
        ds[var].encoding['compressors'] = [blosccodec]

    # Define prefix and commit message based on timeseries period:
    # prefix = "ostia_rep_na_daily_timeseries"
    prefix = "ostia_rep_na_daily_spatial"
    commit_message = "Added OSTIA Reprocessed North Atlantic Daily Timeseries (1981-10-01 - 2025-12-18)."

    # Dask LocalCluster configuration:
    config_kwargs = {
            "temporary_directory":"/dssgfs01/working/otooth/Software/OceanDataStore/OceanDataStore/data/",
            "local_directory":"/dssgfs01/working/otooth/Software/OceanDataStore/OceanDataStore/data/"
        }
    cluster_kwargs = {
            "n_workers" : 25,
            "threads_per_worker" : 1,
            "memory_limit":"6GB"
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
