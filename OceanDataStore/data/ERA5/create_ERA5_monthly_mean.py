# =========================================================
# create_ERA5_monthly_mean.py
#
# Script to calculate monthly mean, minimum, maximum, and
# variance for ERA5 sea surface temperature data.
#
# Created By: Adam Blaker (atb299@noc.ac.uk)
# =========================================================
import logging
import xarray as xr
import numpy as np

from OceanDataStore.cli import initialise_logging

logger = logging.getLogger(__name__)


def main(filepath: str, outpath: str, var_out: str) -> None:
    # ========== Initialise OceanDataStore Logging ========== #
    initialise_logging()

    # ========== Calculate Monthly Mean, Min, Max, and Variance ========== #
    logging.info(f"In Progress: Calculating ERA5 {var_out} monthly mean, min, max and variance for {year}-{month:02d}...")
    ds = xr.open_dataset(filepath, chunks={"time": -1, "latitude": -1, "longitude": -1})
    logging.info(f"Completed: Read ERA5 Hourly {var_out} data from {filepath}.")

    # Experimental: see https://confluence.ecmwf.int/pages/viewpage.action?pageId=173385064
    if 'expver' in [i for i in ds.dims]:
        print(f"Dimension 'expver' present in {filepath}")
        ds = ds.reduce(np.nansum,dim='expver')

    # Catch and rename the time dimension for consistency
    if "valid_time" in ds.dims:
        ds = ds.rename({"valid_time": "time"})

    ds2 = ds.resample(time='1ME').mean()

    for var in ds.data_vars:
        ds2[var+'_min'] = ds[var].resample(time='1ME').min()
        ds2[var+'_max'] = ds[var].resample(time='1ME').max()
        ds2[var+'_var'] = ds[var].resample(time='1ME').var()

    vv = [i for i in ds2.data_vars]
    z_chunks={vv[0]: {'chunksizes': (1, 24, 24), "zlib": True, "complevel": 1},
              vv[1]: {'chunksizes': (1, 24, 24), "zlib": True, "complevel": 1},
              vv[2]: {'chunksizes': (1, 24, 24), "zlib": True, "complevel": 1},
              vv[3]: {'chunksizes': (1, 24, 24), "zlib": True, "complevel": 1}
    }

    logging.info(f"In Progress: Writing ERA5 Monthly {var_out} data to {outpath}...")
    ds2.to_netcdf(outpath, encoding=z_chunks)
    logging.info(f"Completed: ERA5 Monthly {var_out} data saved to {outpath}.")


if __name__ == "__main__":
    # ====== Inputs ====== #
    # Define year and month:
    year = 2026
    month = 5

    # Define ERA5 variable:
    var_in = "sea_ice_cover"
    var_out = "siconc"

    # Define ERA5[T] source - [original, original_latest]:
    # source = "original"
    source = "original_latest"

    # Define path to hourly ERA5 SST data and output path for monthly mean, min, max, and variance:
    filepath = f"/dssgfs01/scratch/npd/forcing/ERA5/{source}/{year}/{var_in}/{var_in}_{year}-{month:02d}.nc"
    outpath = f"/dssgfs01/scratch/otooth/npd_data/observations/ERA5/monthly/{var_out}_y{year}m{month:02d}_monthly.nc"

    # ====== Calculate ERA5 Monthly Mean ====== #
    main(filepath, outpath, var_out)