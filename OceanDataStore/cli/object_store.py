# ===================================================================
# Copyright 2026 National Oceanography Centre
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#  http://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.
# ===================================================================
"""
object_store.py

Description:
This module defines the ObjectStoreS3 class, which is a subclass
of the S3FileSystem class from the s3fs library.

Authors:
    - Ollie Tooth
    - Joao Morado
    - Tobias Ferreira
"""

import json
import logging
import os
from typing import Any

import icechunk
import s3fs

logger = logging.getLogger(__name__)

# Default Icechunk configuration used when none is provided (e.g., JASMIN Object Store).
DEFAULT_ICECHUNK_CONFIG: dict[str, dict[str, Any]] = {
    "storage_config_kwargs": {"region": "us-east-1", "force_path_style": True},
    "repository_config_kwargs": {},
    "storage_settings_kwargs": {"unsafe_use_conditional_update": False, "unsafe_use_conditional_create": False},
}


class ObjectStoreS3(s3fs.S3FileSystem):
    """
    S3-compatible object store filesystem.

    Parameters
    ----------
    anon : bool, default False
        Whether to use an anonymous connection (public buckets only).
    asynchronous : bool, default False
        Whether to use asynchronous operations (instance to be used inside coroutines).
    store_credentials_json : str | None, default None
        Filepath to the object store credentials JSON file, containing the
        keys ``token`` (access key ID), ``secret`` (secret access key) and
        ``endpoint_url``.
    from_env : bool, default False
        Whether to read object store credentials from the environment variables
        ``AWS_ACCESS_KEY_ID``, ``AWS_SECRET_ACCESS_KEY`` and ``AWS_ENDPOINT_URL``.
        Only used when ``store_credentials_json`` is None.
    *fs_args : Any
        Additional positional arguments passed to ``s3fs.S3FileSystem``.
    **fs_kwargs : Any
        Additional keyword arguments passed to ``s3fs.S3FileSystem``.

    Raises
    ------
    ValueError
        If neither ``store_credentials_json`` nor ``from_env=True`` is provided.
    """

    def __init__(
        self,
        anon: bool = False,
        asynchronous: bool = False,
        store_credentials_json: str | None = None,
        from_env: bool = False,
        *fs_args: Any,
        **fs_kwargs: Any,
    ) -> None:
        self._anon = anon
        self._asynchronous = asynchronous

        # Get object store credentials:
        if store_credentials_json is None:
            if from_env:
                self._store_credentials = {
                    "secret": os.getenv("AWS_SECRET_ACCESS_KEY", None),
                    "token": os.getenv("AWS_ACCESS_KEY_ID", None),
                    "endpoint_url": os.getenv("AWS_ENDPOINT_URL", None),
                }
            else:
                raise ValueError(
                    "Object store credentials must be provided via `store_credentials_json` "
                    "or set using `from_env=True`."
                )
        else:
            self._store_credentials = self.load_store_credentials(store_credentials_json)

        # Configure storage options:
        self._storage_options = self.get_storage_options()

        super().__init__(*fs_args, **self._storage_options, **fs_kwargs)

    @staticmethod
    def load_store_credentials(path: str) -> dict[str, Any]:
        """
        Load object store credentials from a JSON file.

        Parameters
        ----------
        path : str
            Filepath to the JSON file containing object store credentials.

        Returns
        -------
        dict[str, Any]
            Dictionary containing the values of the ``token``, ``secret`` and
            ``endpoint_url`` keys used to access the object store.

        Raises
        ------
        FileNotFoundError
            If the credentials file does not exist.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Credentials file not found: {path}")

        with open(path) as f:
            store_credentials = json.load(f)

        for key in ["token", "secret", "endpoint_url"]:
            if key not in store_credentials:
                logger.warning('"%s" not included in the JSON credentials file -> value will be set to None.', key)

        return store_credentials

    def get_storage_options(self, set_async: bool = False) -> dict[str, Any]:
        """
        Get the storage options to access the object store.

        Parameters
        ----------
        set_async : bool, default False
            Whether to return storage options for asynchronous access,
            overriding the ``asynchronous`` option of this instance.

        Returns
        -------
        dict[str, Any]
            Storage options to access the object store (e.g., for
            ``xarray.open_zarr(storage_options=...)``).
        """
        return {
            "anon": self._anon,
            "secret": self._store_credentials["secret"],
            "key": self._store_credentials["token"],
            "client_kwargs": {
                "endpoint_url": self._store_credentials["endpoint_url"],
            },
            "config_kwargs": {
                "request_checksum_calculation": "when_required",
                "response_checksum_validation": "when_required",
            },
            "asynchronous": True if set_async else self._asynchronous,
        }

    def create_bucket(self, bucket: str, **kwargs: Any) -> None:
        """
        Create a bucket in the object store.

        If the bucket already exists, this is logged and no error is raised.

        Parameters
        ----------
        bucket : str
            Name of bucket to create.
        **kwargs : Any
            Additional keyword arguments passed to ``S3FileSystem.mkdir()``.
        """
        try:
            self.mkdir(bucket, **kwargs)
        except FileExistsError:
            logger.info("Failed to create bucket %s -> bucket already exists.", bucket)

    def _icechunk_storage_and_config(
        self,
        bucket: str,
        prefix: str,
        storage_config_kwargs: dict[str, Any] | None = None,
        storage_settings_kwargs: dict[str, Any] | None = None,
        repository_config_kwargs: dict[str, Any] | None = None,
    ) -> tuple[icechunk.Storage, icechunk.RepositoryConfig]:
        """
        Define the Icechunk S3 storage and repository configuration.

        Input dictionaries are copied and are not modified.

        Parameters
        ----------
        bucket : str
            Name of bucket containing the Icechunk repository.
        prefix : str
            Prefix within bucket of the Icechunk repository.
        storage_config_kwargs : dict[str, Any] | None, default None
            Keyword arguments for ``icechunk.s3_storage()``.
        storage_settings_kwargs : dict[str, Any] | None, default None
            Keyword arguments for ``icechunk.StorageSettings()``.
        repository_config_kwargs : dict[str, Any] | None, default None
            Keyword arguments for ``icechunk.RepositoryConfig()``.

        Returns
        -------
        tuple[icechunk.Storage, icechunk.RepositoryConfig]
            Icechunk S3 storage and repository configuration.
        """
        storage_config_kwargs = dict(storage_config_kwargs or {})
        storage_config_kwargs.setdefault("bucket", bucket)
        storage_config_kwargs.setdefault("prefix", prefix)
        storage_config_kwargs.setdefault("region", "us-east-1")
        storage_config_kwargs.setdefault("force_path_style", True)
        storage_config_kwargs.setdefault("access_key_id", self._store_credentials["token"])
        storage_config_kwargs.setdefault("secret_access_key", self._store_credentials["secret"])
        storage_config_kwargs.setdefault("endpoint_url", self._store_credentials["endpoint_url"])

        storage_settings_kwargs = dict(storage_settings_kwargs or {})
        storage_settings_kwargs.setdefault("unsafe_use_conditional_update", False)
        storage_settings_kwargs.setdefault("unsafe_use_conditional_create", False)

        repository_config_kwargs = dict(repository_config_kwargs or {})
        repository_config_kwargs.setdefault("storage", icechunk.StorageSettings(**storage_settings_kwargs))

        storage = icechunk.s3_storage(**storage_config_kwargs)
        repo_config = icechunk.RepositoryConfig(**repository_config_kwargs)

        return storage, repo_config

    def create_icechunk_repo(
        self,
        bucket: str,
        prefix: str,
        storage_config_kwargs: dict[str, Any] | None = None,
        storage_settings_kwargs: dict[str, Any] | None = None,
        repository_config_kwargs: dict[str, Any] | None = None,
        virtual_chunk_containers: icechunk.VirtualChunkContainer | None = None,
    ) -> icechunk.Repository:
        """
        Create a new Icechunk repository in an S3-compatible object store.

        Parameters
        ----------
        bucket : str
            Name of bucket to store Icechunk repository.
        prefix : str
            Prefix within bucket to store Icechunk repository.
        storage_config_kwargs : dict[str, Any] | None, default None
            Keyword arguments for ``icechunk.s3_storage()``.
            See: https://icechunk.io/en/stable/icechunk-python/storage/.
        storage_settings_kwargs : dict[str, Any] | None, default None
            Keyword arguments for ``icechunk.StorageSettings()``.
            See: https://icechunk.io/en/stable/icechunk-python/configuration/#storage.
        repository_config_kwargs : dict[str, Any] | None, default None
            Keyword arguments for ``icechunk.RepositoryConfig()``.
            See: https://icechunk.io/en/stable/icechunk-python/configuration/.
        virtual_chunk_containers : icechunk.VirtualChunkContainer | None, default None
            Virtual chunk container to register in the repository configuration.
            See: https://icechunk.io/en/stable/reference/virtual/#icechunk.virtual.VirtualChunkContainer.

        Returns
        -------
        icechunk.Repository
            New Icechunk repository.
        """
        storage, repo_config = self._icechunk_storage_and_config(
            bucket=bucket,
            prefix=prefix,
            storage_config_kwargs=storage_config_kwargs,
            storage_settings_kwargs=storage_settings_kwargs,
            repository_config_kwargs=repository_config_kwargs,
        )
        if virtual_chunk_containers is not None:
            repo_config.set_virtual_chunk_container(virtual_chunk_containers)

        return icechunk.Repository.create(storage=storage, config=repo_config)

    def open_icechunk_repo(
        self,
        bucket: str,
        prefix: str,
        storage_config_kwargs: dict[str, Any] | None = None,
        repository_config_kwargs: dict[str, Any] | None = None,
        storage_settings_kwargs: dict[str, Any] | None = None,
        container_credentials: dict[str, Any] | None = None,
    ) -> icechunk.Repository:
        """
        Open an existing Icechunk repository from an S3-compatible object store.

        Parameters
        ----------
        bucket : str
            Name of bucket containing the Icechunk repository.
        prefix : str
            Prefix within bucket of the Icechunk repository.
        storage_config_kwargs : dict[str, Any] | None, default None
            Keyword arguments for ``icechunk.s3_storage()``.
            See: https://icechunk.io/en/stable/icechunk-python/storage/.
        repository_config_kwargs : dict[str, Any] | None, default None
            Keyword arguments for ``icechunk.RepositoryConfig()``.
            See: https://icechunk.io/en/stable/icechunk-python/configuration/.
        storage_settings_kwargs : dict[str, Any] | None, default None
            Keyword arguments for ``icechunk.StorageSettings()``.
            See: https://icechunk.io/en/stable/icechunk-python/configuration/#storage.
        container_credentials : dict[str, Any] | None, default None
            Mapping of virtual chunk container URL prefixes to credential objects.
            See: https://icechunk.io/en/stable/reference/#icechunk.Repository.open.

        Returns
        -------
        icechunk.Repository
            Existing Icechunk repository.
        """
        storage, repo_config = self._icechunk_storage_and_config(
            bucket=bucket,
            prefix=prefix,
            storage_config_kwargs=storage_config_kwargs,
            storage_settings_kwargs=storage_settings_kwargs,
            repository_config_kwargs=repository_config_kwargs,
        )

        if container_credentials is None:
            authorize_virtual_chunk_access = None
        else:
            authorize_virtual_chunk_access = icechunk.credentials.containers_credentials(container_credentials)

        return icechunk.Repository.open(
            storage=storage,
            config=repo_config,
            authorize_virtual_chunk_access=authorize_virtual_chunk_access,
        )
