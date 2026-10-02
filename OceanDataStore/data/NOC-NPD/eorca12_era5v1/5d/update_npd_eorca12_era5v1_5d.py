# =========================================================
# earthmover_npd_eorca12_era5v1.py
#
# Script to write NOC NPD eORCA12 ERA5v1 5-day mean ocean
# physics and sea-ice outputs to Icechunk repository for
# Earthmover Data Marketplace.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# =========================================================

import logging
import os
import sys

from nemo_cookbook import NEMODataTree

from OceanDataStore import OceanDataCatalog
from OceanDataStore.cli import update_icechunk

logger = logging.getLogger(__name__)


def banner():
    """Log the OceanDataStore banner."""
    logger.info(
        """
         .~~~.
       .(     ).~~~~~~.
     ~(               ).~~~.
   .(    OceanDataStore     ).  
  (___________________________).

""",
        extra={"simple": True},
    )


def initialise_logging():
    """Initialise logging configuration."""
    logging.basicConfig(
        stream=sys.stdout,
        format="🌐  OceanDataStore  🌐 | %(levelname)10s | %(asctime)s | %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main():
    # ========== Initialize Logging and Print Banner ========== #
    initialise_logging()
    banner()

    # ========== Prepare Data ========== #
    # Open NOC STAC Catalog:
    catalog = OceanDataCatalog(catalog_name="noc-stac")

    # == NEMO eORCA12 domain_cfg == #
    ds_domain = catalog.open_dataset(id="noc-npd-era5/npd-eorca12-era5v1/r1i1c1f1/gn/domain/domain_cfg")
    # ds_domain = ds_domain.chunk({"nav_lev": 3, "y": 1803, "x": 2160})

    # == NEMO T-grid 2-dimensional variables == #
    ds_gridT_2d = catalog.open_dataset(id="noc-npd-era5/npd-eorca12-era5v1/r1i1c1f1/gn/T5d_3d",
                                    variable_names=["zos", "tos_con", "sos_abs", "hfds", "sowaflup", "somxl010"],
                                    )

    # Pre-Processing:
    ds_gridT_2d = (ds_gridT_2d
                .rename({"somxl010": "mlotst", "sowaflup": "wfo"})
                .drop_vars(["time_centered"])
                )

    # == NEMO T-grid 3-dimensional variables == #
    ds_gridT_3d = catalog.open_dataset(id="noc-npd-era5/npd-eorca12-era5v1/r1i1c1f1/gn/T5d_4d",
                                    variable_names=["thetao_con", "so_abs",],
                                    )

    # Pre-Processing:
    ds_gridT_3d = (ds_gridT_3d
                .drop_vars(["time_centered"])
                )
    # Add model bathymetry to the T-grid dataset:
    ds_gridT_3d['bathymetry'] = ds_domain.rename_vars({"nav_lev": "deptht"})['bathy_metry']
    # Add reference vertical grid spacing to the T-grid dataset:
    ds_gridT_3d['e3t_0'] = ds_domain.rename({"nav_lev": "deptht"})['e3t_0']

    # == NEMO icemod 2-dimensional variables == #
    ds_icemod = catalog.open_dataset(id="noc-npd-era5/npd-eorca12-era5v1/r1i1c1f1/gn/I5d_3d",
                                    variable_names=["siconc", "sivolu"],
                                    )

    # Pre-Processing:
    ds_icemod = (ds_icemod
                .rename({"sivolu": "sithick"})
                .drop_vars(["time_centered"])
                )

    # == Merge datasets == #
    ds_gridT_3d['zos'] = ds_gridT_2d['zos']
    ds_gridT_3d['tos_con'] = ds_gridT_2d['tos_con']
    ds_gridT_3d['sos_abs'] = ds_gridT_2d['sos_abs']
    ds_gridT_3d['hfds'] = ds_gridT_2d['hfds']
    ds_gridT_3d['wfo'] = ds_gridT_2d['wfo']
    ds_gridT_3d['mlotst'] = ds_gridT_2d['mlotst']
    ds_gridT_3d['siconc'] = ds_icemod['siconc']
    ds_gridT_3d['sithick'] = ds_icemod['sithick']

    # == NEMO U-grid 3-dimensional variables == #
    ds_gridU_3d = catalog.open_dataset(id="noc-npd-era5/npd-eorca12-era5v1/r1i1c1f1/gn/U5d_4d",
                                    variable_names=["uo"],
                                    )

    # Pre-Processing:
    ds_gridU_3d = (ds_gridU_3d
                .drop_vars(["time_centered"])
                )

    # Add reference vertical grid spacing to the U-grid dataset:
    ds_gridU_3d['e3u_0'] = ds_domain.rename({"nav_lev": "depthu"})['e3u_0']

    # == NEMO V-grid 3-dimensional variables == #
    ds_gridV_3d = catalog.open_dataset(id="noc-npd-era5/npd-eorca12-era5v1/r1i1c1f1/gn/V5d_4d",
                                    variable_names=["vo"],
                                    )

    # Pre-Processing:
    ds_gridV_3d = (ds_gridV_3d
                .drop_vars(["time_centered"])
                )

    # Add reference vertical grid spacing to the V-grid dataset:
    ds_gridV_3d['e3v_0'] = ds_domain.rename({"nav_lev": "depthv"})['e3v_0']

    # ==== Create NEMODataTree === #
    datasets = {"parent": {"domain": ds_domain, "gridT": ds_gridT_3d, "gridU": ds_gridU_3d, "gridV": ds_gridV_3d}}
    nemo = NEMODataTree.from_datasets(datasets, iperio=True, nftype="T", read_mask=True)


    # ========== Update CF-Compliant Metadata ========== #
    # == NEMO T-grid CF-compliance == #
    nemo["gridT"] = nemo["gridT"].chunk({"k": 3, "j": 1803, "i": 2160})
    nemo["gridT"] = nemo["gridT"].dataset.drop_vars(["top_level", "bottom_level"])

    # CF-compliant variable attributes:
    nemo["gridT"]["tos_con"].attrs["long_name"] = "Sea Surface Conservative Temperature"
    nemo["gridT"]["sos_abs"].attrs["long_name"] = "Sea Surface Absolute Salinity"
    nemo["gridT"]["hfds"].attrs["long_name"] = "Total Downward Heat Flux at Sea Surface"
    nemo["gridT"]["wfo"].attrs["long_name"] = "Net Upward Water Flux at Sea Surface"
    nemo["gridT"]["thetao_con"].attrs["long_name"] = "Sea Water Conservative Temperature"
    nemo["gridT"]["so_abs"].attrs["long_name"] = "Sea Water Absolute Salinity"
    nemo["gridT"]["siconc"].attrs["long_name"] = "Sea Ice Area Fraction"
    nemo["gridT"]["sithick"].attrs["long_name"] = "Sea Ice Thickness Derived From Sea Ice Volume per Unit Area"

    var_list = ["zos", "tos_con", "sos_abs", "hfds", "wfo", "thetao_con", "so_abs",
                "siconc", "sithick", "bathymetry", "glamt", "gphit", "deptht",
                "mlotst", "tmask", "tmaskutil", "e1t", "e2t", "e3t_0"
                ]
    for var in var_list:
        nemo["gridT"][var].encoding.clear()

    nemo["gridT"]['bathymetry'].attrs["standard_name"] = "sea_floor_depth_below_sea_surface"
    nemo["gridT"]['bathymetry'].attrs["long_name"] = "Ocean Bathymetry"
    nemo["gridT"]['bathymetry'].attrs["units"] = "m"

    nemo["gridT"]["glamt"].encoding.update({"dtype": "float32"})
    nemo["gridT"]["glamt"].attrs["standard_name"] = "longitude"
    nemo["gridT"]["glamt"].attrs["long_name"] = "Longitude of Ocean T-Grid Points"
    nemo["gridT"]["glamt"].attrs["units"] = "degree_east"

    nemo["gridT"]["gphit"].encoding.update({"dtype": "float32"})
    nemo["gridT"]["gphit"].attrs["standard_name"] = "latitude"
    nemo["gridT"]["gphit"].attrs["long_name"] = "Latitude of Ocean T-Grid Points"
    nemo["gridT"]["gphit"].attrs["units"] = "degree_north"

    nemo["gridT"]["deptht"].encoding.update({"dtype": "float32"})
    nemo["gridT"]["deptht"].attrs["standard_name"] = "depth"
    nemo["gridT"]["deptht"].attrs["long_name"] = "Depth of Ocean T-Grid Points"
    nemo["gridT"]["deptht"].attrs["positive"] = "down"
    nemo["gridT"]["deptht"].attrs["units"] = "m"

    nemo["gridT"]['tmask'].attrs["standard_name"] = "land_sea_mask"
    nemo["gridT"]['tmask'].attrs["long_name"] = "Ocean T-Grid Land-Sea Mask"

    nemo["gridT"]['tmaskutil'].attrs["standard_name"] = "land_sea_unique_point_mask"
    nemo["gridT"]['tmaskutil'].attrs["long_name"] = "Ocean T-Grid Land-Sea Unique Point Mask"

    nemo["gridT"]['e1t'].attrs["standard_name"] = "grid_scale_factor_in_x_direction"
    nemo["gridT"]['e1t'].attrs["long_name"] = "Horizontal T-Grid Scale Factor in X-Direction"
    nemo["gridT"]['e1t'].attrs["units"] = "m"

    nemo["gridT"]['e2t'].attrs["standard_name"] = "grid_scale_factor_in_y_direction"
    nemo["gridT"]['e2t'].attrs["long_name"] = "Horizontal T-Grid Scale Factor in Y-Direction"
    nemo["gridT"]['e2t'].attrs["units"] = "m"

    nemo["gridT"]['e3t_0'].attrs["standard_name"] = "grid_scale_factor_in_z_direction_at_surface"
    nemo["gridT"]['e3t_0'].attrs["long_name"] = "Reference Vertical T-Grid Scale Factor in Z-Direction"
    nemo["gridT"]['e3t_0'].attrs["units"] = "m"

    # CF-Compliant dataset attributes:
    nemo["gridT"].attrs["title"] = "NOC Near-Present Day ERA5v1 global ocean physics & sea-ice outputs stored on the native eORCA12 curvilinear NEMO model T-grid."
    nemo["gridT"].attrs["institution"] = "National Oceanography Centre, UK"
    nemo["gridT"].attrs["source"] = "NEMO v4.2.2 + SI3 v4.0 ocean sea-ice outputs from the eORCA12 configuration forced using bias-corrected ERA5 reanalysis atmospheric fields."
    nemo["gridT"].attrs["references"] = "NOC Near-Present Day: https://noc-msm.github.io/NOC_Near_Present_Day/"
    nemo["gridT"].attrs["comment"] = "This dataset contains 5-day mean outputs for a temporal subset (1990-present) of the original NOC NPD ERA5v1 simulation (1976-present)."
    # Remove non-CF-compliant attributes:
    nemo["gridT"].attrs.pop("name", None)
    nemo["gridT"].attrs.pop("timeStamp", None)
    nemo["gridT"].attrs.pop("uuid", None)
    nemo["gridT"].attrs.pop("history", None)
    nemo["gridT"].attrs.pop("description", None)

    # == NEMO U-grid CF-compliance == #
    nemo["gridU"] = nemo["gridU"].chunk({"k": 3, "j": 1803, "i": 2160})
    # CF-compliant variable attributes:
    nemo["gridU"]["uo"].attrs["long_name"] = "Sea Water Velocity along X-Axis"

    var_list = ["uo", "glamu", "gphiu", "depthu", "umask", "umaskutil", "e1u", "e2u", "e3u_0"]
    for var in var_list:
        nemo["gridU"][var].encoding.clear()

    # CF-compliant ancillary variable attributes:
    nemo["gridU"]['umask'].attrs["standard_name"] = "land_sea_mask"
    nemo["gridU"]['umask'].attrs["long_name"] = "Ocean U-Grid Land-Sea Mask"

    nemo["gridU"]['umaskutil'].attrs["standard_name"] = "land_sea_unique_point_mask"
    nemo["gridU"]['umaskutil'].attrs["long_name"] = "Ocean U-Grid Land-Sea Unique Point Mask"

    nemo["gridU"]['e1u'].attrs["standard_name"] = "grid_scale_factor_in_x_direction"
    nemo["gridU"]['e1u'].attrs["long_name"] = "Horizontal U-Grid Scale Factor in X-Direction"
    nemo["gridU"]['e1u'].attrs["units"] = "m"

    nemo["gridU"]['e2u'].attrs["standard_name"] = "grid_scale_factor_in_y_direction"
    nemo["gridU"]['e2u'].attrs["long_name"] = "Horizontal U-Grid Scale Factor in Y-Direction"
    nemo["gridU"]['e2u'].attrs["units"] = "m"

    nemo["gridU"]['e3u_0'].attrs["standard_name"] = "grid_scale_factor_in_z_direction_at_surface"
    nemo["gridU"]['e3u_0'].attrs["long_name"] = "Reference Vertical U-Grid Scale Factor in Z-Direction"
    nemo["gridU"]['e3u_0'].attrs["units"] = "m"

    nemo["gridU"]["glamu"].encoding.update({"dtype": "float32"})
    nemo["gridU"]["glamu"].attrs["standard_name"] = "longitude"
    nemo["gridU"]["glamu"].attrs["long_name"] = "Longitude of Ocean U-Grid Points"
    nemo["gridU"]["glamu"].attrs["units"] = "degree_east"

    nemo["gridU"]["gphiu"].encoding.update({"dtype": "float32"})
    nemo["gridU"]["gphiu"].attrs["standard_name"] = "latitude"
    nemo["gridU"]["gphiu"].attrs["long_name"] = "Latitude of Ocean U-Grid Points"
    nemo["gridU"]["gphiu"].attrs["units"] = "degree_north"

    nemo["gridU"]["depthu"].encoding.update({"dtype": "float32"})
    nemo["gridU"]["depthu"].attrs["standard_name"] = "depth"
    nemo["gridU"]["depthu"].attrs["long_name"] = "Depth of Ocean U-Grid Points"
    nemo["gridU"]["depthu"].attrs["positive"] = "down"
    nemo["gridU"]["depthu"].attrs["units"] = "m"

    # CF-Compliant dataset attributes:
    nemo["gridU"].attrs["title"] = "NOC Near-Present Day ERA5v1 global ocean physics & sea-ice outputs stored on the native eORCA12 curvilinear NEMO model U-grid."
    nemo["gridU"].attrs["institution"] = "National Oceanography Centre, UK"
    nemo["gridU"].attrs["source"] = "NEMO v4.2.2 + SI3 v4.0 ocean sea-ice outputs from the eORCA12 configuration forced using bias-corrected ERA5 reanalysis atmospheric fields."
    nemo["gridU"].attrs["references"] = "NOC Near-Present Day: https://noc-msm.github.io/NOC_Near_Present_Day/"
    nemo["gridU"].attrs["comment"] = "This dataset contains 5-day mean outputs for a temporal subset (1990-present) of the original NOC NPD ERA5v1 simulation (1976-present)."
    # Remove non-CF-compliant attributes:
    nemo["gridU"].attrs.pop("name", None)
    nemo["gridU"].attrs.pop("timeStamp", None)
    nemo["gridU"].attrs.pop("uuid", None)
    nemo["gridU"].attrs.pop("history", None)
    nemo["gridU"].attrs.pop("description", None)

    # == NEMO V-grid CF-compliance == #
    nemo["gridV"] = nemo["gridV"].chunk({"k": 3, "j": 1803, "i": 2160})
    # CF-compliant variable attributes:
    nemo["gridV"]["vo"].attrs["long_name"] = "Sea Water Velocity along Y-Axis"

    var_list = ["vo", "glamv", "gphiv", "depthv", "vmask", "vmaskutil", "e1v", "e2v", "e3v_0"]
    for var in var_list:
        nemo["gridV"][var].encoding.clear()

    # CF-compliant ancillary variable attributes:
    nemo["gridV"]['vmask'].attrs["standard_name"] = "land_sea_mask"
    nemo["gridV"]['vmask'].attrs["long_name"] = "Ocean V-Grid Land-Sea Mask"

    nemo["gridV"]['vmaskutil'].attrs["standard_name"] = "land_sea_unique_point_mask"
    nemo["gridV"]['vmaskutil'].attrs["long_name"] = "Ocean V-Grid Land-Sea Unique Point Mask"

    nemo["gridV"]['e1v'].attrs["standard_name"] = "grid_scale_factor_in_x_direction"
    nemo["gridV"]['e1v'].attrs["long_name"] = "Horizontal V-Grid Scale Factor in X-Direction"
    nemo["gridV"]['e1v'].attrs["units"] = "m"

    nemo["gridV"]['e2v'].attrs["standard_name"] = "grid_scale_factor_in_y_direction"
    nemo["gridV"]['e2v'].attrs["long_name"] = "Horizontal V-Grid Scale Factor in Y-Direction"
    nemo["gridV"]['e2v'].attrs["units"] = "m"

    nemo["gridV"]['e3v_0'].attrs["standard_name"] = "grid_scale_factor_in_z_direction_at_surface"
    nemo["gridV"]['e3v_0'].attrs["long_name"] = "Reference Vertical V-Grid Scale Factor in Z-Direction"
    nemo["gridV"]['e3v_0'].attrs["units"] = "m"

    nemo["gridV"]["glamv"].encoding.update({"dtype": "float32"})
    nemo["gridV"]["glamv"].attrs["standard_name"] = "longitude"
    nemo["gridV"]["glamv"].attrs["long_name"] = "Longitude of Ocean V-Grid Points"
    nemo["gridV"]["glamv"].attrs["units"] = "degree_east"

    nemo["gridV"]["gphiv"].encoding.update({"dtype": "float32"})
    nemo["gridV"]["gphiv"].attrs["standard_name"] = "latitude"
    nemo["gridV"]["gphiv"].attrs["long_name"] = "Latitude of Ocean V-Grid Points"
    nemo["gridV"]["gphiv"].attrs["units"] = "degree_north"

    nemo["gridV"]["depthv"].encoding.update({"dtype": "float32"})
    nemo["gridV"]["depthv"].attrs["standard_name"] = "depth"
    nemo["gridV"]["depthv"].attrs["long_name"] = "Depth of Ocean V-Grid Points"
    nemo["gridV"]["depthv"].attrs["positive"] = "down"
    nemo["gridV"]["depthv"].attrs["units"] = "m"

    # CF-Compliant dataset attributes:
    nemo["gridV"].attrs["title"] = "NOC Near-Present Day ERA5v1 global ocean physics & sea-ice outputs stored on the native eORCA12 curvilinear NEMO model V-grid."
    nemo["gridV"].attrs["institution"] = "National Oceanography Centre, UK"
    nemo["gridV"].attrs["source"] = "NEMO v4.2.2 + SI3 v4.0 ocean sea-ice outputs from the eORCA12 configuration forced using bias-corrected ERA5 reanalysis atmospheric fields."
    nemo["gridV"].attrs["references"] = "NOC Near-Present Day: https://noc-msm.github.io/NOC_Near_Present_Day/"
    nemo["gridV"].attrs["comment"] = "This dataset contains 5-day mean outputs for a temporal subset (1990-present) of the original NOC NPD ERA5v1 simulation (1976-present)."
    # Remove non-CF-compliant attributes:
    nemo["gridV"].attrs.pop("name", None)
    nemo["gridV"].attrs.pop("timeStamp", None)
    nemo["gridV"].attrs.pop("uuid", None)
    nemo["gridV"].attrs.pop("history", None)
    nemo["gridV"].attrs.pop("description", None)

    # ========== Send to Icechunk Repository ========== #
    bucket = "npd-eorca12-era5v1"
    prefix = "eorca12-era5v1-5d"
    store_credentials_json = ".../credentials/jasmin_os_credentials.json"
    group = "gridV"
    branch = "main"
    config_kwargs = {
            "temporary_directory":f"{os.getcwd()}",
            "local_directory":f"{os.getcwd()}"
        }
    cluster_kwargs = {
            "n_workers" : 30,
            "threads_per_worker" : 1,
            "memory_limit":"3GB"
        }

    for year in range(2015, 2025):
        logger.info(f"=== Updating eORCA12 ERA5v1 {group[-1]}5d Icechunk repository -> {year} ===")
        commit_message = f"Added eORCA12 ERA5v1 {group[-1]}5d ({year}-01 - {year}-12)"

        update_icechunk(
            file=nemo[group].to_dataset().sel(time_counter=slice(f'{year}-01', f'{year}-12')),
            bucket=bucket,
            object_prefix=prefix,
            store_credentials_json=store_credentials_json,
            group=group,
            variables=None,
            append_dim='time_counter',
            grid_filepath=None,
            update_coords=None,
            rechunk=None,
            attrs=None,
            branch=branch,
            commit_message=commit_message,
            dask_config_kwargs=config_kwargs,
            dask_cluster_kwargs=cluster_kwargs,
            icechunk_config=None,
            )
    
if __name__ == "__main__":
    main()
