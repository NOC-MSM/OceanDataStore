# =========================================================
# create_OISSTv2_Hobday_daily_climatology.py
#
# Script to calculate daily mean and quantile climatology
# for OISSTv2 Hobday sea surface temperature data.
#
# Created By: Oliver Tooth (oliver.tooth@noc.ac.uk)
# =========================================================
import argparse
import glob
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


def main(
    start_year: int,
    end_year: int,
    data_path: str="/dssgfs01/scratch/otooth/npd_data/observations/OISST/daily",
    output: str="oisstv2_hobday_daily_climatology.zarr"
    ) -> None:
    # ========== Initialise OceanDataStore Logging ========== #
    initialise_logging()

    # ========== Initialise Dask Client ========== #
    client = Client(n_workers=20, threads_per_worker=1)
    logger.info(f"Dask client initialized: {client}")

    # ========== Compute Daily Climatology from OISSTv2 Hobday Dataset ========== #
    logger.info(f"Computing OISSTv2 Hobday Daily Climatology from {start_year} to {end_year}")

    # Create list of selected files for the given year range:
    files = sorted(glob.glob(pathname=f"{data_path}/sst.day.mean.????.nc"))
    selected_files = [file for file in files if int(file[-7:-3]) >= start_year and int(file[-7:-3]) <= end_year]
    print(f"Selected files for climatology computation: {selected_files}", flush=True)

    # Open multi-file dataset:
    ds = xr.open_mfdataset(
        paths=selected_files,
        combine="by_coords",
        parallel=True,
        engine='h5netcdf',
        chunks={"time": 31, "lat": 180, "lon": 360},
        preprocess=lambda d: d['sst']
        )
    logger.info(f"Completed: Opened OISSTv2 Hobday dataset for years: {start_year} to {end_year}")

    # Add Climatological Day of Year (clim_day) coordinate to the dataset
    doy = ds['time'].dt.dayofyear
    is_leap = ds['time'].dt.is_leap_year
    after_feb28 = (~is_leap) & (doy >= 60)
    clim_day = xr.where(after_feb28, doy + 1, doy)
    ds = ds.assign_coords(clim_day=("time", clim_day.data))

    # Rename variables:
    ds = ds.rename({"sst": "tos"})

    # Compute daily climatology (day of year):
    for day in range(1, 367):
        logger.info(f"Calculating Mean, 10th and 90th percentiles for day {day}...")
        pooled = ds['tos'][ds['clim_day'].isin(pooled_days(day=day))]

        # Build output dataset
        clim = xr.Dataset()
        clim["tos_mean"] = pooled.mean(dim="time", skipna=True)
        clim["tos_p10"] = pooled.quantile(q=0.1, dim="time", skipna=True).astype(np.float32)
        clim["tos_p90"] = pooled.quantile(q=0.9, dim="time", skipna=True).astype(np.float32)
        clim = clim.expand_dims(clim_day=[day])
        logger.info(f"Completed: Created OISSTv2 Hobday Daily Climatology SST dataset for day {day}.")

        # Update variable encodings:
        blosccodec = zarr.codecs.BloscCodec(cname="zstd", clevel=3, shuffle="shuffle")
        for var in list(clim.data_vars) + list(clim.coords):
            clim[var].encoding.clear()
            clim[var].encoding['compressors'] = [blosccodec]

        # Save output
        logger.info(f"In Progress: Saving climatology to {output}...")
        if day == 1:
            clim.to_zarr(store=output, mode="w", zarr_format=3)
        else:
            clim.to_zarr(store=output, append_dim='clim_day', zarr_format=3)
        logger.info(f"Completed: Saved climatology to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute SST Daily Climatology")
    parser.add_argument("start_year", type=int, help="Start year (e.g. 2000)")
    parser.add_argument("end_year", type=int, help="End year (e.g. 2010)")
    parser.add_argument("--data_path", default=".", help="Directory containing SST files")
    parser.add_argument("--output", default="sst_climatology.zarr", help="Output file")

    args = parser.parse_args()

    main(args.start_year, args.end_year, args.data_path, args.output)
