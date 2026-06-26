# =========================================================
# create_ERA5_daily_climatology.py
#
# Script to calculate daily mean, minimum, maximum, and
# variance for ERA5 sea surface temperature data.
#
# Created By: Adam Blaker (atb299@noc.ac.uk)
# =========================================================
import numpy as np
import xarray as xr
import glob
import argparse
import re
from dask.distributed import Client

def extract_year(filename):
    """Extract year from filename like sst_y2011m07.nc"""
    match = re.search(r"y(\d{4})m\d{2}", filename)
    return int(match.group(1)) if match else None

def preprocess(ds):
    if "valid_time" in ds.dims:
        ds = ds.rename({"valid_time": "time"})
    return ds

def main(start_year, end_year, data_path="./", output="sst_climatology.nc"):

    client = Client(n_workers=16, threads_per_worker=1)
    print(client, flush=True)

    # Find all SST files
    files = sorted(glob.glob(f"{data_path}/sst_y????m??_daily.nc"))

    # print("Files: ", files)

    # Filter files by year
    selected_files = [
        f for f in files
        if extract_year(f) is not None and start_year <= extract_year(f) <= end_year
    ]

    if not selected_files:
        raise ValueError("No files found in the specified year range.")

    print(f"Using {len(selected_files)} files from {start_year} to {end_year}")

    # Open multiple files
    ds = xr.open_mfdataset(selected_files, preprocess=preprocess, combine="by_coords", parallel=True, chunks={"time": 31, "latitude": 721, "longitude": 360})
    # print("New chunks:", ds["sst"].chunks, flush=True)

    ds = ds.chunk({
        "time": -1,
        "latitude": 100,
        "longitude": 100
    })

    # Compute daily climatology (day of year)
    g_sst = ds["sst"].groupby("time.dayofyear")   # Group once for readability

    mean = g_sst.mean("time")
    mean = mean.persist()

    var = g_sst.var("time")
    var = var.persist()

    p10 = g_sst.quantile(0.10, dim="time")
    p10 = p10.persist()

    p90 = g_sst.quantile(0.90, dim="time")
    p90 = p90.persist()

    minimum = g_sst.min("time")
    minimum = minimum.persist()

    maximum = g_sst.max("time")
    maximum = maximum.persist()

    # Build output dataset
    clim = xr.Dataset()
    
    clim["sst_mean"]        = mean
    clim["sst_variance"]    = var
    clim["sst_p10"]         = p10.astype(np.float32)
    clim["sst_p90"]         = p90.astype(np.float32)
    clim["sst_minimum"]     = minimum
    clim["sst_maximum"]     = maximum


    clim = clim.chunk({
        "dayofyear": 30,
        "latitude": 721,
        "longitude": 1440
    })

    # Save output
    clim.to_netcdf(output)

    print(f"Climatology saved to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute SST daily climatology")
    parser.add_argument("start_year", type=int, help="Start year (e.g. 2000)")
    parser.add_argument("end_year", type=int, help="End year (e.g. 2010)")
    parser.add_argument("--data_path", default=".", help="Directory containing SST files")
    parser.add_argument("--output", default="sst_climatology.nc", help="Output file")

    args = parser.parse_args()

    main(args.start_year, args.end_year, args.data_path, args.output)
