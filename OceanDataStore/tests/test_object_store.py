"""
test_object_store.py

Description:
This module defines unit tests for the ObjectStoreS3 class, which is a subclass
of the S3FileSystem class from the s3fs library.

Authors:
    - Ollie Tooth
"""

import pytest
import json
from ..object_store import ObjectStoreS3


@pytest.fixture
def credentials_dict():
    return {
        "token": "dummy_token",
        "secret": "dummy_secret",
        "endpoint_url": "https://example.com"
    }


@pytest.fixture
def fake_json_file(credentials_dict, mocker):
    return mocker.mock_open(read_data=json.dumps(credentials_dict))


@pytest.fixture
def store_with_args(credentials_dict):
    return ObjectStoreS3(
        anon=True,
        asynchronous=False,
        secret=credentials_dict["secret"],
        key=credentials_dict["token"],
        endpoint_url=credentials_dict["endpoint_url"]
    )


@pytest.fixture
def store_with_json(fake_json_file, mocker):
    mocker.patch("builtins.open", fake_json_file)
    return ObjectStoreS3(store_credentials_json="dummy_path.json")


def test_init_with_args(store_with_args, credentials_dict):
    assert store_with_args._store_credentials == credentials_dict
    assert store_with_args._remote_options["anon"] is True
    assert store_with_args._remote_options["asynchronous"] is False


def test_init_with_json(store_with_json, credentials_dict):
    assert store_with_json._store_credentials == credentials_dict
    assert store_with_json._remote_options["client_kwargs"]["endpoint_url"] == credentials_dict["endpoint_url"]


def test_load_store_credentials_success(fake_json_file, credentials_dict, mocker):
    mocker.patch("builtins.open", fake_json_file)
    creds = ObjectStoreS3.load_store_credentials("fakepath.json")
    assert creds == credentials_dict


def test_load_store_credentials_missing_key(mocker):
    incomplete_data = {"token": "abc"}
    fake_file = mocker.mock_open(read_data=json.dumps(incomplete_data))
    mocker.patch("builtins.open", fake_file)
    creds = ObjectStoreS3.load_store_credentials("dummy.json")
    assert creds["token"] == "abc"
    assert "secret" not in creds or creds["secret"] is None
    assert "endpoint_url" not in creds or creds["endpoint_url"] is None


def test_create_bucket_success(store_with_args, mocker):
    mock_mkdir = mocker.patch.object(store_with_args, "mkdir")
    store_with_args.create_bucket("mybucket")
    mock_mkdir.assert_called_once_with("mybucket")


def test_create_bucket_exists(store_with_args, mocker):
    mocker.patch.object(store_with_args, "mkdir", side_effect=FileExistsError)
    store_with_args.create_bucket("existing-bucket")


def test_get_remote_options(store_with_args):
    opts = store_with_args.get_remote_options()
    assert opts["anon"] is True
    assert opts["asynchronous"] is False
    assert "client_kwargs" in opts


def test_get_store(store_with_args, mocker):
    mock_store = mocker.patch("zarr.storage.FsspecStore")
    store_with_args.get_store("some/path.zarr")
    mock_store.assert_called_once()


def test_get_mapper(store_with_args, mocker):
    mock_mapper = mocker.patch("fsspec.get_mapper")
    store_with_args.get_mapper(bucket="mybucket")
    mock_mapper.assert_called_once()


def test_create_icechunk_repo(store_with_args, mocker):
    mock_storage = mocker.patch("icechunk.s3_storage")
    mock_repo_config = mocker.patch("icechunk.RepositoryConfig")
    mock_repo_create = mocker.patch("icechunk.Repository.create")

    store_with_args.create_icechunk_repo(
        bucket="b",
        prefix="p",
        storage_config_kwargs={},
        repository_config_kwargs={},
        storage_settings_kwargs={}
    )
    mock_storage.assert_called_once()
    mock_repo_config.assert_called_once()
    mock_repo_create.assert_called_once()


def test_open_icechunk_repo(store_with_args, mocker):
    mock_storage = mocker.patch("icechunk.s3_storage")
    mock_repo_config = mocker.patch("icechunk.RepositoryConfig")
    mock_repo_open = mocker.patch("icechunk.Repository.open")

    store_with_args.open_icechunk_repo(
        bucket="b",
        prefix="p",
        storage_config_kwargs={},
        repository_config_kwargs={},
        storage_settings_kwargs={}
    )
    mock_storage.assert_called_once()
    mock_repo_config.assert_called_once()
    mock_repo_open.assert_called_once()
