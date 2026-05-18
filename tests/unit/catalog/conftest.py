"""
conftest.py

Fixtures for OceanDataCatalog unit tests.

Authors:
    - Ollie Tooth
"""
import pytest
from unittest.mock import MagicMock

from OceanDataStore.catalog import OceanDataCatalog


def make_mock_item(item_id, properties=None, assets=None) -> MagicMock:
    """
    Define minimal mock pystac.Item.
    """
    item = MagicMock()
    item.id = item_id
    item.properties = properties or {}
    item.assets = assets or {}
    item.collection_id = item_id.split("/")[0] if "/" in item_id else "test-collection"
    item.bbox = [-180.0, -90.0, 180.0, 90.0]
    return item


@pytest.fixture
def mock_catalog(mocker) -> MagicMock:
    """
    Patch pystac.read_file to return mock STAC Catalog with two collections.

    Collections: "noc-npd-era5", "noc-npd-jra55"
    """
    # Define mock Collections with get_items():
    mock_col_era5 = MagicMock()
    mock_col_era5.id = "noc-npd-era5"
    mock_col_era5.title = "NPD ERA5v1"
    mock_col_era5.description = "Test ERA5 collection"
    mock_col_era5.extent = MagicMock()
    mock_col_era5.extent.temporal.intervals = [[None, None]]
    mock_col_era5.get_items.return_value = []

    mock_col_jra55 = MagicMock()
    mock_col_jra55.id = "noc-npd-jra55"
    mock_col_jra55.title = "NPD JRA55v1"
    mock_col_jra55.description = "Test JRA55 collection"
    mock_col_jra55.extent = MagicMock()
    mock_col_jra55.extent.temporal.intervals = [[None, None]]
    mock_col_jra55.get_items.return_value = []

    # Define mock Catalog with get_all_collections() and get_child():
    mock_pystac_catalog = MagicMock()
    mock_pystac_catalog.get_all_collections.return_value = [mock_col_era5, mock_col_jra55]
    mock_pystac_catalog.get_child.side_effect = lambda id: {
        "noc-npd-era5": mock_col_era5,
        "noc-npd-jra55": mock_col_jra55,
    }.get(id)
    mock_pystac_catalog.get_items.return_value = []

    # Define mock read_file to return the mock Catalog:
    mocker.patch(
        "OceanDataStore.catalog.oceandatacatalog.pystac.read_file",
        return_value=mock_pystac_catalog,
    )
    return mock_pystac_catalog


@pytest.fixture
def catalog_instance(mock_catalog):
    """
    OceanDataCatalog with pystac patched and two mock Items pre-loaded.

    Items:
      - "noc-npd-era5/npd-eorca1-era5v1/r1i1c1f1/gn/T1y"  (platform gn, has tos_con/sos_con)
      - "noc-npd-era5/npd-eorca1-era5v1/r1i1c1f1/gn/domain" (platform gn, no variables)
    """
    catalog = OceanDataCatalog()

    item_era5 = make_mock_item(
        item_id="noc-npd-era5/npd-eorca1-era5v1/r1i1c1f1/gn/T1y",
        properties={
            "platform": "gn",
            "variables": ["tos_con", "sos_con"],
            "variable_standard_names": [
                "sea_surface_temperature",
                "sea_surface_salinity",
            ],
            "title": "Test ERA5 Item",
            "start_datetime": "1976-01-01",
            "end_datetime": "2020-12-31",
        },
    )
    item_domain = make_mock_item(
        item_id="noc-npd-era5/npd-eorca1-era5v1/r1i1c1f1/gn/domain",
        properties={
            "platform": "gn",
            "variables": [],
            "variable_standard_names": [],
            "title": "Domain Item",
        },
    )
    catalog.Items = [item_era5, item_domain]
    return catalog
