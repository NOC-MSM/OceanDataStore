"""
OceanDataStore: Catalog Module

An open-source Python library to streamline writing, updating and accessing
ocean data stored in cloud object storage.
"""
__author__ = "Ollie Tooth, Joao Morado, Tobias Ferreira"
__credits__ = "National Oceanography Centre (NOC), Southampton, UK"

from OceanDataStore.catalog.oceandatacatalog import OceanDataCatalog, CatalogSummary

__all__ = ("OceanDataCatalog", "CatalogSummary",)
