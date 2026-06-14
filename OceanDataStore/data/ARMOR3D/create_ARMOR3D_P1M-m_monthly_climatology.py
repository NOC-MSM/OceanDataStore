# =========================================================
# create_ARMOR3D_P1M-m_climatology.py
#
# Script to create ARMOR3D REP monthly climatologies for
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
    compute_dx,
    compute_dy,
    compute_cell_area,
    compute_cell_thickness,
    compute_land_sea_mask,
)

logger = logging.getLogger(__name__)

def main():
    # ========== Initialize Logging and Print Banner ========== #
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
        "description": "Multi Observation Global Ocean ARMOR3D multi-year reprocessed temperature salinity, sea surface height, geostrophic current and mixed layer depth climatology on 1/8 degree regular grid and 50 depth levels.",
        "source": "Numerical models: Multiple Linear Regression, Optimal Interpolation. In-situ observations: Copernicus In Situ TAC (including Argo, XBT, CTD and moorings) Copernicus Sea Level TAC, CNES-CLS22 Mean Dynamic Topography, OSTIA Sea Surface Temperature Analysis, Copernicus MOB TAC (Sea Surface Salinity), and World Ocean Atlas 2018 (WOA18).",
        "dataset_type": "observation",
        "product_type": "climatology",
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
        "status": "completed",
        "update_frequency": "None",
        "bbox": "[-180.0, 180.0, -90.0, 90.0]",
    })

    logging.info("-> Completed: Updated ARMOR3D CF-metadata.")

    # -- Calculate climate normal monthly climatologies -- #
    output_dir = "/dssgfs01/scratch/otooth/npd_data/observations/ARMOR3D/climatology/"
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
        ds_climatology['cell_thickness'] = compute_cell_thickness(ds_climatology)
        ds_climatology['cell_volume'] = ds_climatology['cell_thickness'] * ds_climatology['cell_area']

        # Update attributes for custom ancillary variables:
        ds_climatology['cell_volume'].attrs.update({
            'long_name': "Grid-Cell Volume",
            'standard_name': "cell_volume",
            'units': "m3",
        })

        # Update time bounds to reflect climatological period:
        ds_climatology['time_bnds'] = xr.DataArray(data=np.zeros((12, 2), dtype='datetime64[M]'), dims=('month', 'bnds'))
        ds_climatology['time_bnds'][:, 0] = np.arange(f'{start_year}-01', f'{start_year+1}-01', dtype='datetime64[M]')
        ds_climatology['time_bnds'][:, 1] = np.arange(f'{end_year}-01', f'{end_year+1}-01', dtype='datetime64[M]')
        logging.info(f"-> Completed: Calculated monthly climatology for {start_year}-{end_year} climate normal period.")

        # Update title attribute to reflect climatological period:
        ds_climatology.attrs['title'] = f"Multi Observation Global Ocean 3D Temperature Salinity Height Geostrophic Current and MLD monthly climatology ({start_year}-{end_year})."
        ds_climatology.attrs['start_datetime'] = f"{start_year}-01-01"
        ds_climatology.attrs['end_datetime'] = f"{end_year}-12-31"

        # Update variable encodings:
        blosccodec = zarr.codecs.BloscCodec(cname="lz4", clevel=5, shuffle=zarr.codecs.BloscShuffle.shuffle)

        # Infer variable chunk sizes (preserve source chunking):
        for var in list(ds_climatology.data_vars) + list(ds_climatology.coords):
            source_chunks = ds_climatology[var].encoding.get('chunks', None)
            ds_climatology[var].encoding.clear()
            ds_climatology[var].encoding['compressors'] = [blosccodec]
            # Cast float64 back to float32 to match source precision:
            if ds_climatology[var].dtype == np.float64:
                ds_climatology[var].encoding['dtype'] = 'float32'
            if source_chunks is not None:
                ds_climatology[var].encoding['chunks'] = source_chunks

        # Write monthly climatology to Zarr:
        output_filepath = f"{output_dir}ARMOR3D_global_{start_year}_{end_year}_monthly_climatology.zarr"
        ds_climatology.to_zarr(output_filepath, zarr_format=3, mode="w")
        logging.info(f"-> Completed: Saved monthly climatology for {start_year}-{end_year} climate normal period to {output_filepath}.")

    # -- Close ARMOR3D analysis datasets -- #
    ds_climatology.close()
    ds.close()

if __name__ == "__main__":
    main()
