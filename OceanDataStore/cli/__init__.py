"""
OceanDataStore: CLI Sub-package

An open-source Python library to streamline writing, updating and accessing
ocean data stored in cloud object storage.
"""
__author__ = "Ollie Tooth, Joao Morado, Tobias Ferreira"
__credits__ = "National Oceanography Centre (NOC), Southampton, UK"

from OceanDataStore.cli.object_store_handler import (
    send_to_zarr,
    send_to_icechunk,
    update_zarr,
    update_icechunk,
    list_objects
)

__all__ = ("send_to_zarr", "send_to_icechunk", "update_zarr", "update_icechunk", "list_objects")
