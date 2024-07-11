"""S3 object store class."""
import io
import json
import logging
import os
from typing import IO, List, Union

import fsspec
import numpy as np
import s3fs

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


    def get_signed_url(
        self,
        bucket: str,
        object_name: str,
        expiration: int = 3600) -> str:
        """
        Get a signed URL to access an object in the object store.

        Parameters
        ----------
        bucket (str):
            Bucket name.
        object_name (str):
            Object name.
        expiration (int, optional):
            Expiration time in seconds. Defaults to 3600.

        Returns
        -------
        signed_url
            Signed URL to access the object in the object store.
        """

        signed_url = self.url(bucket + '/' + object_name, expires=expiration)
        return signed_url

    def create_bucket(self, bucket: str, **kwargs) -> None:
        """
        Create a bucket in the object store.

        Parameters
        ----------
        bucket
            Bucket to create. Bucket names can consist only of lowercase letters, numbers, dots (.), and hyphens (-).
        """
        try:
            return self.mkdir(bucket, **kwargs)
        except FileExistsError:
            logging.info("Bucket '%s' already exists.", bucket)

    def get_remote_options(self, override: bool = False) -> dict:
        """
        Get the remote options of the object store.

        Parameters
        ----------
        override
            Flag to create remote_options from scratch (True)
            or to simply retrieve the current dict (False).

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

    def get_mapper(
        self, bucket: str, prefix: str = "s3://", **get_mapper_kwargs
    ) -> fsspec.mapping.FSMap:
        """
        Make a MutableMaping interface to the desired bucket.

        Parameters
        ----------
        bucket
            Name of the bucket to place the file in.
        prefix: str, default "s3://"
            Protocol prefix
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

    from typing import Union

    def write_file_to_bucket(
        self,
        path: Union[str, os.PathLike, IO],
        bucket: str,
        file_name: str,
        chunk_size: int = -1,
        parallel: bool = False,
    ) -> None:
        """
        Write to a bucket of the object store.

        Parameters
        ----------
        path
            Absolute or relative filepath of the file to be written to the object store,
            or file-like object to be written to the object store.
        bucket
            Name of the bucket to place the file in.
        file_name
            Name that will be used to identify the file in the bucket.
        chunk_size
            Size of the chunk (in bytes) to read/write at once.
            If the chunk size is -1, the file will be read/written at once.
        parallel
            Flag to enable parallel writing (True) or not (False).
        """
        assert (
            bucket.split(os.path.sep, 1)[0] in self.get_bucket_list()
        ), f'Bucket "{bucket}" does not exist.'

        if isinstance(path, str) or isinstance(path, os.PathLike):
            assert os.path.isfile(path), f'"{path}" is not a file.'
            file_size = os.path.getsize(path)
        elif isinstance(path, io.IOBase):
            file_size = path.seek(0, os.SEEK_END)
        else:
            raise ValueError(f'"{path}" is not file-like, path-like or a string.')

        # create the empty file
        dest_path = os.path.join(bucket, file_name)
        self.open(dest_path, mode="wb", s3=dict(profile="default")).close()

        # create the chunks offsets and lengths
        chks = self._create_chunks_offsets_lengths(file_size, chunk_size)

        # write the file to the bucket
        self._write_to_bucket(path, dest_path, chks, parallel)

    def _write_to_bucket(
        self,
        path: Union[str, os.PathLike, IO],
        dest_path: str,
        chunks_offsets_lengths: dict,
        parallel: bool,
    ) -> None:
        """
        Write to a bucket of the object store.

        Parameters
        ----------
        path
            Absolute or relative filepath of the file to be written to the object store,
            or file-like object to be written to the object store.
        dest_path
            Name of the bucket to place the file in.
        chunks_offsets_lengths
            Dictionary containing the chunk offsets and lengths
            of the file to be written to the object store.
        parallel
            Flag to enable parallel writing (True) or not (False).
        """
        n_chunks = len(chunks_offsets_lengths)

        # Arguments to be fed to the map
        multi_part_files = [f"{dest_path}.part{i}" for i in range(n_chunks)]
        chks_offsets = [
            chunks_offsets_lengths[chk]["offset"] for chk in chunks_offsets_lengths
        ]
        chks_lengths = [
            chunks_offsets_lengths[chk]["length"] for chk in chunks_offsets_lengths
        ]
        paths = [path] * n_chunks

        if parallel:
            import dask

            dask.compute(
                list(
                    map(
                        dask.delayed(self._write_chunk),
                        paths,
                        multi_part_files,
                        chks_offsets,
                        chks_lengths,
                    )
                )
            )
        else:
            list(
                map(
                    self._write_chunk,
                    paths,
                    multi_part_files,
                    chks_offsets,
                    chks_lengths,
                )
            )

        if n_chunks > 1:
            # Remove any partial uploads in the bucket associated with the file
            # Create single S3 file from list of S3 files
            self.merge(dest_path, multi_part_files)
            # Remove any partial uploads in the bucket associated with the file
            self.rm(multi_part_files)

    def __open(self, path: str | os.PathLike | IO, mode: str = "rb") -> IO:
        """
        Open a file using a bespoke interface.

        Parameters
        ----------
        path
            Absolute or relative filepath of the file to be opened,
            or file-like object to be opened.
        mode
            File open mode.

        Returns
        -------
        filelike object
        """
        if isinstance(path, str) or isinstance(path, os.PathLike):
            return open(path, mode)
        elif isinstance(path, io.IOBase):
            # filelike object
            return path
        else:
            raise ValueError(f"Unsupported file type: {type(path)}")

    def _write_chunk(
        self, path_read, path_write, chunk_offset: int, chunk_length: int
    ) -> None:
        """
        Write a chunk to an open file.

        Parameters
        ----------
        path_read
            File to read from.
        path_write
            File to write to.
        chunk_offset
            Offset of the chunk (in bytes).
        chunk_length
            Length of the chunk (in bytes).
        """
        # Read the chunk
        with self.__open(path_read, mode="rb") as f:
            f.seek(chunk_offset, 0)
            bytechunk = f.read(chunk_length)

        # Write the chunk
        with self.open(path_write, mode="wb", s3=dict(profile="default")) as f:
            f.write(bytechunk)

    def _create_chunks_offsets_lengths(self, nbytes, chunk_size: int) -> dict:
        """
        Create the chunks offsets and lengths for a file with nbytes given the chunk_size.

        Parameters
        ----------
        nbytes
            Number of bytes of the file.
        chunk_size
            Size of the chunk (in bytes).

        Returns
        -------
        chunks_offsets_lengths
            Dictionary containing the chunks offsets and lengths.
        """
        chunks_offsets_lengths = {}

        if chunk_size == -1:
            chunk_size = nbytes

        # Calculate the number of chunks
        nchunks = int(np.ceil(nbytes / chunk_size))

        # Calculate the chunks offsets and length
        for i in range(nchunks):
            chunks_offsets_lengths[i] = {
                "offset": i * chunk_size,
                "length": chunk_size,
            }

        return chunks_offsets_lengths
