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
exceptions.py

Description:
This module defines the exception classes raised by OceanDataStore when
performing compatibility checks against existing stores.

Authors:
    - Joao Morado
    - Tobias Ferreira
    - Ollie Tooth
"""

from collections.abc import Mapping
from typing import Any


class OceanDataStoreError(Exception):
    """Base class for all OceanDataStore exceptions."""


class ObjectNotFound(OceanDataStoreError):
    """
    Exception raised when an object is not found in the object store.

    Parameters
    ----------
    object_name : str
        Path to the missing object in the object store.
    """

    def __init__(self, object_name: str) -> None:
        super().__init__(f"Object '{object_name}' not found in the object store.")


class AppendDimensionError(OceanDataStoreError):
    """
    Exception raised when attempting to prepend values along the append dimension.

    Parameters
    ----------
    dim : str
        Name of the append dimension.
    """

    def __init__(self, dim: str) -> None:
        super().__init__(f"Cannot prepend to existing values along append dimension {dim}.")


class DimensionNotFound(OceanDataStoreError):
    """
    Exception raised when a dimension is missing from an existing store.

    Parameters
    ----------
    dim : str
        Name of the missing dimension.
    object_name : str
        Path to the store in the object store.
    """

    def __init__(self, dim: str, object_name: str) -> None:
        super().__init__(f"Dimension {dim} is not found in {object_name}.")


class DimensionSizeError(OceanDataStoreError):
    """
    Exception raised when a dimension size differs from the existing store.

    Parameters
    ----------
    dim : str
        Name of the dimension.
    size : int
        Size of the dimension in the source data.
    expected_size : int
        Size of the dimension in the existing store.
    """

    def __init__(self, dim: str, size: int, expected_size: int) -> None:
        super().__init__(f"Dimension {dim} has size {size}, expected {expected_size}.")


class AppendDimensionSizeError(OceanDataStoreError):
    """
    Exception raised when the overlap along the append dimension is inconsistent.

    Parameters
    ----------
    dim : str
        Name of the append dimension.
    size : int
        Number of source values that overlap the existing store.
    expected_size : int
        Number of source values found in the existing store.
    """

    def __init__(self, dim: str, size: int, expected_size: int) -> None:
        super().__init__(f"Append dimension {dim} has {size} overlapping values, expected {expected_size}.")


class ChunkSizeError(OceanDataStoreError):
    """
    Exception raised when the requested chunks do not match the existing store chunks.

    Parameters
    ----------
    chunks : Mapping[str, Any]
        Requested chunk sizes per dimension.
    store_chunks : Mapping[str, Any]
        Chunk sizes per dimension in the existing store.
    """

    def __init__(self, chunks: Mapping[str, Any], store_chunks: Mapping[str, Any]) -> None:
        super().__init__(f"Specified chunks are {chunks}, expected {store_chunks}.")
