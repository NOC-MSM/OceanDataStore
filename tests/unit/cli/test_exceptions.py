"""
test_exceptions.py

Unit tests for custom exceptions in OceanDataStore.cli.exceptions.
"""
import pytest

from OceanDataStore.cli.exceptions import (
    ObjectNotFound,
    AppendDimensionError,
    DimensionNotFound,
    DimensionSizeError,
    AppendDimensionSizeError,
    ChunkSizeError,
)


def test_ObjectNotFound():
    exc = ObjectNotFound(object_name="my_object")
    assert isinstance(exc, Exception)
    assert "my_object" in str(exc)


def test_AppendDimensionError():
    exc = AppendDimensionError("time_counter")
    assert isinstance(exc, Exception)
    assert "time_counter" in str(exc)


def test_DimensionNotFound():
    exc = DimensionNotFound("depth", "my_store")
    assert isinstance(exc, Exception)
    assert "Dimension depth" in str(exc)
    assert "my_store" in str(exc)


def test_DimensionSizeError():
    exc = DimensionSizeError(dim="x", size=3, expected_size=4)
    assert isinstance(exc, Exception)
    assert "x" in str(exc)
    assert "3" in str(exc)
    assert "expected 4" in str(exc)


def test_AppendDimensionSizeError():
    exc = AppendDimensionSizeError(dim="time_counter", size=5, expected_size=3)
    assert isinstance(exc, Exception)
    assert "dimension time_counter" in str(exc)
    assert "5" in str(exc)
    assert "expected 3" in str(exc)


def test_ChunkSizeError():
    exc = ChunkSizeError(chunks={"x": 2}, store_chunks={"x": 3})
    assert isinstance(exc, Exception)
    assert "2" in str(exc)
    assert "expected {'x': 3}" in str(exc)
