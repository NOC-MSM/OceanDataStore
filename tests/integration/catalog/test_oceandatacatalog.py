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
from OceanDataStore.catalog.oceandatacatalog import OceanDataCatalog

# Fixture to instantiate catalog using the default URL
@pytest.fixture(scope="module")
def catalog():
    return OceanDataCatalog()

@pytest.fixture(scope="module")
def icechunk_item_id():
    return "noc-npd-era5/npd-eorca1-era5v1/r1i1c1f1/gn/T1y"

@pytest.fixture(scope="module")
def zarr_item_id():
    return "noc-npd-jra55/npd-eorca1-jra55v1/r1i1c1f1/gn/T1y"

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
    assert "noc-npd-era5" in collections

def test_available_items(catalog):
    items = catalog.available_items
    assert isinstance(items, list)
    assert all(isinstance(i, str) for i in items)

def test_available_search_items(catalog):
    catalog.search(platform="gn")
    items = catalog.available_items
    assert isinstance(items, list)
    assert all(isinstance(i, str) for i in items)

def test_search_valid_collection(catalog):
    catalog.search(collection="noc-npd-era5")
    assert catalog.Collection is not None
    assert isinstance(catalog.available_items, list)

def test_search_invalid_collection(catalog):
    with pytest.raises(ValueError, match="Collection 'invalid' not found"):
        catalog.search(collection="invalid")

def test_filter_by_platform(catalog):
    catalog.search(platform="gn")
    assert isinstance(catalog.Items, list)
    for item in catalog.Items:
        assert "gn" in item.properties.get("platform", "")

def test_filter_by_variable(catalog):
    catalog.search(variable_name="tos_con")
    assert isinstance(catalog.Items, list)
    for item in catalog.Items:
        assert "tos_con" in item.properties.get("variables", [])

def test_filter_by_standard_name(catalog):
    catalog.search(standard_name="sea_surface_temperature")
    assert isinstance(catalog.Items, list)
    for item in catalog.Items:
        assert "sea_surface_temperature" in item.properties.get("variable_standard_names", [])

def test_filter_by_item_name(catalog):
    catalog.search(item_name="domain")
    assert isinstance(catalog.Items, list)
    for item in catalog.Items:
        assert "domain" in item.id

def test_summary_outputs(catalog):
    # Catalog summary:
    assert catalog.summary() == catalog.Catalog.describe()
    # Collection summary:
    catalog.search(collection='noc-npd-era5')
    assert (catalog.Collection or catalog.Catalog).describe() == catalog.Collection.describe()

def test_open_icechunk_dataset(catalog, icechunk_item_id):
    assert isinstance(catalog.open_dataset(id=icechunk_item_id), xr.Dataset)

def test_open_zarr_dataset(catalog, zarr_item_id):
    assert isinstance(catalog.open_dataset(id=zarr_item_id), xr.Dataset)

def test_open_dataset_with_time_range(catalog, icechunk_item_id):
    ds = catalog.open_dataset(id=icechunk_item_id, start_datetime="1976-01", end_datetime="1990-01")
    assert isinstance(ds, xr.Dataset)
    assert ds.time_counter.min() >= np.datetime64("1976-01")
    assert ds.time_counter.max() <= np.datetime64("1990-01")

def test_open_dataset_with_bbox(catalog, icechunk_item_id):
    ds = catalog.open_dataset(id=icechunk_item_id, bbox=(-180.0, 0.0, 180.0, 90.0))
    assert isinstance(ds, xr.Dataset)
    assert ds.nav_lat.min() >= 0.0
    assert ds.nav_lat.max() <= 90.0

def test_open_dataset_invalid_asset_key(catalog, icechunk_item_id):
    with pytest.raises(ValueError, match="key 'invalid_key' not found in Item ID"):
        catalog.open_dataset(icechunk_item_id, asset_key="invalid_key")

def test_open_dataset_invalid_id(catalog):
    with pytest.raises(RuntimeError, match="Item ID 'invalid_id' not found in Catalog"):
        catalog.open_dataset(id="invalid_id")

def test_open_dataset_invalid_variable_names(catalog, icechunk_item_id):
    with pytest.raises(KeyError, match="One or more variables not found in dataset"):
        catalog.open_dataset(id=icechunk_item_id, variable_names=["invalid_variable"])
