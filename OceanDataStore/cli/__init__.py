# ===================================================================
# Copyright 2026 National Oceanography Centre
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#  http://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.
# ===================================================================
"""
OceanDataStore: CLI Sub-package

An open-source Python library to streamline writing, updating and accessing
ocean data stored in cloud object storage.
"""
__author__ = "Ollie Tooth, Joao Morado, Tobias Ferreira"
__credits__ = "National Oceanography Centre (NOC), Southampton, UK"

from OceanDataStore.cli.icechunk import (
    send_to_icechunk,
    update_icechunk,
)
from OceanDataStore.cli.logging import initialise_logging
from OceanDataStore.cli.utils import ObjectStoreS3, list_objects
from OceanDataStore.cli.zarr import (
    send_to_zarr,
    update_zarr,
)

__all__ = ("initialise_logging", "send_to_zarr", "send_to_icechunk", "update_zarr", "update_icechunk", "list_objects", "ObjectStoreS3")
