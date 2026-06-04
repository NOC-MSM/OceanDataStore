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
This module defines exceptions classes to be
raised when performing sanity checks.

Authors:
    - Joao Morado
    - Tobias Ferreira
    - Ollie Tooth
"""
import logging


class ObjectNotFound(Exception):
    """Exception raised for when an object is not found in the object store."""

    def __init__(self, object_name):
        """Initialise the exception."""
        message = f"Object '{object_name}' not found in the object store."
        logging.warning(message)
        super().__init__(message)

class AppendDimensionError(Exception):
    """
    Exception raised when attempting to modify values along append dimension.
    """

    def __init__(self, dim):
        """Initialise the exception."""
        message = f"Cannot prepend to existing values along append dimension {dim}."
        logging.warning(message)
        super().__init__(message)

class DimensionNotFound(Exception):
    """Exception raised when a dimension is missing."""

    def __init__(self, dim, object_name):
        """Initialise the exception."""
        message = f"Dimension {dim} is not found in {object_name}."
        logging.warning(message)
        super().__init__(message)

class DimensionSizeError(Exception):
    """Exception raised when a dimension has incorrect size."""

    def __init__(self, dim, size, expected_size):
        """Initialise the exception."""
        message = f"Dimension {dim} has size {size}, expected {expected_size}."
        logging.warning(message)
        super().__init__(message)

class AppendDimensionSizeError(Exception):
    """Exception raised when an append dimension has incorrect size."""

    def __init__(self, dim, size, expected_size):
        """Initialise the exception."""
        message = f"Append dimension {dim} has {size} overlapping values, expected {expected_size}."
        logging.warning(message)
        super().__init__(message)

class ChunkSizeError(Exception):
    """Exception raised when data chunks do not match zarr store chunks."""

    def __init__(self, chunks, store_chunks):
        """Initialise the exception."""
        message = f"Specified chunks are {chunks}, expected {store_chunks}."
        logging.warning(message)
        super().__init__(message)
