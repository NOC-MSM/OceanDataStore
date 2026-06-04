"""
test_object_store.py

Description:
Unit tests for the ObjectStoreS3 class in OceanDataStore.cli.object_store.

Authors:
    - Ollie Tooth
"""

import pytest
import json
from OceanDataStore.cli.object_store import ObjectStoreS3


# --- Module Fixtures --- #
@pytest.fixture
def fake_json_file(credentials_dict, mocker):
    return mocker.mock_open(read_data=json.dumps(credentials_dict))

@pytest.fixture
def store_with_json(fake_json_file, mocker):
    mocker.patch("builtins.open", fake_json_file)
    mocker.patch("OceanDataStore.cli.object_store.s3fs.S3FileSystem.__init__", return_value=None)
    return ObjectStoreS3(store_credentials_json="dummy_path.json")


# --- Unit Tests --- #
class TestObjectStoreS3Initialization:
    def test_init_with_args(self, store_with_args, credentials_dict):
        # Test input credentials and remote options are set correctly:
        assert store_with_args._store_credentials == credentials_dict
        assert store_with_args._storage_options["anon"] is True
        assert store_with_args._storage_options["asynchronous"] is False

    def test_init_with_json(self, store_with_json, credentials_dict):
        # Test JSON credentials are loaded and remote options set correctly:
        assert store_with_json._store_credentials == credentials_dict
        assert store_with_json._storage_options["client_kwargs"]["endpoint_url"] == credentials_dict["endpoint_url"]

    def test_init_no_credentials_defaults_to_none(self, mocker):
        mocker.patch("OceanDataStore.cli.object_store.s3fs.S3FileSystem.__init__", return_value=None)
        store = ObjectStoreS3(anon=True, asynchronous=False)
        assert store._store_credentials == {"secret": None, "token": None, "endpoint_url": None}


class TestObjectStoreS3LoadCredentials:
    def test_load_store_credentials_success(self, fake_json_file, credentials_dict, mocker):
        mocker.patch("builtins.open", fake_json_file)
        creds = ObjectStoreS3.load_store_credentials("fakepath.json")
        assert creds == credentials_dict

    def test_load_store_credentials_missing_key(self, mocker):
        incomplete_data = {"token": "abc"}
        fake_file = mocker.mock_open(read_data=json.dumps(incomplete_data))
        mocker.patch("builtins.open", fake_file)
        creds = ObjectStoreS3.load_store_credentials("dummy.json")
        assert creds["token"] == "abc"
        assert "secret" not in creds or creds.get("secret") is None
        assert "endpoint_url" not in creds or creds.get("endpoint_url") is None

    def test_load_store_credentials_file_not_found(self):
        with pytest.raises(Exception):
            ObjectStoreS3.load_store_credentials("/nonexistent/ods_test_path.json")


class TestObjectStoreS3GetRemoteOptions:
    def test_get_storage_options_contents(self, store_with_args):
        opts = store_with_args._storage_options
        assert "anon" in opts
        assert "asynchronous" in opts
        assert "secret" in opts
        assert "key" in opts
        assert "client_kwargs" in opts
        assert "config_kwargs" in opts

    def test_get_storage_options_values(self, store_with_args, credentials_dict):
        opts = store_with_args.get_storage_options()
        assert opts["anon"] is True
        assert opts["asynchronous"] is False
        assert opts["secret"] == credentials_dict["secret"]
        assert opts["key"] == credentials_dict["token"]
        assert opts["client_kwargs"]["endpoint_url"] == credentials_dict["endpoint_url"]
        assert opts["config_kwargs"]["request_checksum_calculation"] == "when_required"
        assert opts["config_kwargs"]["response_checksum_validation"] == "when_required"

    def test_get_storage_options_async(self, store_with_args, credentials_dict):
        opts = store_with_args.get_storage_options(set_async=True)
        # Updated asynchronous option:
        assert opts["asynchronous"] is True
        # Remaining storage options remain unchanged:
        assert opts["anon"] is True
        assert opts["secret"] == credentials_dict["secret"]
        assert opts["key"] == credentials_dict["token"]
        assert opts["client_kwargs"]["endpoint_url"] == credentials_dict["endpoint_url"]
        assert opts["config_kwargs"]["request_checksum_calculation"] == "when_required"
        assert opts["config_kwargs"]["response_checksum_validation"] == "when_required"
