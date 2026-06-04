"""
test_utils.py

Unit tests for utility functions in OceanDataStore.cli.utils.
"""
import pytest
import xarray as xr

from OceanDataStore.cli.utils import (
    CaptureWarningsPlugin,
    timer,
    _preprocess_dataset,
)

# --- Unit Tests --- #
class TestTimer:
    def test_send_dataset_action(self):
        t = timer("send", "dest/path")
        assert t.action == "Sent dataset to"

    def test_send_variable_action(self):
        t = timer("send", "dest/path", var="tos")
        assert t.action == "Sent tos to"

    def test_replace_dataset_action(self):
        t = timer("replace", "dest/path")
        assert t.action == "Updated"

    def test_replace_variable_action(self):
        t = timer("replace", "dest/path", var="tos")
        assert t.action == "Updated tos in"

    def test_append_dataset_action(self):
        t = timer("append", "dest/path")
        assert t.action == "Appended to"

    def test_append_variable_action(self):
        t = timer("append", "dest/path", var="tos")
        assert t.action == "Appended tos to"

    def test_invalid_action_raises(self):
        with pytest.raises(ValueError, match="Invalid action"):
            timer("invalid", "dest/path")

    def test_context_manager_sets_timing(self):
        t = timer("send", "dest/path")
        with t:
            pass
        assert hasattr(t, "t_start")
        assert hasattr(t, "t_end")
        assert t.t_end >= t.t_start


class TestCaptureWarningsPlugin:
    def test_setup_calls_capture_warnings_true(self, mocker):
        mock_capture = mocker.patch("OceanDataStore.cli.utils.logging.captureWarnings")
        plugin = CaptureWarningsPlugin()
        plugin.setup(None)
        mock_capture.assert_called_once_with(True)

    def test_teardown_calls_capture_warnings_false(self, mocker):
        mock_capture = mocker.patch("OceanDataStore.cli.utils.logging.captureWarnings")
        plugin = CaptureWarningsPlugin()
        plugin.teardown(None)
        mock_capture.assert_called_once_with(False)


class TestPreprocessDataset:
    def test_invalid_filepaths_type(self):
        with pytest.raises(TypeError, match="filepaths must be a list"):
            _preprocess_dataset(file=42)

    def test_list_with_non_string_element(self):
        with pytest.raises(TypeError, match="filepaths must be a list of strings"):
            _preprocess_dataset(file=[1, 2])

    def test_str_invalid_extension(self):
        with pytest.raises(ValueError, match="Invalid file extension"):
            _preprocess_dataset(file="data.nc4")

    def test_list_invalid_extension(self):
        with pytest.raises(ValueError, match="Invalid file extension"):
            _preprocess_dataset(file=["data.nc4"])

    def test_invalid_rechunk_type(self):
        with pytest.raises(TypeError, match="rechunk must be a dictionary"):
            _preprocess_dataset(file="data.nc", rechunk=42)

    def test_invalid_append_dim_type(self):
        with pytest.raises(TypeError, match="append_dim must be a string"):
            _preprocess_dataset(file="data.nc", append_dim=5)

    def test_invalid_update_coords_type(self):
        with pytest.raises(TypeError, match="update_coords must be a dictionary"):
            _preprocess_dataset(file="data.nc", update_coords="bad")

    def test_invalid_grid_filepath_type(self):
        with pytest.raises(TypeError, match="grid_filepath must be a string"):
            _preprocess_dataset(file="data.nc", grid_filepath=99)

    def test_invalid_attrs_type(self):
        with pytest.raises(TypeError, match="attrs must be a dictionary"):
            _preprocess_dataset(file="data.nc", attrs="bad")

    def test_invalid_parallel_type(self):
        with pytest.raises(TypeError, match="parallel must be a boolean"):
            _preprocess_dataset(file="data.nc", parallel="yes")

    def test_glob_no_files_raises(self):
        with pytest.raises(FileNotFoundError):
            _preprocess_dataset(file="/tmp/nonexistent_ods_test_glob_*.nc")

    def test_dataset_input_passes_validation(self, simple_dataset):
        result = _preprocess_dataset(file=simple_dataset)
        assert isinstance(result, xr.Dataset)
