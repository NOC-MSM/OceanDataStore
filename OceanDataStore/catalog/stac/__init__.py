"""
OceanDataStore: STAC Catalog Module

Tools for constructing the NOC Spatio-Temporal Asset Catalog (STAC) to local JSON files.
"""
from OceanDataStore.catalog.stac.create_noc_stac import create_noc_stac
from OceanDataStore.catalog.stac.npd_era5_collection import create_npd_era5_collection
from OceanDataStore.catalog.stac.npd_jra55_collection import create_npd_jra55_collection
from OceanDataStore.catalog.stac.rapid_evo_collection import create_rapid_evo_collection

__all__ = (
    "create_noc_stac",
    "create_npd_era5_collection",
    "create_npd_jra55_collection",
    "create_rapid_evo_collection",
)
