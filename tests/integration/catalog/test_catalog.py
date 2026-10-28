"""
test_data_catalog.py

Description:
This module defines unit tests for the OceanDataCatalog() class which is
a container for the NOC STAC and a basic API for accessing data
using pystac, Zarr and Icechunk.

Authors:
    - Ollie Tooth
"""

import numpy as np
import pytest
import xarray as xr

from OceanDataStore.catalog import OceanDataCatalog


# Fixture to instantiate catalog using the default URL
@pytest.fixture(scope="module")
def catalog():
    return OceanDataCatalog()

@pytest.fixture(scope="module")
def icechunk_item_id():
    return "en4.2.2/en4.2.2_analysis_g10_monthly"

@pytest.fixture(scope="module")
def zarr_item_id():
    return "noc-npd-jra55/npd-eorca1-jra55v1/r1i1c1f1/T1y"

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
    catalog.search(item_name="domain_cfg")
    items = catalog.available_items
    assert isinstance(items, list)
    assert all(isinstance(i, str) for i in items)

def test_search_valid_collection(catalog):
    catalog.search(collection="noc-npd-era5")
    assert catalog.Collection is not None
    assert isinstance(catalog.available_items, list)

def test_open_icechunk_dataset(catalog, icechunk_item_id):
    assert isinstance(catalog.open_dataset(id=icechunk_item_id), xr.Dataset)

def test_open_zarr_dataset(catalog, zarr_item_id):
    assert isinstance(catalog.open_dataset(id=zarr_item_id), xr.Dataset)

def test_open_dataset_variable_subset(catalog, icechunk_item_id):
    ds = catalog.open_dataset(id=icechunk_item_id, variable_names=["thetao", "so"])
    assert isinstance(ds, xr.Dataset)
    assert "thetao" in ds.data_vars
    assert "so" in ds.data_vars

def test_open_dataset_with_time_range(catalog, icechunk_item_id):
    ds = catalog.open_dataset(id=icechunk_item_id, start_datetime="2020-01", end_datetime="2025-12")
    assert isinstance(ds, xr.Dataset)
    assert ds["time"].min() >= np.datetime64("2020-01")
    assert ds["time"].max() <= np.datetime64("2026-01")

def test_open_dataset_with_bbox(catalog, icechunk_item_id):
    ds = catalog.open_dataset(id=icechunk_item_id, bbox=(-180.0, 0.0, -45.0, 45.0))
    assert isinstance(ds, xr.Dataset)
    assert ds["longitude"].min() >= -180.0
    assert ds["longitude"].max() <= 0.0
    assert ds["latitude"].min() >= -45.0
    assert ds["latitude"].max() <= 45.0
