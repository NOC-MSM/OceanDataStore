# =========================================================
# update_noc_npd_era5v1_var_attrs.py
#
# Script to update variable attributes in NOC
# Near-Present Day ERA5v1 Icechunk repositories.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# =========================================================
from OceanDataStore.data.utils import update_icechunk_variable_attrs

# ========= Shared Inputs ========= #
# Define credential to write to JASMIN OS:
credentials_filepath = ".../credentials/jasmin_os_credentials.json"

# Define bucket and prefix to Icechunk repository:
bucket = "npd-eorca025-era5v1" # "npd-eorca1-era5v1", "npd-eorca025-era5v1", "npd-eorca12-era5v1"
config_name = "NPD eORCA025 ERA5v1" # "NPD eORCA1 ERA5v1", "NPD eORCA025 ERA5v1", "NPD eORCA12 ERA5v1"
prefix_list = ["eorca025-era5v1-1y", "eorca025-era5v1-1m", "eorca025-era5v1-5d"] # ["eorca1-era5v1-1y", "eorca1-era5v1-1m"], ["eorca025-era5v1-1y", "eorca025-era5v1-1m", "eorca025-era5v1-5d"], ["eorca12-era5v1-1y", "eorca12-era5v1-1m", "eorca12-era5v1-5d"]
group_list = ["gridT", "gridU", "gridV", "gridW", "gridF"]

# ========= Update variable attributes ========= #
for prefix in prefix_list:
    for group in group_list:
        vars = [f"glam{group[-1].lower()}", f"gphi{group[-1].lower()}"]
        attrs = [{"units": "degrees_east", "standard_name": "longitude", "long_name": "Longitude"},
                 {"units": "degrees_north", "standard_name": "latitude", "long_name": "Latitude"}
                 ]
        message = f"Updated {config_name} {prefix} variable attributes -> {vars}"

        update_icechunk_variable_attrs(
                credentials_filepath=credentials_filepath,
                bucket=bucket,
                prefix=prefix,
                vars=vars,
                attrs=attrs,
                commit_message=message,
                branch="main",
                group=group,
                )
