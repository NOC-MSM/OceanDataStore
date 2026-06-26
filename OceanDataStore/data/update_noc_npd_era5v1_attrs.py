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


def main(credentials_filepath: str,
         bucket: str,
         config_name: str,
         nemo_config_name: str,
         platform: str,
         agg: str,
         prefix_list: list
         ) -> None:
        # ========== Initialise OceanDataStore Logging ========== #
        initialise_logging()

        # ========= Update global attributes ========= #
        for prefix in prefix_list:
                logging.info(f"In Progress: Updating global attributes for {config_name} {prefix}...")

                # Define aggregation frequency from prefix:
                if "1y" in prefix:
                        agg_freq = "annual"
                elif "1m" in prefix:
                        agg_freq = "monthly"
                elif "5d" in prefix:
                        agg_freq = "5-daily"
                else:
                        raise ValueError(f"Unable to determine aggregation frequency from prefix: {prefix}")
                
                # Define dimensionality from prefix:
                if "_3d" in prefix:
                        dimensionality = "3-dimensional"
                elif "_4d" in prefix:
                        dimensionality = "4-dimensional"
                else:
                        dimensionality = ""

                # Define grid type from prefix:
                if "T" in prefix:
                        grid = "T-grid"
                        variable_type = "scalar variables"
                elif "U" in prefix:
                        grid = "U-grid"
                        variable_type = "vector variables"
                elif "V" in prefix:
                        grid = "V-grid"
                        variable_type = "vector variables"
                elif "W" in prefix:
                        grid = "W-grid"
                        variable_type = "vector variables"
                elif "S" in prefix:
                        grid = ""
                        variable_type = "scalar variables"
                elif "I" in prefix:
                        grid = "T-grid"
                        variable_type = "sea-ice variables"
                else:
                        raise ValueError(f"Unable to determine grid type from prefix: {prefix}")

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
                        "title": f"National Oceanography Centre Near-Present Day (NPD) {horizontal_grid_resolution} global ocean physics & sea-ice hindcast.", 
                        "description": f"NOC Near-Present Day {agg_freq} {agg} global ocean physics & sea-ice hindcast forced using bias-corrected ERA5 atmospheric reanalysis {dimensionality} {variable_type} stored on the native {nemo_config_name} curvilinear NEMO model {grid}.",
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
                        "biogeochemistry_component": "None",
                        "atmospheric_component": "None",
                        "atmospheric_forcing": "ERA5 v1",
                        "variant": "r1i1c1f1",
                }

                message = f"Updated {config_name} {agg_freq} {agg} -> root group attributes."

                update_icechunk_global_attrs(
                        credentials_filepath=credentials_filepath,
                        bucket=bucket,
                        prefix=prefix,
                        attrs=attrs,
                        commit_message=message,
                        )

                logging.info(f"Completed: Updated global attributes for {config_name} {prefix}.")
        

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
        # prefix_list = ["I1m", "I1y",
        #                "S1m", "S1y",
        #                "T1m", "T1y",
        #                "U1m", "U1y",
        #                "V1m", "V1y",
        #                "W1m", "W1y",
        #                ]
        
        # -- eORCA025 --- #
        # prefix_list = ["I1m_3d", "I1y_3d", "I5d_3d",
        #                "S1m_1d", "S1y_1d", "S5d_1d",
        #                "T1m_3d", "T1m_4d", "T1y_3d", "T1y_4d", "T5d_3d", "T5d_4d",
        #                "U1m_3d", "U1m_4d", "U1y_3d", "U1y_4d", "U5d_3d", "U5d_4d",
        #                "V1m_3d", "V1m_4d", "V1y_3d", "V1y_4d", "V5d_3d", "V5d_4d",
        #                "W1m_4d", "W1y_4d", "W5d_4d"
        #                ]

        # -- eORCA12 --- #
        prefix_list = ["I1m_3d", "I1y_3d",
                       "S1m_1d", "S1y_1d",
                       "T1m_3d", "T1m_4d", "T1y_3d", "T1y_4d",
                       "U1m_3d", "U1m_4d", "U1y_3d", "U1y_4d",
                       "V1m_3d", "V1m_4d", "V1y_3d", "V1y_4d",
                       "W1m_4d", "W1y_4d",
                       ]

        # ========= Run Main Function ========= #
        main(credentials_filepath=credentials_filepath,
             bucket=bucket,
             config_name=config_name,
             nemo_config_name=nemo_config_name,
             platform=platform,
             agg=agg,
             prefix_list=prefix_list
             )
