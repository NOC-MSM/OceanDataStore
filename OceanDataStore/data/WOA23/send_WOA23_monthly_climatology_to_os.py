# =========================================================
# send_WOA23_monthly_climatology_to_os.py
#
# Script to write WOA23 monthly climatologies to Icechunk
# repository in JASMIN cloud object storage.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# =========================================================
import glob
import logging

import numpy as np
import pandas as pd
import xarray as xr
import zarr

from OceanDataStore.cli import initialise_logging, send_to_icechunk
from OceanDataStore.data.utils import (
    compute_cell_area,
    compute_dx,
    compute_dy,
)

logger = logging.getLogger(__name__)


# -- Utility Functions -- #
def get_filepaths(file_prefix:str, file_directory:str) -> list:
    """
    Get filepaths for World Ocean Atlas 2023 climate normals
    in-situ temperature and practical salinity data. 

    Parameters
    ----------
    file_prefix : str
        Prefix of the WOA23 filepaths to be returned.
    file_directory : str
        Directory containing the WOA23 files.

    Returns
    -------
    filepaths : list
        List of WOA23 filepaths for practical salinity & in-situ temperature.
    """
    # Define salinity and temperature filenames:
    salinity_filename = f"{file_prefix}_s*.nc"
    temperature_filename = f"{file_prefix}_t*.nc"

    # Collect filepaths for salinity and temperature data:
    filepaths_sal = sorted(glob.glob(f"{file_directory}/{salinity_filename}"))
    filepaths_temp = sorted(glob.glob(f"{file_directory}/{temperature_filename}"))

    return filepaths_sal, filepaths_temp


def main():
    # ========== Initialise OceanDataStore Logging ========== #
    initialise_logging()
    logging.info("In Progress: Sending WOA23 Monthly Climatologies to JASMIN Object Store.")

    # ========== Prepare Data ========== #
    filedir = "/dssgfs01/scratch/otooth/npd_data/observations/WOA2023"
    salinity_paths, temperature_paths = [], []
    for prefix in ['woa23_decav71A0', 'woa23_decav81B0', 'woa23_decav91C0']:
        # Define file paths for WOA23 monthly climatologies:
        filepaths_sal, filepaths_temp = get_filepaths(file_directory=filedir, file_prefix=prefix)
        salinity_paths.append(filepaths_sal[1:13])
        temperature_paths.append(filepaths_temp[1:13])

    # Define year bounds for each WOA23 monthly climatology:
    year_bound_start = [1971, 1981, 1991]
    year_bound_end = [2000, 2010, 2020]

    for temp_path, sal_path, start_year, end_year in zip(temperature_paths, salinity_paths, year_bound_start, year_bound_end):
        logging.info(f"-> In Progress: Preparing WOA23 {start_year}-{end_year} monthly climatology...")
        # Open WOA23 monthly climatologies dataset:
        ds_s = xr.open_mfdataset(sal_path, decode_times=False, data_vars='all')
        ds_t = xr.open_mfdataset(temp_path, decode_times=False, data_vars='all')

        ds = xr.merge([ds_s, ds_t], compat='no_conflicts').squeeze(drop=True)
        ds = ds.rename({'time': 'month'}).assign_coords({'month': np.arange(1, 13)})
        ds['climatology_bounds'].data = np.array([[np.datetime64(f'{start_year}-{month:02d}', 'M'), np.datetime64(f'{end_year}-{month:02d}', 'M')] for month in range(1, 13)])

        ds = ds.rename({"lon": "longitude",
                        "lat": "latitude",
                        "climatology_bounds": "time_bnds"
                        })

        # Use OceanDataStore standard variable names:
        for var in ds.data_vars:
            if var.startswith("t_"):
                ds = ds.rename({var: var.replace("t_", "thetao_")})
            elif var.startswith("s_"):
                ds = ds.rename({var: var.replace("s_", "so_")})

        # Add ancillary variables:
        ds['dx'] = compute_dx(ds)
        ds['dy'] = compute_dy(ds)
        ds['cell_area'] = compute_cell_area(ds)

        # Custom ancillary variables:
        ds['cell_thickness'] = ds['depth_bnds'].isel(nbounds=1) - ds['depth_bnds'].isel(nbounds=0)
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
        logging.info(f"Completed: Prepared WOA23 {start_year}-{end_year} monthly climatology dataset with ancillary variables.")

        # ========== Prepare Ancillary Data ========== #
        # Open WOA23 land sea mask:
        df_mask = pd.read_table("/dssgfs01/working/otooth/Software/OceanDataStore/OceanDataStore/data/WOA23/data/landsea_04.msk",
                                delimiter=',',
                                header=0
                                )
        # Define level of sea floor (i.e. bottom standard level) at each grid cell:
        ds['bottom_level'] = xr.full_like(ds['cell_area'], fill_value=np.nan).squeeze(drop=True)
        ds['bottom_level'].data = df_mask['Bottom_Standard_Level'].values.reshape(720, 1440)
        ds['bottom_level'].name = "bottom_level"
        ds['bottom_level'].attrs = {"standard_name": "model_level_number_at_sea_floor",
                                    "long_name": "Model Level Number at Sea Floor",
                                    "units": "1"
                                    }
        # Define land sea mask (1 for ocean grid cells, 0 for land grid cells):
        ds['mask'] = ds['bottom_level'] > 1
        ds['mask'].name = "sea_binary_mask"
        ds["mask"] = ds["mask"].assign_attrs({'long_name': "Land-Sea Binary Mask",
                                              "standard_name": "sea_binary_mask",
                                              "comment": "1 = sea, 0 = land"
                                              })
        logging.info("Completed: Prepared land sea mask & bottom level variables.")
        
        # Open WOA23 basin mask:
        df_basin = pd.read_table("/dssgfs01/working/otooth/Software/OceanDataStore/OceanDataStore/data/WOA23/data/basinmask_04.msk",
                                delimiter=',',
                                header=0
                                )
        # Define basin mask (integer values for each ocean basin, NaN for land grid cells):
        ds['basin_mask'] = xr.full_like(ds['cell_area'], fill_value=np.nan).squeeze(drop=True)
        for basin, longitude, latitude in df_basin[["Basin_0m", "Longitude", "Latitude"]].itertuples(index=False):
            ds['basin_mask'].loc[dict(latitude=latitude, longitude=longitude)] = basin

        ds['basin_mask'].attrs = {
            "standard_name": "ocean_basin_mask",
            "long_name": "Ocean Basin Mask",
            "basin_name": {
            1: "Atlantic Ocean",
            2: "Pacific Ocean",
            3: "Indian Ocean",
            4: "Mediterranean Sea",
            5: "Baltic Sea",
            6: "Black Sea",
            7: "Red Sea",
            8: "Persian Gulf",
            9: "Hudson Bay",
            10: "Southern Ocean",
            11: "Arctic Ocean",
            12: "Sea of Japan",
            13: "Kara Sea",
            14: "Sulu Sea",
            15: "Baffin Bay",
            16: "East Mediterranean",
            17: "West Mediterranean",
            18: "Sea of Okhotsk",
            19: "Banda Sea",
            20: "Caribbean Sea",
            21: "Andaman Basin",
            22: "North Caribbean",
            23: "Gulf of Mexico",
            24: "Beaufort Sea",
            25: "South China Sea",
            26: "Barents Sea",
            27: "Celebes Sea",
            28: "Aleutian Basin",
            29: "Fiji Basin",
            30: "North American Basin",
            31: "West European Basin",
            32: "Southeast Indian Basin",
            33: "Coral Sea",
            34: "East Indian Basin",
            35: "Central Indian Basin",
            36: "Southwest Atlantic Basin",
            37: "Southeast Atlantic Basin",
            38: "Southeast Pacific Basin",
            39: "Guatemala Basin",
            40: "East Caroline Basin",
            41: "Marianas Basin",
            42: "Philippine Sea",
            43: "Arabian Sea",
            44: "Chile Basin",
            45: "Somali Basin",
            46: "Mascarene Basin",
            47: "Crozet Basin",
            48: "Guinea Basin",
            49: "Brazil Basin",
            50: "Argentine Basin",
            51: "Tasman Sea",
            52: "Atlantic Indian Basin",
            53: "Caspian Sea",
            54: "Sulu Sea II",
            55: "Venezuela Basin",
            56: "Bay of Bengal",
            57: "Java Sea",
            58: "East Indian Atlantic Basin",
            59: "Chiloe",
            60: "Bransfield Strait",
            }
        }
        logging.info("Completed: Prepared ocean basin mask variable.")

        # ========== CF Attributes ========== #
        ds.attrs.clear()
        ds = ds.assign_attrs({
            "Conventions": "CF-1.6",
            "title": f"World Ocean Atlas 2023 temperature and salinity monthly climatology ({start_year}-{end_year}).",
            "description": f"World Ocean Atlas 2023 (WOA23) temperature and salinity monthly climatology for the global ocean from objectively analysed, quality controlled in-situ profile data ({start_year}-{end_year}).",
            "source": "Numerical models: Objective Analysis. In-situ observations: World Ocean Database (WOD).",
            "dataset_type": "observation",
            "product_type": "climatology",
            "product_version": "1.0",
            "institution": "NOAA National Centers for Environmental Information (NCEI)",
            "citation": "Reagan, James R.; Boyer, Tim P.; García, Hernán E.; Locarnini, Ricardo A.; Baranova, Olga K.; Bouchard, Courtney; Cross, Scott L.; Mishonov, Alexey V.; Paver, Christopher R.; Seidov, Dan; Wang, Zhankun; Dukhovskoy, Dmitry (2023). World Ocean Atlas 2023 (NCEI Accession 0270533). https://www.ncei.noaa.gov/archive/accession/0270533. In Reagan, James R.; Boyer, Tim P.; García, Hernán E.; Locarnini, Ricardo A.; Baranova, Olga K.; Bouchard, Courtney; Cross, Scott L.; Mishonov, Alexey V.; Paver, Christopher R.; Seidov, Dan; Wang, Zhankun; Dukhovskoy, Dmitry (2023). World Ocean Atlas 2023. NOAA National Centers for Environmental Information. Dataset. https://doi.org/10.25921/va26-hv25. Accessed 06-05-2026.",
            "references": "Locarnini, R.A., A.V. Mishonov, O.K. Baranova, J.R. Reagan, T.P. Boyer, D. Seidov, Z. Wang, H.E. Garcia, C. Bouchard, S.L. Cross, C.R. Paver, and D. Dukhovskoy (2024). World Ocean Atlas 2023, Volume 1: Temperature. A. Mishonov Technical Editor, NOAA Atlas NESDIS 89. https://doi.org/10.25923/54bh-1613. Reagan, J.R., D. Seidov, Z. Wang, D. Dukhovskoy, T.P. Boyer, R.A. Locarnini, O.K. Baranova, A.V. Mishonov, H.E. Garcia, C. Bouchard, S.L. Cross, and C.R. Paver (2023). World Ocean Atlas 2023, Volume 2: Salinity. A. Mishonov Technical Editor, NOAA Atlas NESDIS 90, https://doi.org/10.25923/70qt-9574.",
            "acknowledgement": "None",
            "license": "World Ocean Atlas 2023 data were obtained from https://www.ncei.noaa.gov/access/world-ocean-atlas-2023/ and are provided under a Creative Commons CC0 1.0 Universal License https://creativecommons.org/publicdomain/zero/1.0/",
            "doi": "https://doi.org/10.25921/va26-hv25",
            "platform": "gr",
            "horizontal_grid_type": "regular rectilinear",
            "horizontal_grid_resolution": "0.25 degree",
            "vertical_grid_type": "z",
            "vertical_grid_coordinate": "depth",
            "vertical_grid_levels": 57,
            "aggregation": "mean",
            "aggregation_frequency": "monthly",
            "status": "completed",
            "update_frequency": "None",
            "bbox": "[-180.0, 180.0, -90.0, 90.0]",
        })
        logging.info(f"Completed: Added CF-compliant global attributes to WOA23 {start_year}-{end_year} monthly climatology dataset.")

        # ========== Send to Icechunk Repository ========== #
        logging.info(f"In Progress: Sending WOA23 {start_year}-{end_year} monthly climatology to Icechunk Repository...")
        bucket = "woa23"
        prefix = f"woa23_{start_year}_{end_year}_monthly_climatology"
        exists = False
        store_credentials_json = ".../credentials/jasmin_os_credentials.json"
        branch = "main"
        commit_message = f"Added WOA23 {start_year}-{end_year} monthly climatology."
        variable_commits = True
        config_kwargs = {
                "temporary_directory":".../OceanDataStore/OceanDataStore/data/WOA23/",
                "local_directory":".../OceanDataStore/OceanDataStore/data/WOA23/"
            }
        cluster_kwargs = {
                "n_workers" : 25,
                "threads_per_worker" : 1,
                "memory_limit":"3GB"
            }
        
        # Optimise chunk sizes for spatial analysis:
        ds = ds.chunk({'longitude': 1440, 'latitude': 720, 'depth': 5, 'month': 1})

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
            branch=branch,
            commit_message=commit_message,
            variable_commits=variable_commits,
            dask_config_kwargs=config_kwargs,
            dask_cluster_kwargs=cluster_kwargs,
            )

        logging.info(f"Completed: Sent WOA23 {start_year}-{end_year} monthly climatology to Icechunk Repository.")

if __name__ == "__main__":
    main()
