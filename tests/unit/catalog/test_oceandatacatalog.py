"""
test_catalog.py

Unit tests for OceanDataCatalog and CatalogSummary.

Authors:
    - Ollie Tooth
"""
import pytest
import numpy as np
import xarray as xr
from unittest.mock import MagicMock

from OceanDataStore.catalog.oceandatacatalog import CatalogSummary


class TestCatalogSummaryRepr:
    def test_repr_returns_display_text(self):
        cs = CatalogSummary(display_text="text output", display_html="<html>")
        assert repr(cs) == "text output"

    def test_html_returns_display_html(self):
        cs = CatalogSummary(display_text="text output", display_html="<html>")
        assert cs._repr_html_() == "<html>"


class TestOceanDataCatalogRepr:
    def test_repr_contains_catalog_name(self, catalog_instance):
        r = repr(catalog_instance)
        assert "noc-stac" in r
        assert "OceanDataCatalog" in r

    def test_repr_contains_item_count(self, catalog_instance):
        r = repr(catalog_instance)
        assert "2" in r


class TestOceanDataCatalogSearch:
    def test_search_collection_type_error(self, catalog_instance):
        with pytest.raises(TypeError, match="'collection' must be a string or None"):
            catalog_instance.search(collection=1234)

    def test_search_dataset_type_error(self, catalog_instance):
        with pytest.raises(TypeError, match="'dataset_type' must be a string or None"):
            catalog_instance.search(dataset_type=["observation"])

    def test_search_product_type_error(self, catalog_instance):
        with pytest.raises(TypeError, match="'product_type' must be a string or None"):
            catalog_instance.search(product_type=["timeseries"])

    def test_search_variable_name_type_error(self, catalog_instance):
        with pytest.raises(TypeError, match="'variable_name' must be a string or None"):
            catalog_instance.search(variable_name=42)

    def test_search_standard_name_type_error(self, catalog_instance):
        with pytest.raises(TypeError, match="'standard_name' must be a string or None"):
            catalog_instance.search(standard_name=42)

    def test_search_item_name_type_error(self, catalog_instance):
        with pytest.raises(TypeError, match="'item_name' must be a string or None"):
            catalog_instance.search(item_name=42)

    def test_search_variable_and_standard_name_raises(self, catalog_instance):
        # Use mock catalog to reach variable name | standard name validation:
        with pytest.raises(ValueError, match="Only one of 'variable_name' or 'standard_name' can be specified."):
            catalog_instance.search(
                variable_name="tos", standard_name="sea_surface_temperature"
            )
    def test_search_invalid_collection_raises(self, catalog_instance):
        with pytest.raises(ValueError, match="Collection 'invalid' not found"):
            catalog_instance.search(collection="invalid")


class TestOceanDataCatalogFilterItems:
    def test_filter_no_criteria_returns_all(self, catalog_instance):
        result = catalog_instance._filter_items(items=catalog_instance.Items)
        assert result == catalog_instance.Items

    def test_filter_by_dataset_type_match(self, catalog_instance):
        result = catalog_instance._filter_items(
            items=catalog_instance.Items, dataset_type="model"
        )
        assert len(result) == 2

    def test_filter_by_dataset_type_no_match(self, catalog_instance):
        result = catalog_instance._filter_items(
            items=catalog_instance.Items, dataset_type="observation"
        )
        assert result == []

    def test_filter_by_product_type_match(self, catalog_instance):
        result = catalog_instance._filter_items(
            items=catalog_instance.Items, product_type="timeseries"
        )
        assert len(result) == 1

    def test_filter_by_product_type_no_match(self, catalog_instance):
        result = catalog_instance._filter_items(
            items=catalog_instance.Items, product_type="climatology"
        )
        assert result == []

    def test_filter_by_variable(self, catalog_instance):
        result = catalog_instance._filter_items(
            items=catalog_instance.Items, variable_name="tos_con"
        )
        assert len(result) == 1
        assert "tos_con" in result[0].properties["variables"]

    def test_filter_by_standard_name(self, catalog_instance):
        result = catalog_instance._filter_items(
            items=catalog_instance.Items,
            standard_name="sea_surface_temperature",
        )
        assert len(result) == 1

    def test_filter_by_item_name(self, catalog_instance):
        result = catalog_instance._filter_items(
            items=catalog_instance.Items, item_name="domain"
        )
        assert len(result) == 1
        assert "domain" in result[0].id

    def test_filter_combined_dataset_type_and_variable(self, catalog_instance):
        result = catalog_instance._filter_items(
            items=catalog_instance.Items, dataset_type="model", variable_name="tos_con"
        )
        assert len(result) == 1

    def test_filter_empty_items_list(self, catalog_instance):
        result = catalog_instance._filter_items(items=[], dataset_type="model")
        assert result == []


class TestOceanDataCatalogSummary:
    def test_summary_returns_catalog_summary(self, catalog_instance):
        result = catalog_instance.summary()
        assert isinstance(result, CatalogSummary)

    def test_summary_display_text_contains_item_count(self, catalog_instance):
        result = catalog_instance.summary()
        assert "2" in repr(result)

    def test_summary_contains_collection_id(self, catalog_instance):
        result = catalog_instance.summary()
        assert "noc-npd-era5" in repr(result)

    def test_summary_raises_without_items(self, catalog_instance):
        catalog_instance.Items = None
        with pytest.raises(ValueError, match="No Items returned"):
            catalog_instance.summary()


class TestOceanDataCatalogItemSummary:
    def test_item_summary_type_error(self, catalog_instance):
        with pytest.raises(TypeError, match="'id' must be a string"):
            catalog_instance.item_summary(id=123)

    def test_item_summary_found_in_items(self, catalog_instance):
        result = catalog_instance.item_summary(
            id="noc-npd-era5/npd-eorca1-era5v1/r1i1c1f1/gn/T1y"
        )
        assert isinstance(result, CatalogSummary)

    def test_item_summary_invalid_id_raises(self, catalog_instance, mocker):
        catalog_instance.Items = None
        mocker.patch.object(
            catalog_instance, "_open_item", side_effect=Exception("not found")
        )
        with pytest.raises(ValueError, match="Item 'nonexistent' not found in Catalog"):
            catalog_instance.item_summary(id="nonexistent")


class TestOceanDataCatalogOpenRepo:
    def test_open_repo_invalid_id_type(self, catalog_instance):
        with pytest.raises(TypeError, match="'id' must be a string"):
            catalog_instance.open_repo(id=123)

    def test_open_repo_invalid_id_raises_runtime_error(self, catalog_instance, mocker):
        mocker.patch.object(
            catalog_instance, "_open_item", side_effect=Exception("not found")
        )
        with pytest.raises(RuntimeError, match="Item ID 'invalid_id' not found in Catalog"):
            catalog_instance.open_repo(id="invalid_id")

    def test_open_repo_invalid_asset_key(self, catalog_instance, mocker):
        mock_item = MagicMock()
        mock_item.assets = {"icechunk": MagicMock()}
        mocker.patch.object(catalog_instance, "_open_item", return_value=mock_item)
        with pytest.raises(ValueError, match="key 'invalid_key' not found in Item ID"):
            catalog_instance.open_repo(id="test-id", asset_key="invalid_key")

    def test_open_repo_invalid_asset_type(self, catalog_instance, mocker):
        mock_item = MagicMock()
        mock_asset = MagicMock()
        mock_asset.extra_fields = {
            "bucket": "my-bucket",
            "prefix": "my-prefix",
            "anonymous": True,
            "endpoint_url": "https://example.com",
        }
        mock_asset.to_dict.return_value = {"type": "application/vnd.zarr"}
        mock_item.assets = {"zarr": mock_asset}

        mocker.patch.object(catalog_instance, "_open_item", return_value=mock_item)

        with pytest.raises(ValueError, match="Item ID 'test-id' asset is not an Icechunk repository."):
            catalog_instance.open_repo(id="test-id")



class TestOceanDataCatalogOpenDataset:
    def test_open_dataset_invalid_id_type(self, catalog_instance):
        with pytest.raises(TypeError, match="'id' must be a string"):
            catalog_instance.open_dataset(id=123)

    def test_open_dataset_invalid_group_type(self, catalog_instance):
        with pytest.raises(TypeError, match="'group' must be a string or None"):
            catalog_instance.open_dataset(id="test-id", group=123)

    def test_open_dataset_invalid_variable_names_type(self, catalog_instance):
        # Validate TypeError before network call:
        with pytest.raises(TypeError, match="'variable_names' must be a list"):
            catalog_instance.open_dataset(id="test-id", variable_names="tos")

    def test_open_dataset_invalid_start_datetime_type(self, catalog_instance):
        with pytest.raises(TypeError, match="'start_datetime' must be a string or None"):
            catalog_instance.open_dataset(id="test-id", start_datetime=2020)

    def test_open_dataset_invalid_end_datetime_type(self, catalog_instance):
        with pytest.raises(TypeError, match="'end_datetime' must be a string or None"):
            catalog_instance.open_dataset(id="test-id", end_datetime=2020)

    def test_open_dataset_invalid_bbox_type(self, catalog_instance):
        # Validate TypeError before network call:
        with pytest.raises(TypeError, match="'bbox' must be a tuple or None"):
            catalog_instance.open_dataset(id="test-id", bbox=[-180.0, -90.0, 180.0, 90.0])

    def test_open_dataset_invalid_bbox_length(self, catalog_instance):
        # Tuple with only 3 elements
        with pytest.raises(TypeError):
            catalog_instance.open_dataset(id="test-id", bbox=(-180.0, -90.0, 180.0))

    def test_open_dataset_invalid_asset_key(self, catalog_instance, mocker):
        mock_item = MagicMock()
        mock_item.assets = {"zarr": MagicMock()}
        mocker.patch.object(catalog_instance, "_open_item", return_value=mock_item)
        with pytest.raises(ValueError, match="key 'invalid_key' not found in Item ID"):
            catalog_instance.open_dataset(id="test-id", asset_key="invalid_key")

    def test_open_dataset_invalid_id_raises_runtime_error(self, catalog_instance, mocker):
        mocker.patch.object(
            catalog_instance, "_open_item", side_effect=Exception("not found")
        )
        with pytest.raises(RuntimeError, match="Item ID 'invalid_id' not found in Catalog"):
            catalog_instance.open_dataset(id="invalid_id")

    def test_open_dataset_invalid_variable_names(self, catalog_instance, mocker):
        mock_item = MagicMock()
        mock_asset = MagicMock()
        mock_asset.extra_fields = {
            "bucket": "my-bucket",
            "prefix": "my-prefix",
            "anonymous": True,
            "endpoint_url": "https://example.com",
        }
        mock_asset.to_dict.return_value = {"type": "application/vnd.zarr+icechunk"}
        mock_item.assets = {"icechunk": mock_asset}

        mocker.patch.object(catalog_instance, "_open_item", return_value=mock_item)

        ds = xr.Dataset({"tos": (["time"], np.arange(5, dtype="float32"))})
        mocker.patch.object(catalog_instance, "_open_icechunk_store", return_value=ds)

        with pytest.raises(KeyError, match="One or more variables not found in dataset"):
            catalog_instance.open_dataset(id="test-id", variable_names=["invalid_variable"])
