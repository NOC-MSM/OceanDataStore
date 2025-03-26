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
        message = f"Attempting to modify existing values along append dimension {dim}."
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

class ChunkSizeError(Exception):
    """Exception raised when data chunks do not match zarr store chunks."""

    def __init__(self, chunks, store_chunks):
        """Initialise the exception."""
        message = f"Specified chunks are {chunks}, expected {store_chunks}."
        logging.warning(message)
        super().__init__(message)
