# =========================================================
# create_EN4.2.2_analysis_g10_climatology.py
#
# Script to create EN.4.2.2 analyses climatologies for
# climate normals (1971-2000, 1981-2010, 1991-2020) and
# write to local netCDF files.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# =========================================================
import logging

import numpy as np
import xarray as xr
import zarr

from OceanDataStore.cli import initialise_logging
from OceanDataStore.data.utils import (
    compute_cell_area,
    compute_dx,
    compute_dy,
    compute_land_sea_mask,
)

logger = logging.getLogger(__name__)

def main():
    # ========== Initialize Logging and Print Banner ========== #
    initialise_logging()

    # ========== Prepare Data ========== #
    # Open complete EN.4.2.2 analysis dataset:
    filepath = "/dssgfs01/scratch/otooth/npd_data/observations/EN.4.2.2/EN.4.2.2.f.analysis.g10.*.nc"
    ds = xr.open_mfdataset(filepath, combine="by_coords", data_vars="all", engine="netcdf4")
    logging.info("-> Completed: Opened EN.4.2.2 analysis dataset from netCDF files.")

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
        "title": "EN.4.2.2 ocean temperature and salinity monthly climatology.",
        "description": "EN.4.2.2 quality controlled ocean temperature and salinity monthly climatology from objective analyses with uncertainty estimates using Gouretski and Reseghetti (2010) corrections.",
        "source": "Numerical models: Objective Analysis. In-situ observations: Argo, Arctic Synoptic Basin-wide Oceanography (ASBO) project, Global Temperature and Salinity Profile Programme (GTSPP), and World Ocean Database 2018 (WOD18).",
        "dataset_type": "observation",
        "product_type": "climatology",
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
        "status": "completed",
        "update_frequency": "None",
        "bbox": "[-180.0, 180.0, -90.0, 90.0]",
    })

    logging.info("-> Completed: Updated EN.4.2.2 analysis CF-metadata.")

    # -- Calculate climate normal monthly climatologies -- #
    output_dir = "/dssgfs01/scratch/otooth/npd_data/observations/EN.4.2.2/climatology/"
    start_years = [1971, 1981, 1991]
    end_years = [2000, 2010, 2020]

    for start_year, end_year in zip(start_years, end_years):
        logging.info(f"In Progress: Calculating monthly climatology for {start_year}-{end_year} climate normal period...")
        # Calculate monthly climatology for the specified period:
        ds_climatology = ds.sel(time=slice(f'{start_year}-01', f'{end_year}-12')).groupby('time.month').mean()

        # Add ancillary variables:
        ds_climatology['mask'] = compute_land_sea_mask(ds['thetao'].isel(time=0, depth=0))
        ds_climatology['dx'] = compute_dx(ds)
        ds_climatology['dy'] = compute_dy(ds)
        ds_climatology['cell_area'] = compute_cell_area(ds)
        # Custom ancillary variables:
        ds_climatology['cell_thickness'] = (ds_climatology['depth_bnds'].isel(bnds=1) - ds_climatology['depth_bnds'].isel(bnds=0)).isel(month=0)
        ds_climatology['cell_volume'] = ds_climatology['cell_thickness'] * ds_climatology['cell_area']

        # Update attributes for custom ancillary variables:
        ds_climatology['cell_thickness'].attrs.update({
            'long_name': "Grid-Cell Thickness",
            'standard_name': "cell_thickness",
            'units': "m",
        })
        ds_climatology['cell_volume'].attrs.update({
            'long_name': "Grid-Cell Volume",
            'standard_name': "cell_volume",
            'units': "m3",
        })

        # Update time bounds to reflect climatological period:
        ds_climatology['time_bnds'][:, 0] = np.arange(f'{start_year}-01', f'{start_year+1}-01', dtype='datetime64[M]')
        ds_climatology['time_bnds'][:, 1] = np.arange(f'{end_year}-01', f'{end_year+1}-01', dtype='datetime64[M]')
        logging.info(f"-> Completed: Calculated monthly climatology for {start_year}-{end_year} climate normal period.")

        # Update title attribute to reflect climatological period:
        ds_climatology.attrs['title'] = f"EN.4.2.2 ocean temperature and salinity monthly climatology ({start_year}-{end_year})."

        ds_climatology.attrs['description'] = f"EN.4.2.2: quality controlled ocean temperature and salinity monthly climatology ({start_year}-{end_year}) from objective analyses with uncertainty estimates using Gouretski and Reseghetti (2010) corrections."

        # Update variable encodings:
        blosccodec = zarr.codecs.BloscCodec(cname="zstd", clevel=3, shuffle=zarr.codecs.BloscShuffle.shuffle)
        for var in list(ds_climatology.data_vars) + list(ds_climatology.coords):
            ds_climatology[var].encoding['compressors'] = [blosccodec]

        # Write monthly climatology to netCDF:
        output_filepath = f"{output_dir}EN.4.2.2.f.analysis.g10.{start_year}_{end_year}_monthly_climatology.nc"
        ds_climatology.to_netcdf(output_filepath)
        logging.info(f"-> Completed: Saved monthly climatology for {start_year}-{end_year} climate normal period to {output_filepath}.")

    # -- Close EN.4.2.2 analysis datasets -- #
    ds_climatology.close()
    ds.close()

if __name__ == "__main__":
    main()
