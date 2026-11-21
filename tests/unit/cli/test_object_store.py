"""
test_object_store.py

Description:
Unit tests for the ObjectStoreS3 class in OceanDataStore.cli.object_store.

Authors:
    - Ollie Tooth
"""

import copy
import json

import pytest

from OceanDataStore.cli.object_store import ObjectStoreS3


# --- Module Fixtures --- #
@pytest.fixture
def fake_json_file(credentials_dict, mocker):
    return mocker.mock_open(read_data=json.dumps(credentials_dict))


@pytest.fixture
def store_with_json(fake_json_file, mocker):
    mocker.patch("builtins.open", fake_json_file)
    mocker.patch("OceanDataStore.cli.object_store.os.path.exists", return_value=True)
    mocker.patch("OceanDataStore.cli.object_store.s3fs.S3FileSystem.__init__", return_value=None)
    return ObjectStoreS3(store_credentials_json="dummy_path.json")


# --- Unit Tests --- #
class TestObjectStoreS3Initialization:
    def test_init_with_args(self, store_with_args, credentials_dict):
        # Test environment credentials and remote options are set correctly:
        assert store_with_args._store_credentials == credentials_dict
        assert store_with_args._storage_options["anon"] is True
        assert store_with_args._storage_options["asynchronous"] is False

    def test_init_with_json(self, store_with_json, credentials_dict):
        # Test JSON credentials are loaded and remote options set correctly:
        assert store_with_json._store_credentials == credentials_dict
        assert store_with_json._storage_options["client_kwargs"]["endpoint_url"] == credentials_dict["endpoint_url"]

    def test_init_from_env_unset_defaults_to_none(self, mocker, monkeypatch):
        for var in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_ENDPOINT_URL"):
            monkeypatch.delenv(var, raising=False)
        mocker.patch("OceanDataStore.cli.object_store.s3fs.S3FileSystem.__init__", return_value=None)
        store = ObjectStoreS3(anon=True, asynchronous=False, from_env=True)
        assert store._store_credentials == {"secret": None, "token": None, "endpoint_url": None}

    def test_init_no_credentials_raises(self, mocker):
        mocker.patch("OceanDataStore.cli.object_store.s3fs.S3FileSystem.__init__", return_value=None)
        with pytest.raises(ValueError, match="credentials must be provided"):
            ObjectStoreS3(anon=True, asynchronous=False)


class TestObjectStoreS3LoadCredentials:
    def test_load_store_credentials_success(self, fake_json_file, credentials_dict, mocker):
        mocker.patch("builtins.open", fake_json_file)
        mocker.patch("OceanDataStore.cli.object_store.os.path.exists", return_value=True)
        creds = ObjectStoreS3.load_store_credentials("fakepath.json")
        assert creds == credentials_dict

    def test_load_store_credentials_missing_key(self, mocker):
        incomplete_data = {"token": "abc"}
        fake_file = mocker.mock_open(read_data=json.dumps(incomplete_data))
        mocker.patch("builtins.open", fake_file)
        mocker.patch("OceanDataStore.cli.object_store.os.path.exists", return_value=True)
        creds = ObjectStoreS3.load_store_credentials("dummy.json")
        assert creds["token"] == "abc"
        assert "secret" not in creds or creds.get("secret") is None
        assert "endpoint_url" not in creds or creds.get("endpoint_url") is None

    def test_load_store_credentials_file_not_found(self):
        with pytest.raises(FileNotFoundError):
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

    def test_get_storage_options_async_does_not_mutate_instance(self, store_with_args):
        # Requesting asynchronous options must not change the instance's own options:
        store_with_args.get_storage_options(set_async=True)
        assert store_with_args._storage_options["asynchronous"] is False
        assert store_with_args.get_storage_options()["asynchronous"] is False


class TestObjectStoreS3IcechunkConfig:
    def test_icechunk_config_does_not_mutate_inputs(self, store_with_args, credentials_dict, mocker):
        mock_s3_storage = mocker.patch("OceanDataStore.cli.object_store.icechunk.s3_storage")
        mocker.patch("OceanDataStore.cli.object_store.icechunk.RepositoryConfig")
        storage_config_kwargs = {"region": "us-east-1", "force_path_style": True}
        storage_settings_kwargs = {"unsafe_use_conditional_update": False}
        repository_config_kwargs = {}
        inputs = copy.deepcopy([storage_config_kwargs, storage_settings_kwargs, repository_config_kwargs])

        store_with_args._icechunk_storage_and_config(
            bucket="bucket",
            prefix="prefix",
            storage_config_kwargs=storage_config_kwargs,
            storage_settings_kwargs=storage_settings_kwargs,
            repository_config_kwargs=repository_config_kwargs,
        )

        # Input configs are unchanged (no bucket, prefix or credentials inserted):
        assert [storage_config_kwargs, storage_settings_kwargs, repository_config_kwargs] == inputs
        # Storage is defined using bucket, prefix & instance credentials:
        kwargs = mock_s3_storage.call_args.kwargs
        assert kwargs["bucket"] == "bucket"
        assert kwargs["prefix"] == "prefix"
        assert kwargs["access_key_id"] == credentials_dict["token"]
        assert kwargs["secret_access_key"] == credentials_dict["secret"]
        assert kwargs["endpoint_url"] == credentials_dict["endpoint_url"]

    def test_icechunk_config_user_values_take_precedence(self, store_with_args, mocker):
        mock_s3_storage = mocker.patch("OceanDataStore.cli.object_store.icechunk.s3_storage")
        mocker.patch("OceanDataStore.cli.object_store.icechunk.RepositoryConfig")

        store_with_args._icechunk_storage_and_config(
            bucket="bucket", prefix="prefix", storage_config_kwargs={"region": "eu-west-2"}
        )

        assert mock_s3_storage.call_args.kwargs["region"] == "eu-west-2"
        assert mock_s3_storage.call_args.kwargs["force_path_style"] is True
