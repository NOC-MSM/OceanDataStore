# =========================================================
# send_HadISST1_monthly_to_os.py
#
# Script to write HadISST1 monthly data to Icechunk
# repository in JASMIN cloud object storage.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# =========================================================
import logging

import numpy as np
import xarray as xr
import zarr

from OceanDataStore.cli import initialise_logging, send_to_icechunk
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
    # Open HadISST1 monthly dataset:
    filedir = "/dssgfs01/scratch/otooth/npd_data/observations/HadISST"
    ds = xr.open_dataset(f"{filedir}/HadISST_sst.nc", engine="netcdf4")
    ds_si = xr.open_dataset(f"{filedir}/HadISST_ice.nc", engine="netcdf4")

    # Add sea ice concentration to single dataset:
    ds['sic'] = ds_si['sic']

    # Rename variables to standard names:
    ds = ds.rename({"sst": "tos", "sic": "siconc"})
    # Fill missing sea surface temperature values with NaNs:
    ds['tos'] = xr.where(cond=ds['tos'] == -1000, x=np.nan, y=ds['tos'])

    # Update variable attributes:
    ds["tos"].attrs.update({
        "long_name": "Sea Surface Temperature",
    })
    ds["siconc"].attrs.update({
        "long_name": "Sea Ice Area Fraction",
    })

    # Update global attributes:
    ds.attrs.clear()

    ds = ds.assign_attrs({
        "Conventions": "CF-1.0",
        "title": "Hadley Centre Sea Ice and Sea Surface Temperature (HadISST) monthly timeseries.",
        "description": "HadISST v1.1 monthly averages of sea surface temperature and sea ice concentration.",
        "source": "Numerical models: Reduced Space Optimal Interpolation. In-situ observations: Met Office Marine Data Bank (MDB), Comprehensive Ocean-Atmosphere Data Set (COADS). Satellite observations: Advanced Very High Resolution Radiometer (AVHRR).",
        "dataset_type": "observation",
        "product_type": "timeseries",
        "product_version": "1.1",
        "institution": "Met Office, UK",
        "citation": "Rayner, N. A., Parker, D. E., Horton, E. B., Folland, C. K., Alexander, L. V., Rowell, D. P., Kent, E. C., Kaplan, A.  Global analyses of sea surface temperature, sea ice, and night marine air temperature since the late nineteenth century J. Geophys. Res.Vol. 108, No. D14, 4407 10.1029/2002JD002670.",
        "references": "Rayner, N. A., Parker, D. E., Horton, E. B., Folland, C. K., Alexander, L. V., Rowell, D. P., Kent, E. C., Kaplan, A.  Global analyses of sea surface temperature, sea ice, and night marine air temperature since the late nineteenth century J. Geophys. Res.Vol. 108, No. D14, 4407 10.1029/2002JD002670.",
        "acknowledgement": "None",
        "license": "HadISST1.1 data were obtained from https://www.metoffice.gov.uk/hadobs/hadisst/ and are © Crown Copyright, Met Office, [2026], provided under a Non-Commercial Government Licence http://www.nationalarchives.gov.uk/doc/non-commercial-government-licence/version/2/.",
        "doi": "None",
        "platform": "gr",
        "horizontal_grid_type": "regular rectilinear",
        "horizontal_grid_resolution": "1 degree",
        "aggregation": "mean",
        "aggregation_frequency": "monthly",
        "status": "ongoing",
        "update_frequency": "quarterly",
        "bbox": "[-180.0, 180.0, -90.0, 90.0]",
    })

    # Add ancillary variables:
    ds['mask'] = compute_land_sea_mask(ds['tos'].isel(time=0))
    ds['dx'] = compute_dx(ds)
    ds['dy'] = compute_dy(ds)
    ds['cell_area'] = compute_cell_area(ds)

    # Add Northern and Southern Hemisphere sea ice area timeseries:
    ds['siarea_NH'] = (ds['siconc'].where(ds['latitude'] > 0) * ds['cell_area']).sum(dim=['latitude', 'longitude'])
    ds['siarea_NH'].attrs = {'long_name': 'Total Northern Hemisphere Sea Ice Area', 'standard_name': 'sea_ice_area', 'units': 'm2'}

    ds['siarea_SH'] = (ds['siconc'].where(ds['latitude'] < 0) * ds['cell_area']).sum(dim=['latitude', 'longitude'])
    ds['siarea_SH'].attrs = {'long_name': 'Total Southern Hemisphere Sea Ice Area', 'standard_name': 'sea_ice_area', 'units': 'm2'}

    # ========== Send to Icechunk Repository ========== #
    bucket = "hadisst"
    prefix = "hadisst_v1.1_monthly"
    exists = False
    store_credentials_json = ".../credentials/jasmin_os_credentials.json"
    branch = "main"
    commit_message = "Added HadISST1 sea surface temperature and sea ice concentration monthly (1870-01-2026-04)."
    variable_commits = True
    config_kwargs = {
            "temporary_directory":"/dssgfs01/working/otooth/Software/OceanDataStore/OceanDataStore/data/HadISST/",
            "local_directory":"/dssgfs01/working/otooth/Software/OceanDataStore/OceanDataStore/data/HadISST/"
        }
    cluster_kwargs = {
            "n_workers" : 15,
            "threads_per_worker" : 1,
            "memory_limit":"3GB"
        }
    
    # Optimise chunk sizes for spatial analysis:
    ds = ds.chunk({'time': 30, 'latitude': 180, 'longitude': 360})

    # Update variable encodings:
    blosccodec = zarr.codecs.BloscCodec(cname="zstd", clevel=3, shuffle=zarr.codecs.BloscShuffle.shuffle)
    for var in list(ds.data_vars) + list(ds.coords):
        ds[var].encoding['compressors'] = [blosccodec]

    send_to_icechunk(
        file=ds,
        bucket=bucket,
        object_prefix=prefix,
        store_credentials_json=store_credentials_json,
        exists=exists,
        append_dim='time',
        branch=branch,
        commit_message=commit_message,
        variable_commits=variable_commits,
        dask_config_kwargs=config_kwargs,
        dask_cluster_kwargs=cluster_kwargs,
        )

if __name__ == "__main__":
    main()
