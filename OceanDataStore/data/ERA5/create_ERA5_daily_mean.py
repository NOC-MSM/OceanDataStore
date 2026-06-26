# =========================================================
# create_ERA5_daily_mean.py
#
# Script to calculate daily mean, minimum, maximum, and
# variance for ERA5 sea surface temperature data.
#
# Created By: Adam Blaker (atb299@noc.ac.uk)
# =========================================================
import logging
import xarray as xr
import numpy as np

from OceanDataStore.cli import initialise_logging

logger = logging.getLogger(__name__)


def main(filepath: str, outpath: str) -> None:
    # ========== Initialise OceanDataStore Logging ========== #
    initialise_logging()

    # ========== Calculate Daily Mean, Min, Max, and Variance ========== #
    logging.info(f"In Progress: Calculating ERA5 SST daily mean, min, max and variance for {year}-{month:02d}...")
    ds = xr.open_dataset(filepath, chunks={"time": -1, "latitude": -1, "longitude": -1})
    logging.info(f"Completed: Read ERA5 Hourly SST data from {filepath}.")

    # Experimental: see https://confluence.ecmwf.int/pages/viewpage.action?pageId=173385064
    if 'expver' in [i for i in ds.dims]:
        print(f"Dimension 'expver' present in {filepath}")
        ds = ds.reduce(np.nansum,dim='expver')

    # Catch and rename the time dimension for consistency
    if "valid_time" in ds.dims:
        ds = ds.rename({"valid_time": "time"})

    ds2 = ds.resample(time='1D').mean()

    for var in ds.data_vars:
        ds2[var+'_min'] = ds[var].resample(time='1D').min()
        ds2[var+'_max'] = ds[var].resample(time='1D').max()
        ds2[var+'_var'] = ds[var].resample(time='1D').var()

    vv = [i for i in ds2.data_vars]
    z_chunks={vv[0]: {'chunksizes': (1, 24, 24), "zlib": True, "complevel": 1},
            vv[1]: {'chunksizes': (1, 24, 24), "zlib": True, "complevel": 1},
            vv[2]: {'chunksizes': (1, 24, 24), "zlib": True, "complevel": 1},
            vv[3]: {'chunksizes': (1, 24, 24), "zlib": True, "complevel": 1}
    }

    logging.info(f"In Progress: Writing ERA5 Daily SST data to {outpath}...")
    ds2.to_netcdf(outpath, encoding=z_chunks)
    logging.info(f"Completed: ERA5 Daily SST data saved to {outpath}.")


if __name__ == "__main__":
    # ====== Inputs ====== #
    # Define year and month:
    year = 2026
    month = 6

    # Define ERA5[T] source - [original, original_latest]:
    source = "original_latest"

    # Define path to hourly ERA5 SST data and output path for daily mean, min, max, and variance:
    filepath = f"/dssgfs01/scratch/npd/forcing/ERA5/{source}/{year}/sea_surface_temperature/sea_surface_temperature_{year}-{month:02d}.nc"
    outpath = f"/dssgfs01/scratch/otooth/npd_data/observations/ERA5/daily/sst_y{year}m{month:02d}_daily.nc"

    # ====== Calculate ERA5 Daily Mean ====== #
    main(filepath, outpath)