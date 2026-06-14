# =========================================================
# update_EN4.2.2_analyses_g10_to_os.py
#
# Script to update EN.4.2.2 analyses in Icechunk repository
# in JASMIN cloud object storage.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# =========================================================
import logging

import xarray as xr
import zarr

from OceanDataStore.cli import initialise_logging, update_icechunk
from OceanDataStore.data.utils import (
    compute_cell_area,
    compute_dx,
    compute_dy,
    compute_land_sea_mask,
)

logger = logging.getLogger(__name__)


def main():
    # ========== Initialise OceanDataStore Logging ========== #
    initialise_logging()

    # ========== Prepare Data ========== #
    # Open EN.4.2.2 analyses dataset:
    filepath = "/dssgfs01/scratch/otooth/npd_data/observations/EN.4.2.2/EN.4.2.2.f.analysis.g10.20*.nc"
    ds = xr.open_mfdataset(filepath, combine="by_coords", data_vars="all", engine="netcdf4")

    # Standardise coordinate dimension names:
    ds = ds.rename({"lon": "longitude", "lat": "latitude"})

    # Update longitude coordinates to be in the range [-180, 180]:
    ds = ds.assign_coords(
        longitude=((ds["longitude"] + 180) % 360) - 180
    )
    ds = ds.sortby("longitude")

    # Rename variables to standard names:
    ds = ds.rename({"temperature": "thetao",
                    "salinity": "so",
                    "temperature_uncertainty": "thetao_uncertainty",
                    "salinity_uncertainty": "so_uncertainty",
                    "temperature_observation_weights": "thetao_obs_weights",
                    "salinity_observation_weights": "so_obs_weights"
                    })
    
    # Update variable attributes:
    ds["thetao"].attrs.update({
        "long_name": "Potential Temperature",
    })
    ds["so"].attrs.update({
        "long_name": "Practical Salinity",
    })
    ds["thetao_uncertainty"].attrs.update({
        "long_name": "Potential Temperature Error Standard Deviation",
    })
    ds["so_uncertainty"].attrs.update({
        "long_name": "Practical Salinity Error Standard Deviation",
    })
    ds["thetao_obs_weights"].attrs.update({
        "long_name": "Potential Temperature Observation Weights",
    })
    ds["so_obs_weights"].attrs.update({
        "long_name": "Practical Salinity Observation Weights",
    })

    # Update global attributes:
    ds.attrs.clear()

    ds = ds.assign_attrs({
        "Conventions": "CF-1.0",
        "title": "EN.4.2.2 ocean temperature and salinity monthly timeseries.",
        "description": "EN.4.2.2 quality controlled ocean temperature and salinity monthly timeseries from objective analyses with uncertainty estimates using Gouretski and Reseghetti (2010) corrections.",
        "source": "Numerical models: Objective Analysis. In-situ observations: Argo, Arctic Synoptic Basin-wide Oceanography (ASBO) project, Global Temperature and Salinity Profile Programme (GTSPP), and World Ocean Database 2018 (WOD18).",
        "dataset_type": "observation",
        "product_type": "timeseries",
        "product_version": "1.0",
        "institution": "Met Office, UK",
        "citation": "Good, S. A., Martin, M. J., and Rayner, N. A., 2013. EN4: quality controlled ocean temperature and salinity profiles and monthly objective analyses with uncertainty estimates, Journal of Geophysical Research: Oceans, 118, 6704-6716, doi:10.1002/2013JC009067.",
        "references": "Gouretski, V., and Reseghetti, F., 2010: On depth and temperature biases in bathythermograph data: development of a new correction scheme based on analysis of a global ocean database. Deep-Sea Research I, 57, 6. doi:10.1016/j.dsr.2010.03.011.",
        "acknowledgement": "None",
        "license": "EN.4.2.2 data were obtained from https://www.metoffice.gov.uk/hadobs/en4/ and are © Crown Copyright, Met Office, [2026], provided under a Non-Commercial Government Licence http://www.nationalarchives.gov.uk/doc/non-commercial-government-licence/version/2/.",
        "doi": "None",
        "platform": "gr",
        "horizontal_grid_type": "regular rectilinear",
        "horizontal_grid_resolution": "1 degree",
        "vertical_grid_type": "z",
        "vertical_grid_coordinate": "depth",
        "vertical_grid_levels": 42,
        "aggregation": "mean",
        "aggregation_frequency": "monthly",
        "status": "ongoing",
        "update_frequency": "quarterly",
        "bbox": "[-180.0, 180.0, -90.0, 90.0]",
    })

    # Add ancillary variables:
    ds['mask'] = compute_land_sea_mask(ds['thetao'].isel(time=0, depth=0))
    ds['dx'] = compute_dx(ds)
    ds['dy'] = compute_dy(ds)
    ds['cell_area'] = compute_cell_area(ds)

    # Custom ancillary variables:
    ds['cell_thickness'] = (ds['depth_bnds'].isel(bnds=1) - ds['depth_bnds'].isel(bnds=0)).isel(time=0)
    ds['cell_volume'] = ds['cell_thickness'] * ds['cell_area']

    # Update attributes for custom ancillary variables:
    ds['cell_thickness'].attrs.update({
        'long_name': "Grid-Cell Thickness",
        'standard_name': "cell_thickness",
        'units': "m",
    })
    ds['cell_volume'].attrs.update({
        'long_name': "Grid-Cell Volume",
        'standard_name': "cell_volume",
        'units': "m3",
    })

    # ========== Send to Icechunk Repository ========== #
    bucket = "en4.2.2"
    prefix = "en4.2.2_analysis_g10_monthly"
    store_credentials_json = ".../credentials/jasmin_os_credentials.json"
    branch = "main"
    commit_message = "Added EN.4.2.2.analysis.g10 monthly (2000-01-2026-03)."
    config_kwargs = {
            "temporary_directory":".../OceanDataStore/OceanDataStore/data/EN.4.2.2/",
            "local_directory":".../OceanDataStore/OceanDataStore/data/EN.4.2.2/"
        }
    cluster_kwargs = {
            "n_workers" : 25,
            "threads_per_worker" : 1,
            "memory_limit":"3GB"
        }
    
    # Optimise chunk sizes for spatial analysis:
    ds = ds.chunk({'time': 1, 'depth': 20, 'latitude': 173, 'longitude': 360})

    # Update variable encodings:
    blosccodec = zarr.codecs.BloscCodec(cname="zstd", clevel=3, shuffle=zarr.codecs.BloscShuffle.shuffle)
    for var in list(ds.data_vars) + list(ds.coords):
        ds[var].encoding['compressors'] = [blosccodec]

    update_icechunk(
        file=ds,
        bucket=bucket,
        object_prefix=prefix,
        store_credentials_json=store_credentials_json,
        append_dim='time',
        branch=branch,
        commit_message=commit_message,
        dask_config_kwargs=config_kwargs,
        dask_cluster_kwargs=cluster_kwargs,
        )

if __name__ == "__main__":
    main()
