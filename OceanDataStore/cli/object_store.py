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
from typing import Union

import icechunk
import s3fs


class ObjectStoreS3(s3fs.S3FileSystem):
    """
    Initialize S3 Object Store.

    Parameters
    ----------
    anon, bool (False)
        Whether to use anonymous connection (public buckets only).
    asynchronous, bool (True)
        Whether to use asynchronous operations (instance to be used inside corountines).
    store_credentials_json, str (None)
        File path to object store credentials .json file.
    secret, str (None)
        If not anonymous, use this secret key to access object store.
    key, str (None)
        If not anonymous, use this key to access object store.
    endpoint_url, str (None)
        Endpoint URL of object store. Needed for non-AWS S3 object stores.
    """
    def __init__(
        self,
        anon: bool = False,
        asynchronous: bool = False,
        store_credentials_json: Union[str, None] = None,
        secret: Union[str, None] = None,
        key: Union[str, None] = None,
        endpoint_url: Union[str, None] = None,
        *fs_args,
        **fs_kwargs,
    ) -> None:

        # Get object store credentials:
        self._anon = anon
        self._asynchronous = asynchronous

        if store_credentials_json is None:
            logging.info(
                "No JSON file was provided."
                "Object store credentials will be obtained from the arguments passed."
            )
            self._store_credentials = {
                "secret": secret,
                "token": key,
                "endpoint_url": endpoint_url,
            }
        else:
            self._store_credentials = self.load_store_credentials(store_credentials_json)

        # Configure storage options:
        self._storage_options = self.get_storage_options()

        super().__init__(*fs_args, **self._storage_options, **fs_kwargs)

    @staticmethod
    def load_store_credentials(path: str) -> dict:
        """
        Set the credentials of the object store from a JSON file.

        Parameters
        ----------
        path
            Absolute or relative filepath to the JSON file containing
            the object store credentials.

        Returns
        -------
        store_credentials
            Dictionary containing the values of the `token`,
            `secret` and `endpoint_url` keys used to access the
            object store.
        """
        try:
            with open(path) as f:
                store_credentials = json.load(f)
        except Exception as error:
            raise Exception(error)

        for key in ["token", "secret", "endpoint_url"]:
            if key not in store_credentials:
                logging.warning(
                    '"%s" is not a key in the JSON file provided. Its value will be set to None.',
                    key
                )

        return store_credentials


    def get_storage_options(
        self,
        set_async: bool=False,
    ) -> dict:
        """
        Get the storage options to access the object store.

        Returns
        -------
        storage_options
            Dictionary containing the storage options to access the object store.

        """
        # Create storage options dict from credentials:
        self._storage_options = {
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
        }

        if set_async:
            # Override asynchronous option of ObjectStoreS3:
            self._storage_options["asynchronous"] = True
        else:
            self._storage_options["asynchronous"] = self._asynchronous

        return self._storage_options


    def create_bucket(
        self,
        bucket: str,
        **kwargs
    ) -> None:
        """
        Create a bucket in the object store.

        Parameters
        ----------
        bucket
            Name of bucket to create.
            Bucket names can consist only of lowercase letters,
            numbers, dots (.), and hyphens (-).
        """
        try:
            return self.mkdir(bucket, **kwargs)
        except FileExistsError:
            logging.info(f"Bucket {bucket} already exists.")


    def create_icechunk_repo(
        self,
        bucket: str,
        prefix: str,
        storage_config_kwargs: dict = {'region': 'us-east-1', 'force_path_style': True},
        repository_config_kwargs: dict = {},
        storage_settings_kwargs: dict = {'unsafe_use_conditional_update': False, 'unsafe_use_conditional_create': False},
    ) -> icechunk.Repository:
        """
        Create a new Icechunk repository in cloud object storage.

        Parameters
        ----------
        bucket: str
            Name of bucket in s3 object store.
        prefix: str
            Name of prefix within bucket to store object.
        storage_config_kwargs
            Kwargs for icechunk.s3_storage().
            See: https://icechunk.io/en/latest/icechunk-python/storage/.
        repository_config_kwargs
            Kwargs for icechunk.RepositoryConfig().
            See: https://icechunk.io/en/latest/icechunk-python/configuration/.
        storage_settings_kwargs
            Kwargs for icechunk.StorageSettings().
            See: https://icechunk.io/en/latest/icechunk-python/configuration/#storage.

        Returns
        -------
        repo, icechunk.Repository
            Icechunk repository.
        """
        # -- Define S3 storage -- #
        storage = icechunk.s3_storage(
            bucket=bucket,
            prefix=prefix,
            access_key_id=self._store_credentials["token"],
            secret_access_key=self._store_credentials['secret'],
            endpoint_url=self._store_credentials['endpoint_url'],
            **storage_config_kwargs
            )

        # -- Define Icechunk repo config -- #
        repo_config = icechunk.RepositoryConfig(
                        storage = icechunk.StorageSettings(
                            **storage_settings_kwargs,
                            ),
                        **repository_config_kwargs,
                        )

        # -- Create Icechunk repo -- #
        repo = icechunk.Repository.create(
            storage=storage,
            config=repo_config
            )

        return repo


    def open_icechunk_repo(
        self,
        bucket: str,
        prefix: str,
        storage_config_kwargs: dict = {'region': 'us-east-1', 'force_path_style': True},
        repository_config_kwargs: dict = {},
        storage_settings_kwargs: dict = {'unsafe_use_conditional_update': False, 'unsafe_use_conditional_create': False},
    ) -> icechunk.Repository:
        """
        Open an existing Icechunk repository in cloud object storage.

        Parameters
        ----------
        bucket: str
            Name of bucket in s3 object store.
        prefix: str
            Name of prefix within bucket to store object.
        storage_config_kwargs
            Kwargs for icechunk.s3_storage().
            See: https://icechunk.io/en/latest/icechunk-python/storage/.
        repository_config_kwargs
            Kwargs for icechunk.RepositoryConfig().
            See: https://icechunk.io/en/latest/icechunk-python/configuration/.
        storage_settings_kwargs
            Kwargs for icechunk.StorageSettings().
            See: https://icechunk.io/en/latest/icechunk-python/configuration/#storage.

        Returns
        -------
        repo, icechunk.Repository
            Icechunk repository.
        """
        # -- Define S3 storage -- #
        storage = icechunk.s3_storage(
            bucket=bucket,
            prefix=prefix,
            access_key_id=self._store_credentials["token"],
            secret_access_key=self._store_credentials['secret'],
            endpoint_url=self._store_credentials['endpoint_url'],
            **storage_config_kwargs
            )

        # -- Define Icechunk repo config -- #
        repo_config = icechunk.RepositoryConfig(
                        storage = icechunk.StorageSettings(
                            **storage_settings_kwargs,
                            ),
                        **repository_config_kwargs,
                        )

        # -- Open existing Icechunk repo -- #
        repo = icechunk.Repository.open(
            storage=storage,
            config=repo_config
            )

        return repo
