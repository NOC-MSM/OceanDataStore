import argparse
import glob

import dask
import numpy as np
import xarray as xr
from dask.distributed import Client, LocalCluster


def main(
    year_start=1991,
    year_end=2020,
    data_path="/dssgfs01/scratch/otooth/npd_data/observations/OISST/daily/",
    output="./sst.daily.climatology.nc",
    dask_cluster_kwargs={
        "n_workers" : 8,
        "threads_per_worker" : 1,
        "memory_limit":"10GB"
        },
    dask_config_kwargs={
            "temporary_directory":"/dssgfs01/working/otooth/Software/OceanDataStore/OceanDataStore/data/OISST/",
            "local_directory":"/dssgfs01/working/otooth/Software/OceanDataStore/OceanDataStore/data/OISST/"
        }
    ):
    xr.set_options(use_flox=True)

    if dask_config_kwargs is not None:
        dask.config.set(dask_config_kwargs)

    with LocalCluster(**dask_cluster_kwargs) as cluster, Client(cluster) as client:
        print(f"Created LocalCluster with {dask_cluster_kwargs['n_workers']} workers @ Client: {client.dashboard_link}")

        # Find all SST files
        files = sorted(glob.glob(f"{data_path}/sst.day.mean.????.nc"))
        selected_files = [file for file in files if int(file[-7:-3]) >= year_start and int(file[-7:-3]) <= year_end]
        print(f"Selected files for climatology computation: {selected_files}", flush=True)

        # Open multiple files
        ds = xr.open_mfdataset(selected_files, combine="by_coords",
                            parallel=True, engine='h5netcdf',
                            chunks={"time": 31, "latitude": 720, "longitude": 360},
                            preprocess=lambda ds: ds['sst']
                            )

        # Compute daily climatology (day of year)
        ds = ds.chunk({
            "time": -1,
            "lat": 100,
            "lon": 100,
        })
        g_sst = ds["sst"].groupby("time.dayofyear")   # Group once for readability

        mean = g_sst.mean("time")
        mean = mean.persist()

        p10 = g_sst.quantile(0.10, dim="time")
        p10 = p10.persist()

        p90 = g_sst.quantile(0.90, dim="time")
        p90 = p90.persist()

        # Build output dataset
        clim = xr.Dataset()
        clim["sst_mean"] = mean
        clim["sst_p10"] = p10.astype(np.float32)
        clim["sst_p90"] = p90.astype(np.float32)

        # Save output
        print(f"In Progress: Saving Climatology to {output}")
        clim.to_netcdf(output, engine='h5netcdf', mode='w')
        print(f"Completed: Climatology saved to {output}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute OISST v2.1 SST Daily Climatology")
    parser.add_argument("--year_start", type=int, default=1996, help="Start year for climatology")
    parser.add_argument("--year_end", type=int, default=2025, help="End year for climatology")
    parser.add_argument("--data_path", default="/dssgfs01/scratch/otooth/npd_data/observations/OISST/daily", help="Directory containing SST files")
    parser.add_argument("--output", default="./sst.daily.climatology.nc", help="Output file")

    args = parser.parse_args()

    main(args.year_start, args.year_end, args.data_path, args.output)
