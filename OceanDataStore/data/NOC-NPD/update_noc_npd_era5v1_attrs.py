# =========================================================
# update_noc_npd_era5v1_attrs.py
#
# Script to update global and variable attributes in NOC
# Near-Present Day ERA5v1 Icechunk repositories.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# =========================================================
import logging

from OceanDataStore.cli import initialise_logging
from OceanDataStore.data.utils import update_icechunk_global_attrs

logger = logging.getLogger(__name__)

def main(credentials_filepath: str,
         bucket: str,
         config_name: str,
         nemo_config_name: str,
         platform: str,
         agg: str,
         prefix_list: list,
         group_list: list
         ) -> None:
        # ========== Initialise OceanDataStore Logging ========== #
        initialise_logging()

        # ========= Update global attributes ========= #
        for prefix in prefix_list:
                for group in group_list:
                        logger.info(f"In Progress: Updating global attributes for {config_name} {prefix}...")

                        # Define aggregation frequency from prefix:
                        if "1y" in prefix:
                                agg_freq = "annual"
                        elif "1m" in prefix:
                                agg_freq = "monthly"
                        elif "5d" in prefix:
                                agg_freq = "5-daily"
                        else:
                                raise ValueError(f"Unable to determine aggregation frequency from prefix: {prefix}")

                        # Define biogeochemical component
                        if "medusa" in prefix:
                                biogeochemistry_component = "MEDUSA v"
                                model_components = "ocean physics, sea-ice & biogeochemistry"
                        else:
                                biogeochemistry_component = "None"
                                model_components = "ocean physics & sea-ice"
                        
                        # Define dimensionality from prefix:
                        if "_3d" in prefix:
                                dimensionality = "3-dimensional "
                        elif "_4d" in prefix:
                                dimensionality = "4-dimensional "
                        else:
                                dimensionality = ""

                        # Define grid type from prefix:
                        if group is None:
                                grid = "grid"
                                variable_type = "variables"
                        elif "T" in group:
                                grid = "T-grid"
                                variable_type = "scalar variables"
                        elif "U" in group:
                                grid = "U-grid"
                                variable_type = "vector variables"
                        elif "V" in group:
                                grid = "V-grid"
                                variable_type = "vector variables"
                        elif "W" in group:
                                grid = "W-grid"
                                variable_type = "vector variables"
                        elif "F" in group:
                                grid = "F-grid"
                                variable_type = "vector variables"
                        elif "S" in group:
                                grid = ""
                                variable_type = "scalar variables"
                        elif "I" in group:
                                grid = "T-grid"
                                variable_type = "sea-ice variables"
                        else:
                                grid = "grid"
                                variable_type = "variables"

                        # Define resolution from nemo_config_name:
                        if "eORCA12" in nemo_config_name:
                                horizontal_grid_resolution = "1/12 degree"
                        elif "eORCA025" in nemo_config_name:
                                horizontal_grid_resolution = "1/4 degree"
                        elif "eORCA1" in nemo_config_name:
                                horizontal_grid_resolution = "1 degree"
                        else:
                                raise ValueError(f"Unable to determine horizontal grid resolution from NEMO configuration name: {nemo_config_name}")

                        attrs = {
                                "Conventions": "CF-1.6",
                                "title": f"National Oceanography Centre Near-Present Day (NPD) {horizontal_grid_resolution} global {model_components} hindcast.", 
                                "description": f"NOC Near-Present Day {agg_freq} {agg} global {model_components} hindcast forced using bias-corrected ERA5 atmospheric reanalysis {dimensionality}{variable_type} stored on the native {nemo_config_name} curvilinear NEMO model {grid}.",
                                "dataset_type": "model",
                                "product_type": "timeseries",
                                "product_version": "1.0",
                                "institution": "National Oceanography Centre, UK",
                                "citation": "Blaker, A. T., Tooth, O. J., Palmiéri, J., Coward, A. C., and Mecking, J. (2025). NOC-MSM/NOC_Near_Present_Day: v0.9.0 (v0.9.0). Zenodo. https://doi.org/10.5281/zenodo.15310354.",
                                "references": "Blaker, A.T., Tooth, O.J., Palmiéri, J., Coward, A.C., & Mecking, J. (2025). NOC-MSM/NOC_Near_Present_Day: v0.9.0 (v0.9.0). Zenodo. https://doi.org/10.5281/zenodo.15310354. Guiavarc'h, C., Storkey, D., Blaker, A. T., Blockley, E., Megann, A., Hewitt, H., Bell, M. J., Calvert, D., Copsey, D., Sinha, B., Moreton, S., Mathiot, P., and An, B.: GOSI9: UK Global Ocean and Sea Ice configurations, Geosci. Model Dev., 18, 377-403, https://doi.org/10.5194/gmd-18-377-2025, 2025.",
                                "acknowledgement": "NOC Near-Present Day Documentation available at: https://noc-msm.github.io/NOC_Near_Present_Day/",
                                "license": "UK Open Government License v3.0",
                                "doi": "pending",
                                "platform": platform,
                                "horizontal_grid_type": "curvilinear",
                                "horizontal_grid_resolution": horizontal_grid_resolution,
                                "vertical_grid_type": "zps",
                                "vertical_grid_coordinate": "depth with partial step topography",
                                "vertical_grid_levels": 75,
                                "aggregation": agg,
                                "aggregation_frequency": agg_freq,
                                "status": "ongoing",
                                "update_frequency": "quarterly",
                                "bbox": "[-180.0, 180.0, -90.0, 90.0]",
                                "ocean_component": "NEMO v4.2.2",
                                "sea_ice_component": "SI3 v4.0",
                                "biogeochemistry_component": biogeochemistry_component,
                                "atmospheric_component": "None",
                                "atmospheric_forcing": "ERA5 v1",
                                "variant": "r1i1c1f1",
                        }

                        message = f"Updated {config_name} {agg_freq} {agg} -> {group or 'root'} attributes."

                        update_icechunk_global_attrs(
                                credentials_filepath=credentials_filepath,
                                bucket=bucket,
                                prefix=prefix,
                                attrs=attrs,
                                group=group,
                                commit_message=message,
                                )

                        logger.info(f"Completed: Updated global attributes for {config_name} -> {group or 'root'}.")
        

if __name__ == "__main__":
        # ========= Define Shared Inputs ========= #
        # Define credential to write to JASMIN OS:
        credentials_filepath = '.../credentials/jasmin_os_credentials.json'

        # Define NPD configuration propeties:
        bucket = "npd-eorca12-era5v1"
        config_name = "NPD eORCA12 ERA5v1"
        nemo_config_name = "eORCA12"
        agg = "mean"
        platform = "gn"

        # -- eORCA1 --- #
        prefix_list = ["eorca1-era5v1-1y", "eorca1-era5v1-1m"]
        group_list = ["gridT", "gridU", "gridV", "gridW", "gridF"]
        
        # -- eORCA025 --- #
        # prefix_list = ["eorca025-era5v1-1y", "eorca025-era5v1-1m"]
        # group_list = ["gridT", "gridU", "gridV", "gridW", "gridF"]

        # -- eORCA12 --- #
        # prefix_list = ["eorca12-era5v1-1y", "eorca12-era5v1-1m", "eorca12-era5v1-5d"]
        # group_list = ["gridT", "gridU", "gridV", "gridW", "gridF"]

        # ========= Run Main Function ========= #
        main(credentials_filepath=credentials_filepath,
             bucket=bucket,
             config_name=config_name,
             nemo_config_name=nemo_config_name,
             platform=platform,
             agg=agg,
             prefix_list=prefix_list,
             group_list=group_list
             )
