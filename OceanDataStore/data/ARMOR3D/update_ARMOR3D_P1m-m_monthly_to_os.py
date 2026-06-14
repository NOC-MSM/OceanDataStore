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
    compute_dx,
    compute_dy,
    compute_cell_area,
    compute_cell_thickness,
    compute_land_sea_mask,
)

logger = logging.getLogger(__name__)


def main():
    # ========== Initialise OceanDataStore Logging ========== #
    initialise_logging()

    # ========== Prepare Data ========== #
    # Open complete ARMOR3D REP monthly climatology dataset:
    filepath = "/dssgfs01/scratch/otooth/npd_data/observations/ARMOR3D/armor-3d_rep_monthly_NA_*.zarr"
    ds = xr.open_mfdataset(filepath, compat="no_conflicts", data_vars="all", engine="zarr")
    logging.info("-> Completed: Opened ARMOR-3D REP monthly climatology dataset from Zarr stores.")

    # Rename variables to standard names:
    ds = ds.rename({"to": "thetao",
                    "so": "so",
                    })

    # Update global attributes:
    ds.attrs.clear()

    ds = ds.assign_attrs({
        "Conventions": "CF-1.0",
        "title": "Multi Observation Global Ocean 3D Temperature Salinity Height Geostrophic Current and MLD.",
        "description": "Multi Observation Global Ocean ARMOR3D multi-year reprocessed temperature salinity, sea surface height, geostrophic current and mixed layer depth monthly timeseries on 1/8 degree regular grid and 50 depth levels.",
        "source": "Numerical models: Multiple Linear Regression, Optimal Interpolation. In-situ observations: Copernicus In Situ TAC (including Argo, XBT, CTD and moorings) Copernicus Sea Level TAC, CNES-CLS22 Mean Dynamic Topography, OSTIA Sea Surface Temperature Analysis, Copernicus MOB TAC (Sea Surface Salinity), and World Ocean Atlas 2018 (WOA18).",
        "dataset_type": "observation",
        "product_type": "timeseries",
        "product_version": "2.0",
        "institution": "Copernicus Marine Service, Mercator Ocean International, France",
        "citation": "Multi Observation Global Ocean 3D Temperature Salinity Height Geostrophic Current and MLD. E.U. Copernicus Marine Service Information (CMEMS). Marine Data Store (MDS). DOI: 10.48670/moi-00052 (Accessed on 21 04 2026).",
        "references": "Guinehut S., A.-L. Dhomps, G. Larnicol and P.-Y. Le Traon, 2012: High resolution 3D temperature and salinity fields derived from in situ and satellite observations. Ocean Sci., 8(5):845-857. Mulet, S., M.-H. Rio, A. Mignot, S. Guinehut and R. Morrow, 2012: A new estimate of the global 3D geostrophic ocean circulation based on satellite data and in-situ measurements. Deep Sea Research Part II : Topical Studies in Oceanography, 77-80(0):70-81.",
        "acknowledgement": "Generated using E.U. Copernicus Marine Service Information; https://doi.org/10.48670/moi-00052.",
        "license": "ARMOR3D data were obtained from https://doi.org/10.48670/moi-00052, and are provided under the Copernicus Marine Environment Monitoring Service Service Level Agreement (SLA) https://marine.copernicus.eu/user-corner/service-commitments-and-licence?pk_vid=42ac3e352be888641780994034c3bb6e",
        "doi": "10.48670/moi-00052",
        "platform": "gr",
        "horizontal_grid_type": "regular rectilinear",
        "horizontal_grid_resolution": "0.125 degree",
        "vertical_grid_type": "z",
        "vertical_grid_coordinate": "depth",
        "vertical_grid_levels": 50,
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
    ds['cell_thickness'] = compute_cell_thickness(ds)
    ds['cell_volume'] = ds['cell_thickness'] * ds['cell_area']

    # Update attributes for custom ancillary variables:
    ds['cell_volume'].attrs.update({
        'long_name': "Grid-Cell Volume",
        'standard_name': "cell_volume",
        'units': "m3",
    })

    # ========== Send to Icechunk Repository ========== #
    bucket = "armor3d"
    store_credentials_json = ".../credentials/jasmin_os_credentials.json"
    branch = "main"
    config_kwargs = {
            "temporary_directory":".../OceanDataStore/OceanDataStore/data/ARMOR3D/",
            "local_directory":".../OceanDataStore/OceanDataStore/data/ARMOR3D/"
        }
    cluster_kwargs = {
            "n_workers" : 25,
            "threads_per_worker" : 1,
            "memory_limit":"4GB"
        }
    
    # Optimise chunk sizes for spatial analysis:
    for var in ds.data_vars:
        if ds[var].ndim == 4:
            ds[var] = ds[var].chunk({'time': 1, 'depth': 3, 'latitude': 689, 'longitude': 1440})
            ds[var].encoding['chunks'] = (1, 3, 689, 1440)
        elif ds[var].ndim == 3:
            if "time" in ds[var].dims:
                ds[var] = ds[var].chunk({'time': 1, 'latitude': 1378, 'longitude': 2880})
                ds[var].encoding['chunks'] = (1, 1378, 2880)
            elif "depth" in ds[var].dims:
                ds[var] = ds[var].chunk({'depth': 10, 'latitude': 1378, 'longitude': 2880})
                ds[var].encoding['chunks'] = (10, 1378, 2880)
        elif (ds[var].ndim == 2):
            if "latitude" in ds[var].dims and "longitude" in ds[var].dims:
                ds[var] = ds[var].chunk({'latitude': 1378, 'longitude': 2880})
                ds[var].encoding['chunks'] = (1378, 2880)
        elif ds[var].ndim == 1:
            ds[var] = ds[var].chunk({'depth': 50})
            ds[var].encoding['chunks'] = (50,)

    # Update variable encodings:
    blosccodec = zarr.codecs.BloscCodec(cname="zstd", clevel=5, shuffle=zarr.codecs.BloscShuffle.shuffle)
    for var in list(ds.data_vars) + list(ds.coords):
        ds[var].encoding['compressors'] = [blosccodec]

    # Define prefix and commit message based on period:
    prefix = "armor3d_global_my_monthly"
    commit_message = "Added ARMOR3D Global Monthly (2000-2024)."

    update_icechunk(
        file=ds.sel(time=slice("2000-01-01", "2024-12-31")),
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
