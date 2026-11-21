"""
test_cli.py

Unit tests for the command line interface in OceanDataStore.cli.cli.
"""
import json
import logging

import pytest

from OceanDataStore.cli.arg_parser import create_parser
from OceanDataStore.cli.cli import process_action
from OceanDataStore.cli.object_store import DEFAULT_ICECHUNK_CONFIG

BASE_ARGS = ["-f", "data.nc", "-c", "creds.json", "-b", "bucket", "-p", "prefix"]


def _parse(action, *extra):
    return create_parser().parse_args([action, *BASE_ARGS, *extra])


class TestProcessAction:
    def test_send_to_icechunk_uses_default_icechunk_config(self, mocker):
        mock_send = mocker.patch("OceanDataStore.cli.cli.send_to_icechunk")
        process_action(_parse("send_to_icechunk", "-vc"))

        kwargs = mock_send.call_args.kwargs
        assert kwargs["file"] == ["data.nc"]
        assert kwargs["bucket"] == "bucket"
        assert kwargs["object_prefix"] == "prefix"
        assert kwargs["append_dim"] == "time_counter"
        assert kwargs["branch"] == "main"
        assert kwargs["variable_commits"] is True
        assert kwargs["dask_cluster_kwargs"] is None
        assert kwargs["icechunk_config"] == DEFAULT_ICECHUNK_CONFIG
        # A copy is passed so the module-level default cannot be modified:
        assert kwargs["icechunk_config"] is not DEFAULT_ICECHUNK_CONFIG

    def test_update_icechunk_ignores_var_commits(self, mocker, caplog):
        mock_update = mocker.patch("OceanDataStore.cli.cli.update_icechunk")
        with caplog.at_level(logging.WARNING):
            process_action(_parse("update_icechunk", "-vc"))

        assert "variable_commits" not in mock_update.call_args.kwargs
        assert "--var-commits flag will be ignored" in caplog.text

    @pytest.mark.parametrize("action", ["send_to_zarr", "update_zarr"])
    def test_zarr_actions_pass_integer_zarr_version(self, mocker, action):
        mock_fn = mocker.patch(f"OceanDataStore.cli.cli.{action}")
        process_action(_parse(action, "-zv", "2"))

        kwargs = mock_fn.call_args.kwargs
        assert kwargs["zarr_version"] == 2
        assert kwargs["client"] is None
        assert "icechunk_config" not in kwargs

    def test_list_action_dest(self, mocker):
        mock_list = mocker.patch("OceanDataStore.cli.cli.list_objects")
        process_action(_parse("list"))
        mock_list.assert_called_once_with(dest="bucket/prefix", store_credentials_json="creds.json")

    def test_dask_config_missing_key_raises(self, tmp_path):
        config_path = tmp_path / "dask_config.json"
        config_path.write_text(json.dumps({"config_kwargs": {}}))
        with pytest.raises(ValueError, match="cluster_kwargs not found in Dask configuration"):
            process_action(_parse("send_to_zarr", "-dc", str(config_path)))
