# =========================================================
# create_ERA5_Hobday_daily_climatology.py
#
# Script to calculate daily mean and quantile climatology
# for ERA5 sea surface temperature data.
#
# Created By: Oliver Tooth (oliver.tooth@noc.ac.uk)
# =========================================================
import argparse
import logging

import numpy as np
import xarray as xr
from dask.distributed import Client

from OceanDataStore import OceanDataCatalog
from OceanDataStore.cli import initialise_logging

logger = logging.getLogger(__name__)


def pooled_days(day: int, half_width: int=5, ndays: int=366):
    """
    Return cyclic day window centred on `day`.
    """
    offsets = np.arange(-half_width, half_width + 1)
    return ((day - 1 + offsets) % ndays) + 1


def main(start_year,
         end_year,
         output="sst_climatology.zarr"
         ):
    # ========== Initialise OceanDataStore Logging ========== #
    initialise_logging()

    # ========== Initialise Dask Client ========== #
    client = Client(n_workers=30, threads_per_worker=1)
    logger.info(f"Dask client initialized: {client}")

    # ========== Compute Daily Climatology from ERA5 Dataset ========== #
    logger.info(f"Computing ERA5 Daily Climatology from {start_year} to {end_year}")

    # Open multiple files
    catalog = OceanDataCatalog(catalog_name="noc-test-stac")
    ds = catalog.open_dataset(id='era5/era5_daily_timeseries',
                              start_datetime=f"{start_year}-01",
                              end_datetime=f"{end_year}-12",
                              )
    logger.info(f"Completed: Opened ERA5 SST dataset for years: {start_year} to {end_year}")

    # Add Climatological Day of Year (clim_day) coordinate to the dataset:
    doy = ds['time'].dt.dayofyear
    is_leap = ds['time'].dt.is_leap_year
    after_feb28 = (~is_leap) & (doy >= 60)
    clim_day = xr.where(after_feb28, doy + 1, doy)
    ds = ds.assign_coords(clim_day=("time", clim_day.data))

    # Compute daily climatology (day of year):
    for day in range(119, 367):
        logger.info(f"Calculating Mean, 10th and 90th percentiles for day {day}...")
        pooled = ds['tos'][ds['clim_day'].isin(pooled_days(day=day))]

        # Build output dataset
        clim = xr.Dataset()
        clim["tos_mean"] = pooled.mean(dim="time", skipna=True)
        clim["tos_p10"] = pooled.quantile(q=0.1, dim="time", skipna=True).astype(np.float32)
        clim["tos_p90"] = pooled.quantile(q=0.9, dim="time", skipna=True).astype(np.float32)
        clim = clim.expand_dims(clim_day=[day])
        logger.info("Completed: Created ERA5 Daily Climatology SST dataset.")

        clim = clim.chunk({
            "clim_day": 1,
            "latitude": 721,
            "longitude": 1440
        })

        # Save output
        logger.info(f"In Progress: Saving climatology to {output}...")
        if day == 1:
            clim.to_zarr(store=output, mode="w", zarr_format=3)
        else:
            clim.to_zarr(store=output, append_dim="clim_day", zarr_format=3)
        logger.info(f"Completed: Saved climatology to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute SST Daily Climatology")
    parser.add_argument("start_year", type=int, help="Start year (e.g. 2000)")
    parser.add_argument("end_year", type=int, help="End year (e.g. 2010)")
    parser.add_argument("--output", default="sst_climatology.zarr", help="Output file")

    args = parser.parse_args()

    main(args.start_year, args.end_year, args.output)
