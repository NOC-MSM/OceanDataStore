"""
OceanDataStore: STAC Catalog Module

Tools for constructing the NOC Spatio-Temporal Asset Catalog (STAC) to local JSON files.
"""
from OceanDataStore.catalog.stac.npd_era5_collection import create_npd_era5_collection
from OceanDataStore.catalog.stac.npd_jra55_collection import create_npd_jra55_collection
from OceanDataStore.catalog.stac.rapid_evo_collection import create_rapid_evo_collection
from OceanDataStore.catalog.stac.ods_obs_collection import (
    create_nsidc_collection,
    create_woa23_collection,
    create_oisst_collection,
    create_en4_collection,
    create_armor3d_collection,
    create_hadisst_collection,
    create_era5_collection
)

__all__ = (
    "create_npd_era5_collection",
    "create_npd_jra55_collection",
    "create_rapid_evo_collection",
    "create_nsidc_collection",
    "create_woa23_collection",
    "create_oisst_collection",
    "create_en4_collection",
    "create_armor3d_collection",
    "create_hadisst_collection",
    "create_era5_collection"
)
