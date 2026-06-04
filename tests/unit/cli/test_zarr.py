"""
test_zarr.py

Description:
Unit tests for zarr.py functions in OceanDataStore.cli.

Authors:
    - Ollie Tooth
"""
import logging
import pytest
import numpy as np
import xarray as xr

from OceanDataStore.cli.zarr import (
    _check_zarr_compatibility,
    _write_to_zarr,
    _update_zarr_store,
)
from OceanDataStore.cli.exceptions import (
    AppendDimensionError,
    AppendDimensionSizeError,
    ChunkSizeError,
    DimensionNotFound,
    DimensionSizeError,
    ObjectNotFound,
)

# --- Unit Tests --- #
class TestCheckZarrCompatibility:
    def test_object_not_found_raises(self, mock_obj_store, mocker):
        # Test ObjectNotFound when no store exists at the given URL:
        mocker.patch("OceanDataStore.cli.zarr._check_zarr_store", return_value=False)
        source_ds = xr.Dataset(
            {"uo": (["time_counter", "x"], np.ones((5, 4), dtype="float32"))},
            coords={"time_counter": np.arange(5)},
        )
        with pytest.raises(ObjectNotFound):
            _check_zarr_compatibility(data=source_ds, obj_store=mock_obj_store, url="s3://bucket/key")

    def test_store_not_found_raises(self, mock_obj_store, mocker):
        # Test FileNotFoundError when zarr version is incompatible with the store:
        mocker.patch("OceanDataStore.cli.zarr._check_zarr_store", return_value=True)
        mocker.patch("OceanDataStore.cli.zarr.xr.open_zarr", side_effect=Exception("incompatible format"))
        source_ds = xr.Dataset(
            {"uo": (["time_counter", "x"], np.ones((5, 4), dtype="float32"))},
            coords={"time_counter": np.arange(5)},
        )
        with pytest.raises(FileNotFoundError):
            _check_zarr_compatibility(data=source_ds, obj_store=mock_obj_store, url="s3://bucket/key")

    def test_dimension_not_found_raises(self, mock_obj_store, mocker):
        # Test DimensionNotFound when source has additional 'x' dim not in store:
        store_ds = xr.Dataset(
            {"uo": (["time_counter"], np.ones(5, dtype="float32"))},
            coords={"time_counter": np.arange(5)},
        )
        mocker.patch("OceanDataStore.cli.zarr._check_zarr_store", return_value=True)
        mocker.patch("OceanDataStore.cli.zarr.xr.open_zarr", return_value=store_ds)
        source_ds = xr.Dataset(
            {"uo": (["time_counter", "x"], np.ones((5, 4), dtype="float32"))},
            coords={"time_counter": np.arange(5, 10)},
        )
        with pytest.raises(DimensionNotFound):
            _check_zarr_compatibility(data=source_ds, obj_store=mock_obj_store, url="s3://bucket/key")

    def test_dimension_size_mismatch_raises(self, mock_obj_store, mocker):
        # Test DimensionSizeError when store has x=3 & source has x=4:
        store_ds = xr.Dataset(
            {"uo": (["time_counter", "x"], np.ones((5, 3), dtype="float32"))},
            coords={"time_counter": np.arange(5)},
        ).chunk({"time_counter": 1, "x": 3})
        mocker.patch("OceanDataStore.cli.zarr._check_zarr_store", return_value=True)
        mocker.patch("OceanDataStore.cli.zarr.xr.open_zarr", return_value=store_ds)
        source_ds = xr.Dataset(
            {"uo": (["time_counter", "x"], np.ones((5, 4), dtype="float32"))},
            coords={"time_counter": np.arange(5, 10)},
        )
        with pytest.raises(DimensionSizeError):
            _check_zarr_compatibility(data=source_ds, obj_store=mock_obj_store, url="s3://bucket/key")

    def test_prepend_raises_append_dimension_error(self, mock_obj_store, mocker):
        # Test AppendDimensionError when source data precedes store data in append_dim:
        store_ds = xr.Dataset(
            {"uo": (["time_counter", "x"], np.ones((5, 4), dtype="float32"))},
            coords={"time_counter": np.arange(5, 10)},
        ).chunk({"time_counter": 1, "x": 4})
        mocker.patch("OceanDataStore.cli.zarr._check_zarr_store", return_value=True)
        mocker.patch("OceanDataStore.cli.zarr.xr.open_zarr", return_value=store_ds)
        source_ds = xr.Dataset(
            {"uo": (["time_counter", "x"], np.ones((5, 4), dtype="float32"))},
            coords={"time_counter": np.arange(0, 5)},
        )
        with pytest.raises(AppendDimensionError):
            _check_zarr_compatibility(data=source_ds, obj_store=mock_obj_store, url="s3://bucket/key")

    def test_chunk_size_mismatch_raises(self, mock_obj_store, mocker):
        # Test ChunkSizeError when store is chunked with x=4; rechunk requests x=2:
        store_ds = xr.Dataset(
            {"uo": (["time_counter", "x"], np.ones((5, 4), dtype="float32"))},
            coords={"time_counter": np.arange(5)},
        ).chunk({"time_counter": 1, "x": 4})
        mocker.patch("OceanDataStore.cli.zarr._check_zarr_store", return_value=True)
        mocker.patch("OceanDataStore.cli.zarr.xr.open_zarr", return_value=store_ds)
        source_ds = xr.Dataset(
            {"uo": (["time_counter", "x"], np.ones((5, 4), dtype="float32"))},
            coords={"time_counter": np.arange(5, 10)},
        )
        with pytest.raises(ChunkSizeError):
            _check_zarr_compatibility(
                data=source_ds, obj_store=mock_obj_store, url="s3://bucket/key",
                rechunk={"x": 2},
            )

    def test_passes_for_valid_compatible_data(self, mock_obj_store, mocker):
        # Test compatibility check passes when appending is viable:
        store_ds = xr.Dataset(
            {"uo": (["time_counter", "x"], np.ones((5, 4), dtype="float32"))},
            coords={"time_counter": np.arange(5)},
        ).chunk({"time_counter": 1, "x": 4})
        mocker.patch("OceanDataStore.cli.zarr._check_zarr_store", return_value=True)
        mocker.patch("OceanDataStore.cli.zarr.xr.open_zarr", return_value=store_ds)
        source_ds = xr.Dataset(
            {"uo": (["time_counter", "x"], np.ones((5, 4), dtype="float32"))},
            coords={"time_counter": np.arange(5, 10)},
        )
        _check_zarr_compatibility(data=source_ds, obj_store=mock_obj_store, url="s3://bucket/key")


class TestWriteToZarr:
    def test_logs_skip_when_store_exists(self, mock_obj_store, mocker, caplog):
        mocker.patch("OceanDataStore.cli.zarr._check_zarr_store", return_value=True)
        mock_to_zarr = mocker.patch.object(xr.Dataset, "to_zarr", return_value=None)
        url = "s3://bucket/prefix"

        da = xr.DataArray(np.ones((3, 3), dtype="float32"),
                          dims=["time_counter", "x"],
                          coords={"time_counter": np.arange(3)},
                          name="tos",
                          )

        with caplog.at_level(logging.INFO):
            _write_to_zarr(data=da, obj_store=mock_obj_store, url=url)

        assert f"Skipping Variable: Store already exists at {url}" in caplog.text
        mock_to_zarr.assert_not_called()

    def test_write_dataarray_calls_to_zarr(self, mock_obj_store, mocker, caplog):
        mocker.patch("OceanDataStore.cli.zarr._check_zarr_store", return_value=False)
        mock_to_zarr = mocker.patch.object(xr.Dataset, "to_zarr", return_value=None)
        url = "s3://bucket/prefix"

        da = xr.DataArray(np.ones((3, 3), dtype="float32"),
                          dims=["time_counter", "x"],
                          coords={"time_counter": np.arange(3)},
                          name="tos",
                          )

        with caplog.at_level(logging.INFO):
            _write_to_zarr(data=da, obj_store=mock_obj_store, url=url)

        mock_to_zarr.assert_called_once()
        assert "Completed: Sent tos to store s3://bucket/prefix in" in caplog.text

    def test_write_dataset_calls_to_zarr_and_logs_timer(self, mock_obj_store, mocker, caplog):
        mocker.patch("OceanDataStore.cli.zarr._check_zarr_store", return_value=False)
        mock_to_zarr = mocker.patch.object(xr.Dataset, "to_zarr", return_value=None)
        url = "s3://bucket/prefix"

        ds = xr.Dataset({"tos": (["time_counter", "x"],
                                 np.ones((3, 3), dtype="float32")
                                 )},
                        coords={"time_counter": np.arange(3)},
                        )

        with caplog.at_level(logging.INFO):
            _write_to_zarr(data=ds, obj_store=mock_obj_store, url=url)

        mock_to_zarr.assert_called_once()
        assert "Completed: Sent dataset to store s3://bucket/prefix in" in caplog.text


class TestUpdateZarrStore:
    def _make_dataset(self, time_vals):
        return xr.Dataset(
            {"tos": (["time_counter", "x"], np.ones((len(time_vals), 3), dtype="float32"))},
            coords={"time_counter": np.array(time_vals)},
        )

    def test_logs_passed_compatibility_checks(self, mock_obj_store, mocker, caplog):
        # Test "Passed Compatibility Checks" is always logged after compatibility check passes:
        mocker.patch("OceanDataStore.cli.zarr._check_zarr_compatibility", return_value=None)
        store_ds = self._make_dataset(np.arange(5))
        mocker.patch("OceanDataStore.cli.zarr.xr.open_zarr", return_value=store_ds)
        mocker.patch("OceanDataStore.cli.zarr._append_to_zarr", return_value=None)
        source_ds = self._make_dataset(np.arange(5, 10))
        url = "s3://bucket/prefix"

        with caplog.at_level(logging.INFO):
            _update_zarr_store(data=source_ds, obj_store=mock_obj_store, url=url)

        assert f"Passed Compatibility Checks for store {url}" in caplog.text

    def test_logs_updating_when_replace_only(self, mock_obj_store, mocker, caplog):
        # Test "Updating" is logged when source is fully within target (replace only, no append):
        mocker.patch("OceanDataStore.cli.zarr._check_zarr_compatibility", return_value=None)
        store_ds = self._make_dataset(np.arange(5))
        mocker.patch("OceanDataStore.cli.zarr.xr.open_zarr", return_value=store_ds)
        mocker.patch("OceanDataStore.cli.zarr._replace_in_zarr", return_value=None)
        source_ds = self._make_dataset(np.arange(2, 5))
        url = "s3://bucket/prefix"

        with caplog.at_level(logging.INFO):
            _update_zarr_store(data=source_ds, obj_store=mock_obj_store, url=url)

        assert f"Updating {url} along time_counter from 2 to 4." in caplog.text
        assert f"Appending to {url}" not in caplog.text

    def test_logs_updating_and_appending_when_replace_and_append(self, mock_obj_store, mocker, caplog):
        # Test both "Updating" and "Appending" are logged when source overlaps and extends beyond target:
        mocker.patch("OceanDataStore.cli.zarr._check_zarr_compatibility", return_value=None)
        store_ds = self._make_dataset(np.arange(5))
        mocker.patch("OceanDataStore.cli.zarr.xr.open_zarr", return_value=store_ds)
        mocker.patch("OceanDataStore.cli.zarr._replace_in_zarr", return_value=None)
        mocker.patch("OceanDataStore.cli.zarr._append_to_zarr", return_value=None)
        source_ds = self._make_dataset(np.arange(2, 7))
        url = "s3://bucket/prefix"

        with caplog.at_level(logging.INFO):
            _update_zarr_store(data=source_ds, obj_store=mock_obj_store, url=url)

        assert f"Updating {url} along time_counter from 2 to 4." in caplog.text
        assert f"Appending to {url} along time_counter from 5 to 6." in caplog.text

    def test_no_update_log_when_append_only(self, mock_obj_store, mocker, caplog):
        # Test no "Updating" is logged when source has no intersection with target (append only):
        mocker.patch("OceanDataStore.cli.zarr._check_zarr_compatibility", return_value=None)
        store_ds = self._make_dataset(np.arange(5))
        mocker.patch("OceanDataStore.cli.zarr.xr.open_zarr", return_value=store_ds)
        mocker.patch("OceanDataStore.cli.zarr._append_to_zarr", return_value=None)
        source_ds = self._make_dataset(np.arange(5, 10))
        url = "s3://bucket/prefix"

        with caplog.at_level(logging.INFO):
            _update_zarr_store(data=source_ds, obj_store=mock_obj_store, url=url)

        assert f"Updating {url}" not in caplog.text
        assert f"Appending to {url}" not in caplog.text

    def test_raises_append_dimension_size_error(self, mock_obj_store, mocker):
        # Test AppendDimensionSizeError when source has non-contiguous overlap with target:
        mocker.patch("OceanDataStore.cli.zarr._check_zarr_compatibility", return_value=None)
        store_ds = self._make_dataset(np.arange(0, 10, 2))  # [0, 2, 4, 6, 8]
        mocker.patch("OceanDataStore.cli.zarr.xr.open_zarr", return_value=store_ds)
        source_ds = self._make_dataset(np.arange(0, 4))  # [0, 1, 2, 3] — 0 & 2 intersect, but 1 & 3 fall within range
        url = "s3://bucket/prefix"

        with pytest.raises(AppendDimensionSizeError):
            _update_zarr_store(data=source_ds, obj_store=mock_obj_store, url=url)

    def test_logs_sending_variable_for_new_dataarray(self, mock_obj_store, mocker, caplog):
        # Test "Sending Variable" is logged when DataArray variable is not present in target store:
        mocker.patch("OceanDataStore.cli.zarr._check_zarr_compatibility", return_value=None)
        store_ds = self._make_dataset(np.arange(5))  # contains "tos"
        mocker.patch("OceanDataStore.cli.zarr.xr.open_zarr", return_value=store_ds)
        mocker.patch("OceanDataStore.cli.zarr._write_to_zarr", return_value=None)
        source_da = xr.DataArray(
            np.ones((5, 3), dtype="float32"),
            dims=["time_counter", "x"],
            coords={"time_counter": np.arange(5, 10)},
            name="so",
        )
        url = "s3://bucket/prefix"

        with caplog.at_level(logging.INFO):
            _update_zarr_store(data=source_da, obj_store=mock_obj_store, url=url)

        assert "Sending Variable so" in caplog.text