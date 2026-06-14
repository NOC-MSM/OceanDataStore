"""
process_NSIDC_SSI_Antarctic_data.py

Description: Python script to post-process NSIDC Sea Ice Index
data for the Antarctic 1978-2025, including sea ice concentration,
extent and total area.

Created by: Ollie Tooth (oliver.tooth@noc.ac.uk)
Created on: 2025-02-21
"""
# -- Import Python packages -- #
import logging
from datetime import datetime
from glob import glob

import numpy as np
import xarray as xr

from OceanDataStore.cli import initialise_logging


# -- Define Utility Functions -- #
def get_datetimes_from_filenames(file_list):
    # Extract filenames from paths:
    filenames = [file.split('/')[-1] for file in file_list]

    # Convert filenames date str to datetime:
    datetimes = np.array([datetime(year=int(file[2:6]), month=int(file[6:8]), day=15) for file in filenames])

    return datetimes


def main():
    # ========== Initialize Logging and Print Banner ========== #
    initialise_logging()

    logging.info('In Progress: Post-Processing NSIDC Sea Ice Index Antarctic Observations...')

    # ========== Load NSIDC Ancillary Data ========== #
    # Define filepath to ancillary data:
    anc_fpath = "/dssgfs01/scratch/otooth/npd_data/observations/NSIDC/ancillary/NSIDC0771_LatLon_PS_S25km_v1.0.nc"
    # Open NSIDC ancillary data as dataset:
    ds_si = xr.open_dataset(anc_fpath)

    # Define filepath to NSIDC ancillary file - grid cell area:
    area_fpath = "/dssgfs01/scratch/otooth/npd_data/observations/NSIDC/ancillary/NSIDC0771_CellArea_PS_S25km_v1.0.nc"
    # Open NSIDC grid cell area:
    ds_area = xr.open_dataset(area_fpath)
    logging.info("-> Completed: Loaded NSIDC ancillary data and grid cell area.")

    # ========== Load NSIDC Monthly Data ========== #
    # Define directory path:
    dir_path = "/dssgfs01/scratch/otooth/npd_data/observations/NSIDC/antarctic/"

    # Get the list of files in the directory:
    file_paths = glob(f"{dir_path}*.tif")
    file_paths.sort()

    # Retrieve sea ice mask & concentration files:
    version_str = "v4.0"  # Options: "v3.0" or "v4.0"
    mask_files = [f for f in file_paths if f"extent_{version_str}.tif" in f]
    conc_files = [f for f in file_paths if f"concentration_{version_str}.tif" in f]

    # ========== Post-Process Sea Ice Mask Data ========== #
    # Define the time dimension:
    time_simask = xr.DataArray(data=get_datetimes_from_filenames(file_list=mask_files), dims='time', name='time')
    # Load and concatenate all sea ice mask GeoTIFFs:
    simask = xr.concat([xr.open_dataset(i) for i in mask_files], dim=time_simask)
    logging.info("-> Completed: Loaded NSIDC sea ice mask and concentration GeoTIFF files.")

    # Sea Ice Mask is defined by [1: sea ice, 0: ocean]:
    # Values greater than 1 (missing or land) are set to NaN:
    ds_si['simask'] = xr.where(simask['band_data'] > 1, np.nan, simask['band_data']).squeeze(drop=True)
    ds_si["simask"].attrs = {'units': '1', "long_name": "Sea Ice Mask", "standard_name": "sea_ice_mask", "comment": "1 = sea ice, 0 = ocean"}

    # ========== Post-Process Sea Ice Concentration Data ========== #
    # Define the time dimension:
    time_siconc = xr.DataArray(data=get_datetimes_from_filenames(file_list=conc_files), dims='time', name='time')
    # Load and concatenate all sea ice extent GeoTIFFs:
    siconc = xr.concat([xr.open_dataset(i) for i in conc_files], dim=time_siconc)
    logging.info("-> Completed: Loaded NSIDC sea ice concentration GeoTIFF files.")

    # Sea Ice Area Fraction:
    # Note concentration percentage is scaled by 10 -> requires division by 1000.
    # Values greater than 1 (missing or land) are set to NaN:
    ds_si['siconc'] = xr.where(siconc['band_data'] > 1000, np.nan, siconc['band_data']).squeeze(drop=True) / 1000
    ds_si['siconc'].attrs = {'units': '1', 'long_name': 'Sea Ice Area Fraction', 'standard_name': 'sea_ice_area_fraction', "comment": "0 = ocean, 0.01-0.15 = statistically insignificant, > 0.15 = sea ice"}

    # ========== Calculate sea ice area (m2) ========== #
    ds_si['cell_area'] = ds_area['cell_area']
    ds_si['cell_area'].attrs = {'units': 'm2', 'long_name': 'Grid-Cell Area for Sea Ice Variables', "standard_name": "cell_area"}

    ds_si['siextent'] = (ds_si['cell_area']*ds_si['simask']).sum(dim=['x', 'y'])
    ds_si['siextent'].attrs = {'units': 'm2', 'long_name': 'Total Area Where Sea Ice Area Fraction Exceeds 15%', 'standard_name': 'sea_ice_extent'}

    # ========== Update Coordinates ========== #
    ds_si.coords['lon'] = ds_si['longitude']
    ds_si.coords['lat'] = ds_si['latitude']
    # Drop auxiliary variables:
    ds_si = ds_si.drop_vars(["spatial_ref", "crs", "longitude", "latitude"])
    # Rename coordinates:
    ds_si = ds_si.rename({'lon': 'longitude', 'lat': 'latitude'})

    # ========== Update attributes to ensure CF-compliance: ========== #
    ds_si['x'].attrs = {'standard_name': 'projection_x_coordinate', 'long_name': 'x coordinate of projection', 'units': 'meters'}
    ds_si['y'].attrs = {'standard_name': 'projection_y_coordinate', 'long_name': 'y coordinate of projection', 'units': 'meters'}
    ds_si['longitude'].attrs = {'standard_name': 'longitude', 'long_name': 'Longitude', 'units': 'degrees_east'}
    ds_si['latitude'].attrs = {'standard_name': 'latitude', 'long_name': 'Latitude', 'units': 'degrees_north'}
    ds_si['simask'].attrs.pop("valid_range", None)

    # ========== Save NSIDC Sea Ice Index Dataset ========== #
    # Update variable encodings:
    for var in ds_si.variables:
        if ds_si[var].dtype == 'float64':
            ds_si[var].encoding['missing_value'] = None
            ds_si[var].encoding['_FillValue'] = None

    # Define output filepath:
    out_fpath = "/dssgfs01/scratch/otooth/npd_data/observations/NSIDC/NSIDC_Sea_Ice_Index_v4_Antarctic_combined_1978_2025.nc"
    # Save dataset to netCDF file:
    logging.info(f'In Progress: Saving NSIDC Sea Ice Index Antarctic Observations to netCDF file: {out_fpath}...')
    ds_si.to_netcdf(out_fpath, unlimited_dims='time')
    # Close files associated with datasets:
    ds_si.close()
    ds_area.close()

    logging.info(f'Completed: Saved NSIDC Sea Ice Index Antarctic Observations to netCDF file: {out_fpath}.')

if __name__ == "__main__":
    main()