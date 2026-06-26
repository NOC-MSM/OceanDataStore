# =========================================================
# update_icechunk_repo_attrs.py
#
# Script to update global and variable attributes in an
# Icechunk repository.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# =========================================================
from OceanDataStore.data.utils import (
        update_icechunk_global_attrs,
        update_icechunk_variable_attrs,
)

# ========= Shared Inputs ========= #
# Define credential to write to JASMIN OS:
credentials_filepath = '.../credentials/jasmin_os_credentials.json'

# Define time period for climatology:
start_year = 1991
end_year = 2020

# Define bucket and prefix to Icechunk repository:
bucket = "armor3d"
prefix = f"armor3d_global_my_{start_year}_{end_year}_monthly_climatogy"

# ========= Update variable attributes ========= #
vars = ["month"]
attrs = [{"units": "1", "long_name": "Month of Year"}]
message = f"Updated ARMOR3D Monthly Climatology ({start_year}-{end_year}) variable attributes. -> ['month']"

update_icechunk_variable_attrs(
        credentials_filepath=credentials_filepath,
        bucket=bucket,
        prefix=prefix,
        vars=vars,
        attrs=attrs,
        commit_message=message,
        )

# ========= Update global attributes ========= #
attrs = {
        "Conventions": "CF-1.0",
        "title": f"Multi Observation Global Ocean 3D Temperature Salinity Height Geostrophic Current and MLD monthly climatology ({start_year}-{end_year}).",
        "description": f"Multi Observation Global Ocean ARMOR3D multi-year reprocessed temperature salinity, sea surface height, geostrophic current and mixed layer depth climatology on 1/8 degree regular grid and 50 depth levels ({start_year}-{end_year}).",
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
    }

message = f"Updated ARMOR3D Monthly Climatology ({start_year}-{end_year}) -> root group attributes."

update_icechunk_global_attrs(
        credentials_filepath=credentials_filepath,
        bucket=bucket,
        prefix=prefix,
        attrs=attrs,
        commit_message=message,
        )