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
import s3fs
import fsspec
import logging

from typing import List, Union

class ObjectStoreS3(s3fs.S3FileSystem):
    """
    S3 object store.

    Parameters
    ----------
    s3fs
        _description_
    """

    def __init__(
        self,
        anon: bool = False,
        store_credentials_json: Union[str, None] = None,
        secret: Union[str, None] = None,
        key: Union[str, None] = None,
        endpoint_url: Union[str, None] = None,
        *fs_args,
        **fs_kwargs,
    ) -> None:
        """
        Initialize the S3 object store.

        Parameters
        ----------
        anon, optional
            _description_, by default False
        store_credentials_json, optional
            _description_, by default None
        secret, optional
            _description_, by default None
        key, optional
            _description_, by default None
        endpoint_url, optional
            _description_, by default None
        """
        self._anon = anon
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
            self._store_credentials = self.load_store_credentials(
                store_credentials_json
            )

        self._remote_options = self.get_remote_options(override=True)

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
                `secret` and `endpoint_url` keys used
            to access the object store.
        """
        try:
            with open(path) as f:
                store_credentials = json.load(f)
        except Exception as error:
            raise Exception(error)

        for key in ["token", "secret", "endpoint_url"]:
            if key not in store_credentials:
                logging.info("-" * 79)
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

    def get_remote_options(self,
                           override: bool = False
                           ) -> dict:
        """
        Get the remote options of the object store.

        Parameters
        ----------
        override
            Create remote_options from scratch (True)
            or retrieve the current dict (False).

        Returns
        -------
        remote_options
            Dictionary containing the remote options of the object store.

        """
        if override:
            self._remote_options = {
                "anon": self._anon,
                "secret": self._store_credentials["secret"],
                "key": self._store_credentials["token"],
                "client_kwargs": {
                    "endpoint_url": self._store_credentials["endpoint_url"]
                },
            }

        return self._remote_options


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

    def get_bucket_list(self) -> List[str]:
        """
        Get the list of buckets in the object store.

        Returns
        -------
        bucket_list
            List of the object store buckets.
        """
        return self.ls("/")
