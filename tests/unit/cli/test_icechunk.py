"""
test_icechunk.py

Unit tests for compatibility checks in OceanDataStore.cli.icechunk.

Authors:
    - Ollie Tooth
"""
import logging
import pytest
import numpy as np
import xarray as xr
from unittest.mock import MagicMock

from OceanDataStore.cli.icechunk import (
    _check_icechunk_compatibility,
    _write_to_icechunk,
    _update_icechunk_store,
)
from OceanDataStore.cli.exceptions import (
    DimensionSizeError,
    DimensionNotFound,
    AppendDimensionError,
    AppendDimensionSizeError,
    ChunkSizeError,
)


# --- Module Fixtures --- #
@pytest.fixture
def mock_repo():
    """Mock icechunk.Repository whose readonly_session().store is a MagicMock."""
    repo = MagicMock()
    repo.readonly_session.return_value.store = MagicMock()
    return repo


# --- Unit Tests --- #
class TestCheckIcechunkCompatibility:
    def test_store_not_found_raises(self, mocker, simple_dataset, mock_repo):
        mocker.patch(
            "OceanDataStore.cli.icechunk.xr.open_zarr",
            side_effect=Exception("store does not exist"),
        )
        with pytest.raises(FileNotFoundError, match="IcechunkStore not found"):
            _check_icechunk_compatibility(
                data=simple_dataset,
                dest="test/path",
                repo=mock_repo,
                branch="main",
                append_dim="time_counter",
                rechunk=None,
            )

    def test_dimension_size_mismatch_raises(self, mocker, simple_dataset, mock_repo):
        # Test DimensionSizeError when remote store has x=2 & source has x=3:
        store_ds = simple_dataset.isel(x=slice(0, 2))
        mocker.patch(
            "OceanDataStore.cli.icechunk.xr.open_zarr", return_value=store_ds
        )
        with pytest.raises(DimensionSizeError):
            _check_icechunk_compatibility(
                data=simple_dataset,
                dest="test/path",
                repo=mock_repo,
                branch="main",
                append_dim="time_counter",
                rechunk=None,
            )

    def test_dimension_not_found_raises(self, mocker, simple_dataset, mock_repo):
        # Test DimensionNotFound when source has additional 'z' dim:
        source_ds = xr.Dataset(
            {
                "tos": (
                    ["time_counter", "x", "y", "z"],
                    np.ones((5, 3, 3, 2), dtype="float32"),
                )
            },
            coords={"time_counter": np.arange(5)},
        )
        mocker.patch(
            "OceanDataStore.cli.icechunk.xr.open_zarr", return_value=simple_dataset
        )
        with pytest.raises(DimensionNotFound):
            _check_icechunk_compatibility(
                data=source_ds,
                dest="test/path",
                repo=mock_repo,
                branch="main",
                append_dim="time_counter",
                rechunk=None,
            )

    def test_prepend_raises_append_dimension_error(self, mocker, simple_dataset, mock_repo):
        # Test AppendDimensionError when source data precedes store data in append_dim:
        store_ds = xr.Dataset(
            {"tos": (["time_counter", "x", "y"], np.ones((5, 3, 3), dtype="float32"))},
            coords={"time_counter": np.arange(5, 10)},
        )
        mocker.patch(
            "OceanDataStore.cli.icechunk.xr.open_zarr", return_value=store_ds
        )

        with pytest.raises(AppendDimensionError):
            _check_icechunk_compatibility(
                data=simple_dataset,
                dest="test/path",
                repo=mock_repo,
                branch="main",
                append_dim="time_counter",
                rechunk=None,
            )

    def test_chunk_size_mismatch_raises(self, mocker, simple_dataset, mock_repo):
        # Test ChunkSizeError when store is chunked with x=3; rechunk requests x=2
        store_ds = simple_dataset.chunk({"time_counter": 5, "x": 3, "y": 3})
        mocker.patch(
            "OceanDataStore.cli.icechunk.xr.open_zarr", return_value=store_ds
        )
        with pytest.raises(ChunkSizeError):
            _check_icechunk_compatibility(
                data=simple_dataset,
                dest="test/path",
                repo=mock_repo,
                branch="main",
                append_dim="time_counter",
                rechunk={"x": 2},
            )

    def test_passes_for_valid_compatible_data(self, mocker, mock_repo):
        # Test compatibility check passes when appending is viable:
        store_ds = xr.Dataset(
            {"tos": (["time_counter", "x", "y"], np.ones((5, 3, 3), dtype="float32"))},
            coords={"time_counter": np.arange(5)},
        )
        source_ds = xr.Dataset(
            {"tos": (["time_counter", "x", "y"], np.ones((5, 3, 3), dtype="float32"))},
            coords={"time_counter": np.arange(5, 10)},
        )
        mocker.patch(
            "OceanDataStore.cli.icechunk.xr.open_zarr", return_value=store_ds
        )
        _check_icechunk_compatibility(
            data=source_ds,
            dest="test/path",
            repo=mock_repo,
            branch="main",
            append_dim="time_counter",
            rechunk=None,
        )


class TestWriteToIcechunk:
    def test_write_dataarray_calls_to_icechunk(self, mock_repo, mocker, caplog):
        # Test to_icechunk is called and timer logs "Sent tos to store" when writing DataArray:
        mock_to_icechunk = mocker.patch(
            "OceanDataStore.cli.icechunk.icechunk_xr.to_icechunk", return_value=None
        )
        dest = "bucket/prefix"

        da = xr.DataArray(
            np.ones((3, 3), dtype="float32"),
            dims=["time_counter", "x"],
            coords={"time_counter": np.arange(3)},
            name="tos",
        )

        with caplog.at_level(logging.INFO):
            _write_to_icechunk(data=da, dest=dest, repo=mock_repo, commit_message="test commit")

        mock_to_icechunk.assert_called_once()
        assert "Completed: Sent tos to store s3://bucket/prefix in" in caplog.text

    def test_write_dataset_calls_to_icechunk_and_logs_timer(self, mock_repo, mocker, caplog):
        # Test to_icechunk is called and timer logs "Sent dataset to store" when writing Dataset:
        mock_to_icechunk = mocker.patch(
            "OceanDataStore.cli.icechunk.icechunk_xr.to_icechunk", return_value=None
        )
        dest = "bucket/prefix"

        ds = xr.Dataset(
            {"tos": (["time_counter", "x"], np.ones((3, 3), dtype="float32"))},
            coords={"time_counter": np.arange(3)},
        )

        with caplog.at_level(logging.INFO):
            _write_to_icechunk(data=ds, dest=dest, repo=mock_repo, commit_message="test commit")

        mock_to_icechunk.assert_called_once()
        assert "Completed: Sent dataset to store s3://bucket/prefix in" in caplog.text


class TestUpdateIcechunkStore:
    def _make_dataset(self, time_vals):
        return xr.Dataset(
            {"tos": (["time_counter", "x"], np.ones((len(time_vals), 3), dtype="float32"))},
            coords={"time_counter": np.array(time_vals)},
        )

    def test_logs_passed_compatibility_checks(self, mock_repo, mocker, caplog):
        # Test "Passed Compatibility Checks" is always logged after compatibility check passes:
        mocker.patch("OceanDataStore.cli.icechunk._check_icechunk_compatibility", return_value=None)
        store_ds = self._make_dataset(np.arange(5))
        mocker.patch("OceanDataStore.cli.icechunk.xr.open_zarr", return_value=store_ds)
        mocker.patch("OceanDataStore.cli.icechunk._append_to_icechunk", return_value=None)
        source_ds = self._make_dataset(np.arange(5, 10))
        dest = "bucket/prefix"

        with caplog.at_level(logging.INFO):
            _update_icechunk_store(
                data=source_ds, dest=dest, repo=mock_repo, commit_message="test commit"
            )

        assert f"Passed Compatibility Checks for IcechunkStore {dest}" in caplog.text

    def test_logs_updating_when_replace_only(self, mock_repo, mocker, caplog):
        # Test "Updating" is logged when source is fully within target (replace only, no append):
        mocker.patch("OceanDataStore.cli.icechunk._check_icechunk_compatibility", return_value=None)
        store_ds = self._make_dataset(np.arange(5))
        mocker.patch("OceanDataStore.cli.icechunk.xr.open_zarr", return_value=store_ds)
        mocker.patch("OceanDataStore.cli.icechunk._replace_in_icechunk", return_value=None)
        source_ds = self._make_dataset(np.arange(2, 5))
        dest = "bucket/prefix"

        with caplog.at_level(logging.INFO):
            _update_icechunk_store(
                data=source_ds, dest=dest, repo=mock_repo, commit_message="test commit"
            )

        assert f"Updating {dest} along time_counter from 2 to 4." in caplog.text
        assert f"Appending to {dest}" not in caplog.text

    def test_logs_updating_and_appending_when_replace_and_append(self, mock_repo, mocker, caplog):
        # Test both "Updating" and "Appending" are logged when source overlaps and extends beyond target:
        mocker.patch("OceanDataStore.cli.icechunk._check_icechunk_compatibility", return_value=None)
        store_ds = self._make_dataset(np.arange(5))
        mocker.patch("OceanDataStore.cli.icechunk.xr.open_zarr", return_value=store_ds)
        mocker.patch("OceanDataStore.cli.icechunk._replace_in_icechunk", return_value=None)
        mocker.patch("OceanDataStore.cli.icechunk._append_to_icechunk", return_value=None)
        source_ds = self._make_dataset(np.arange(2, 7))
        dest = "bucket/prefix"

        with caplog.at_level(logging.INFO):
            _update_icechunk_store(
                data=source_ds, dest=dest, repo=mock_repo, commit_message="test commit"
            )

        assert f"Updating {dest} along time_counter from 2 to 4." in caplog.text
        assert f"Appending to {dest} along time_counter from 5 to 6." in caplog.text

    def test_logs_appending_when_append_only(self, mock_repo, mocker, caplog):
        # Test "Appending to" is logged when source has no intersection with target (append only):
        mocker.patch("OceanDataStore.cli.icechunk._check_icechunk_compatibility", return_value=None)
        store_ds = self._make_dataset(np.arange(5))
        mocker.patch("OceanDataStore.cli.icechunk.xr.open_zarr", return_value=store_ds)
        mocker.patch("OceanDataStore.cli.icechunk._append_to_icechunk", return_value=None)
        source_ds = self._make_dataset(np.arange(5, 10))
        dest = "bucket/prefix"

        with caplog.at_level(logging.INFO):
            _update_icechunk_store(
                data=source_ds, dest=dest, repo=mock_repo, commit_message="test commit"
            )

        assert f"Appending to {dest} along time_counter from 5 to 9." in caplog.text

    def test_raises_append_dimension_size_error(self, mock_repo, mocker):
        # Test AppendDimensionSizeError when source has non-contiguous overlap with target:
        mocker.patch("OceanDataStore.cli.icechunk._check_icechunk_compatibility", return_value=None)
        store_ds = self._make_dataset(np.arange(0, 10, 2))  # [0, 2, 4, 6, 8]
        mocker.patch("OceanDataStore.cli.icechunk.xr.open_zarr", return_value=store_ds)
        source_ds = self._make_dataset(np.arange(0, 4))  # [0, 1, 2, 3] — non-contiguous overlap
        dest = "bucket/prefix"

        with pytest.raises(AppendDimensionSizeError):
            _update_icechunk_store(
                data=source_ds, dest=dest, repo=mock_repo, commit_message="test commit"
            )

    def test_logs_sending_variable_for_new_dataarray(self, mock_repo, mocker, caplog):
        # Test "Sending Variable" is logged when DataArray variable is not present in target store:
        store_ds = self._make_dataset(np.arange(5))  # contains "tos"
        mocker.patch("OceanDataStore.cli.icechunk.xr.open_zarr", return_value=store_ds)
        mocker.patch("OceanDataStore.cli.icechunk._write_to_icechunk", return_value=None)
        source_da = xr.DataArray(
            np.ones((5, 3), dtype="float32"),
            dims=["time_counter", "x"],
            coords={"time_counter": np.arange(5, 10)},
            name="so",
        )
        dest = "bucket/prefix"

        with caplog.at_level(logging.INFO):
            _update_icechunk_store(
                data=source_da, dest=dest, repo=mock_repo, commit_message="test commit"
            )

        assert "Sending Variable so" in caplog.text
