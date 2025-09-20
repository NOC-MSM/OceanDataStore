"""
test_data_catalog.py

Description:
This module defines unit tests for the OceanDataCatalog() class which is
a container for the NOC STAC and a basic API for accessing data
using pystac, Zarr and Icechunk.

Authors:
    - Ollie Tooth
"""

import pytest
import numpy as np
import xarray as xr
from ..data_catalog import OceanDataCatalog

# Fixture to instantiate catalog using the default URL
@pytest.fixture(scope="module")
def catalog():
    return OceanDataCatalog()

@pytest.fixture(scope="module")
def item_id():
    return "noc-npd-era5/npd-eorca1-era5v1/gn_global/T1y"

def test_catalog_initialization(catalog):
    assert catalog.Catalog is not None
    assert hasattr(catalog, "available_collections")
    assert hasattr(catalog, "available_items")
    assert isinstance(catalog.available_collections, list)
    assert isinstance(catalog.available_items, list)

def test_available_collections(catalog):
    collections = catalog.available_collections
    assert isinstance(collections, list)
    assert all(isinstance(c, str) for c in collections)
    assert "noc-npd" in collections

def test_available_items(catalog):
    items = catalog.available_items
    assert isinstance(items, list)
    assert all(isinstance(i, str) for i in items)

def test_search_valid_collection(catalog):
    catalog.search(collection="noc-npd")
    assert catalog.Collection is not None
    assert isinstance(catalog.available_items, list)

def test_search_invalid_collection(catalog):
    with pytest.raises(ValueError, match="Collection 'invalid' not found"):
        catalog.search(collection="invalid")

def test_filter_by_platform(catalog):
    catalog.search(platform="gn_global")
    assert isinstance(catalog.Items, list)
    for item in catalog.Items:
        assert "gn_global" in item.properties.get("platform", "")

def test_filter_by_variable(catalog):
    catalog.search(variable="tos_con")
    assert isinstance(catalog.Items, list)
    for item in catalog.Items:
        assert "tos_con" in item.properties.get("variables", [])

def test_summary_outputs(catalog):
    # Catalog summary:
    assert catalog.summary() == catalog.Catalog.describe()
    # Collection summary:
    catalog.search(collection='noc-npd')
    assert (catalog.Collection or catalog.Catalog).describe() == catalog.Collection.describe()

def test_open_dataset(catalog, item_id):
    assert isinstance(catalog.open_dataset(id=item_id), xr.Dataset)

def test_open_dataset_with_time_range(catalog, item_id):
    ds = catalog.open_dataset(id=item_id, start_datetime="1976-01", end_datetime="1990-01")
    assert isinstance(ds, xr.Dataset)
    assert ds.time_counter.min() >= np.datetime64("1976-01")
    assert ds.time_counter.max() <= np.datetime64("1990-01")

def test_open_dataset_with_bbox(catalog, item_id):
    ds = catalog.open_dataset(id=item_id, bbox=(-180, 0, 180, 90))
    assert isinstance(ds, xr.Dataset)
    assert ds.nav_lat.min() >= 0.0
    assert ds.nav_lat.max() <= 90.0

def test_open_dataset_invalid_asset_key(catalog, item_id):
    with pytest.raises(ValueError, match="key 'invalid_key' not found in Item ID"):
        catalog.open_dataset(item_id, asset_key="invalid_key")

def test_open_dataset_invalid_id(catalog):
    with pytest.raises(ValueError, match="Item ID 'invalid_id' not found"):
        catalog.open_dataset(id="invalid_id")
    
def test_open_dataset_invalid_variable(catalog, item_id):
    with pytest.raises(KeyError, match="invalid_variable not found in dataset"):
        catalog.open_dataset(id=item_id, variables="invalid_variable")
