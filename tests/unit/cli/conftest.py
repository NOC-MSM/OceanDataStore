"""
conftest.py

Shared fixtures for OceanDataStore CLI unit tests.
"""
import pytest
import numpy as np
import xarray as xr
from unittest.mock import MagicMock

from OceanDataStore.cli.object_store import ObjectStoreS3


@pytest.fixture
def credentials_dict():
    """
    Fixture providing a dictionary of dummy S3 credentials for testing.
    """
    return {
        "token": "dummy_token",
        "secret": "dummy_secret",
        "endpoint_url": "https://example.com",
    }


@pytest.fixture
def store_with_args(credentials_dict, mocker):
    """
    Fixture providing example ObjectStoreS3 instance from keyword arguments.
    Mocks s3fs.S3FileSystem.__init__ to prevent real connection attempts.
    """
    mocker.patch("OceanDataStore.cli.object_store.s3fs.S3FileSystem.__init__", return_value=None)
    return ObjectStoreS3(
        anon=True,
        asynchronous=False,
        secret=credentials_dict["secret"],
        key=credentials_dict["token"],
        endpoint_url=credentials_dict["endpoint_url"],
    )


@pytest.fixture
def mock_obj_store():
    """
    MagicMock ObjectStoreS3 including stubbed credential/option dicts.
    """
    store = MagicMock(spec=ObjectStoreS3)
    store._store_credentials = {
        "token": "dummy_token",
        "secret": "dummy_secret",
        "endpoint_url": "https://example.com",
    }
    store._storage_options = {
        "anon": False,
        "asynchronous": True,
        "secret": "dummy_secret",
        "key": "dummy_token",
        "client_kwargs": {"endpoint_url": "https://example.com"},
        "config_kwargs": {
            "request_checksum_calculation": "when_required",
            "response_checksum_validation": "when_required",
            },
    }
    store.get_storage_options.return_value = {}
    return store


@pytest.fixture
def simple_dataset():
    """
    Fixture providing sample xr.Dataset.
    """
    ds = xr.Dataset(
        {"tos": (["time_counter", "x", "y"], np.ones((5, 3, 3), dtype="float32"))},
        coords={"time_counter": np.arange(5)},
        )
    return ds


@pytest.fixture
def simple_dataarray(simple_dataset):
    """
    Fixture providing sample xr.DataArray.
    """
    da = simple_dataset["tos"]
    da.name = "tos"
    return da
