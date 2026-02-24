"""
OceanDataStore

An open-source Python library to streamline writing, updating and accessing
ocean data stored in cloud object storage.
"""
__author__ = "Ollie Tooth, Joao Morado, Tobias Ferreira"
__credits__ = "National Oceanography Centre (NOC), Southampton, UK"

from importlib.metadata import version as _version

from OceanDataStore.data_catalog import OceanDataCatalog

try:
    __version__ = _version("OceanDataStore")
except Exception:
    # Local copy or not installed with setuptools.
    # Disable minimum version checks on downstream libraries.
    __version__ = "9999"

__all__ = ("OceanDataCatalog")
