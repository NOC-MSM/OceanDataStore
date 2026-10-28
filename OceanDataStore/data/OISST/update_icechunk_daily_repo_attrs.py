# =========================================================
# update_icechunk_daily_repo_attrs.py
#
# Script to update global and variable attributes in an
# Icechunk repository.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# =========================================================
from OceanDataStore.data.utils import update_icechunk_global_attrs

# ========= Shared Inputs ========= #
# Define credential to write to JASMIN OS:
credentials_filepath = ".../credentials//jasmin_os_credentials.json"

# Define bucket and prefix to Icechunk repository:
bucket = "oisst"
prefix = "oisst_v2.1_daily"

# ========= Update global attributes ========= #
attrs = {
        "Conventions": "CF-1.5",
        "title": "NOAA OISSTv2.1 Daily Timeseries",
        "description": "NOAA 1/4° Daily Optimum Interpolation Sea Surface Temperature (OISST) version 2.1 daily sea surface temperature timeseries.",
        "source": "Numerical models: Optimal Interpolation. In-situ observations: ICOADS-D R3.0.2, Argo GDAC. Satellite observations: Advanced Very High Resolution Radiometer (AVHRR).",
        "dataset_type": "observation",
        "product_type": "timeseries",
        "product_version": "2.1",
        "institution": "NOAA National Centers for Environmental Information (NCEI)",
        "citation": "Huang, B., C. Liu, V. Banzon, E. Freeman, G. Graham, B. Hankins, T. Smith, and H.-M. Zhang, 2021: Improvements of the Daily Optimum Interpolation Sea Surface Temperature (DOISST) Version 2.1, Journal of Climate, 34, 2923-2939. doi: 10.1175/JCLI-D-20-0166.1",
        "references": "Huang, B., C. Liu, V. Banzon, E. Freeman, G. Graham, B. Hankins, T. Smith, and H.-M. Zhang, 2020: Improvements of the Daily Optimum Interpolation Sea Surface Temperature (DOISST) Version 2.1, Journal of Climate, 34, 2923-2939. doi: 10.1175/JCLI-D-20-0166.1. Banzon, V., Smith, T. M., Chin, T. M., Liu, C., and Hankins, W., 2016: A long-term record of blended satellite and in situ sea-surface temperature for climate monitoring, modeling and environmental studies. Earth Syst. Sci. Data, 8, 165-176, doi:10.5194/essd-8-165-2016. Reynolds, R. W., T. M. Smith, C. Liu, D. B. Chelton, K. S. Casey, and M. G. Schlax, 2007: Daily high-resolution-blended analyses for sea surface temperature. Journal of Climate, 20, 5473-5496, doi:10.1175/JCLI-D-14-00293.1",
        "acknowledgement": "NOAA OI SST V2 High Resolution Dataset data provided by the NOAA PSL, Boulder, Colorado, USA, from their website at https://psl.noaa.gov.",
        "license": "OISST v2.1 data were obtained from https://psl.noaa.gov/data/gridded/data.noaa.oisst.v2.highres.html and are provided under a Creative Commons CC0 1.0 Universal License https://creativecommons.org/publicdomain/zero/1.0/",
        "doi": "10.1175/JCLI-D-20-0166.1",
        "platform": "gr",
        "horizontal_grid_type": "regular rectilinear",
        "horizontal_grid_resolution": "0.25 degree",
        "aggregation": "mean",
        "aggregation_frequency": "daily",
        "status": "ongoing",
        "update_frequency": "quarterly",
        "bbox": "[-180.0, 180.0, -90.0, 90.0]",
    }

message = "Updated NOAA OISSTv2.1 Daily Timeseries -> root group attributes."

update_icechunk_global_attrs(
        credentials_filepath=credentials_filepath,
        bucket=bucket,
        prefix=prefix,
        attrs=attrs,
        commit_message=message,
        )