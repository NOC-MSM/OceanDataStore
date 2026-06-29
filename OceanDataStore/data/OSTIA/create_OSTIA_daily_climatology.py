# =========================================================
# create_OSTIA_daily_climatology.py
#
# Script to calculate daily mean and quantile climatology
# for OSTIA sea surface temperature data.
#
# Created By: Oliver Tooth (oliver.tooth@noc.ac.uk)
# =========================================================
import argparse
import logging

import numpy as np
import xarray as xr
import zarr
from dask.distributed import Client

from OceanDataStore.cli import initialise_logging

logger = logging.getLogger(__name__)

def pooled_days(day: int, half_width: int=5, ndays: int=366):
    """
    Return cyclic day window centred on `day`.
    """
    offsets = np.arange(-half_width, half_width + 1)
    return ((day - 1 + offsets) % ndays) + 1


def main(start_year, end_year, data_path="/dssgfs01/working/otooth/data/observations/OSTIA/", output="sst_climatology.zarr"):

    # ========== Initialise OceanDataStore Logging ========== #
    initialise_logging()

    # ========== Initialise Dask Client ========== #
    client = Client(n_workers=20, threads_per_worker=1)
    logging.info(f"Dask client initialized: {client}")

    # ========== Compute Daily Climatology from OSTIA Dataset ========== #
    logging.info(f"Computing OSTIA Daily Climatology from {start_year} to {end_year}")

    # Open multiple files
    ds_ostia_rep = xr.open_mfdataset([f"{data_path}ostia_global_sst_daily_NA_1990_1999.zarr",
                                      f"{data_path}ostia_global_sst_daily_NA_2000_2025.zarr"
                                      ], engine="zarr", parallel=True)

    ds_ostia_nrt = xr.open_dataset(f"{data_path}ostia_global_sst_daily_NA_nrt_2025_2026.zarr",
                                   engine="zarr",
                                   )
    ds_ostia_nrt = ds_ostia_nrt.sel(time=slice("2025-12-19", None))

    ds = xr.concat([ds_ostia_rep, ds_ostia_nrt], dim="time")
    ds = ds.sel(time=slice(f"{start_year}-01-01", f"{end_year}-12-31"))
    logging.info(f"Completed: Opened OSTIA dataset for years: {start_year} to {end_year}")

    ds = ds.chunk({
        "time": -1,
        "latitude": 100,
        "longitude": 100
    })

    # Add Climatological Day of Year (clim_day) coordinate to the dataset
    doy = ds['time'].dt.dayofyear
    is_leap = ds['time'].dt.is_leap_year
    after_feb28 = (~is_leap) & (doy >= 60)
    clim_day = xr.where(after_feb28, doy + 1, doy)
    ds = ds.assign_coords(clim_day=("time", clim_day.data))

    # Rename variables and transform temperature from Kelvin to Celsius
    ds = ds.rename({"analysed_sst": "tos",
                    "analysis_error": "tos_error",
                    "sea_ice_fraction": "siconc",
                    })

    ds['tos'] = ds['tos'] - 273.15  # Convert from Kelvin to Celsius
    ds['tos_error'] = ds['tos_error'] - 273.15  # Convert from Kelvin to Celsius

    # Compute daily climatology (day of year):
    for day in range(1, 367):
        logging.info(f"Calculating Mean, 10th and 90th percentiles for day {day}...")
        pooled = ds['tos'][ds['clim_day'].isin(pooled_days(day=day))]

        # Build output dataset
        clim = xr.Dataset()
        clim["tos_mean"] = pooled.mean(dim="time", skipna=True)
        clim["tos_p10"] = pooled.quantile(q=0.1, dim="time", skipna=True).astype(np.float32)
        clim["tos_p90"] = pooled.quantile(q=0.9, dim="time", skipna=True).astype(np.float32)
        clim = clim.expand_dims(clim_day=[day])
        logging.info("Completed: Created OSTIA Daily Climatology SST dataset.")

        clim = clim.chunk({
            "clim_day": 1,
            "latitude": 721,
            "longitude": 1440
        })

        # Update variable encodings:
        blosccodec = zarr.codecs.BloscCodec(cname="zstd", clevel=3, shuffle=zarr.codecs.BloscShuffle.shuffle)
        for var in list(clim.data_vars) + list(clim.coords):
            clim[var].encoding.clear()
            clim[var].encoding['compressors'] = [blosccodec]

        # Save output
        logging.info(f"In Progress: Saving climatology to {output}...")
        if day == 1:
            clim.to_zarr(store=output, mode="w", zarr_format=3)
        else:
            clim.to_zarr(store=output, append_dim='clim_day', zarr_format=3)
        logging.info(f"Completed: Saved climatology to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute SST Daily Climatology")
    parser.add_argument("start_year", type=int, help="Start year (e.g. 2000)")
    parser.add_argument("end_year", type=int, help="End year (e.g. 2010)")
    parser.add_argument("--data_path", default=".", help="Directory containing SST files")
    parser.add_argument("--output", default="sst_climatology.zarr", help="Output file")

    args = parser.parse_args()

    main(args.start_year, args.end_year, args.data_path, args.output)
