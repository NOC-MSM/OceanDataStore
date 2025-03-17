"""
object_store.py

Description:
This module defines the ObjectStoreS3 class, which is a subclass
of the S3FileSystem class from the s3fs library.

Authors:
    - Joao Morado
    - Tobias Ferreira
    - Ollie Tooth
"""
import json
import zarr
import s3fs
import fsspec
import logging

from typing import Union

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
            logging.info("Reading object store credentials from %s", store_credentials_json)
            self._store_credentials = self.load_store_credentials(store_credentials_json)

        # Configure remote options:
        self._remote_options = self.get_remote_options()

        super().__init__(*fs_args, **self._remote_options, **fs_kwargs)

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


    def create_bucket(self,
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


    def get_remote_options(self) -> dict:
        """
        Get the remote options to access the object store.

        Returns
        -------
        remote_options
            Dictionary containing the remote options to access the object store.

        """
        # Create remote options dict from credentials:
        self._remote_options = {
            "anon": self._anon,
            "asynchronous": self._asynchronous,
            "secret": self._store_credentials["secret"],
            "key": self._store_credentials["token"],
            "client_kwargs": {
                "endpoint_url": self._store_credentials["endpoint_url"]
            },
        }

        return self._remote_options
    

    def get_store(self,
                  path: str,
                  **get_store_kwargs
                  ) -> zarr.storage.FsspecStore:
        """
        Get a remote store in a desired bucket using fsspec.

        Parameters
        ----------
        dest: str, default "s3://"
            Protocol prefix to object store.
        **get_store_kwargs
            Kwargs for zarr.storage.FsspecStore().
            See: https://zarr.readthedocs.io/en/stable/api/zarr/storage/index.html#zarr.storage.FsspecStore.

        Returns
        -------
        store, FsspecStore
            A remote store based on fsspec.
        """
        store = zarr.storage.FsspecStore(fs=self, path=path, **get_store_kwargs)

        return store


    def get_mapper(self,
                   bucket: str,
                   prefix: str = "s3://",
                   **get_mapper_kwargs
                   ) -> fsspec.mapping.FSMap:
        """
        Get a MutableMaping interface to the desired bucket.

        Parameters
        ----------
        bucket
            Name of bucket.
        prefix: str, default "s3://"
            Protocol prefix to object store.
        **get_mapper_kwargs
            Kwargs for get_mapper.
            See: https://filesystem-spec.readthedocs.io/en/latest/api.html#fsspec.get_mapper.

        Returns
        -------
        mapper
            Dict-like key-value store.
        """  # noqa adamwa
        mapper = fsspec.get_mapper(
            prefix + bucket, **self._remote_options, **get_mapper_kwargs
        )

        return mapper
