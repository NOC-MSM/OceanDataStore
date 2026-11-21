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
zarr.py

Description:
This module defines functions to send and update data in Zarr stores in
cloud object storage.

Authors:
    - Ollie Tooth
"""

import logging
import warnings
from typing import Any

import dask
import numpy as np
import xarray as xr
from dask.distributed import Client, LocalCluster

from OceanDataStore.cli.exceptions import (
    AppendDimensionError,
    AppendDimensionSizeError,
    ChunkSizeError,
    DimensionNotFound,
    DimensionSizeError,
    ObjectNotFound,
)
from OceanDataStore.cli.object_store import ObjectStoreS3
from OceanDataStore.cli.utils import (
    CaptureWarningsPlugin,
    CloseClientSessionPlugin,
    Timer,
    _preprocess_dataset,
)

logger = logging.getLogger(__name__)


# ======== Define Zarr Validation Functions ======== #
def _validate_inputs(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    variables: list[str] | None,
    append_dim: str,
    grid_filepath: str | None,
    update_coords: dict[str, str] | None,
    rechunk: dict[str, int] | None,
    attrs: dict[str, Any] | None,
    parallel: bool,
    zarr_version: int,
) -> None:
    """
    Validate the types of the inputs used to send or update a Zarr store.

    See ``send_to_zarr`` for a description of the parameters.

    Raises
    ------
    TypeError
        If any input has an invalid type.
    """
    if not isinstance(file, (list, str, xr.Dataset)):
        raise TypeError("file must be a list of strings, a string, or an xarray.Dataset.")
    if not isinstance(bucket, str):
        raise TypeError("bucket must be a string.")
    if not isinstance(object_prefix, str):
        raise TypeError("object_prefix must be a string.")
    if not isinstance(store_credentials_json, str):
        raise TypeError("store_credentials_json must be a string.")
    if variables is not None and (
        not isinstance(variables, list) or not all(isinstance(var, str) for var in variables)
    ):
        raise TypeError("variables must be a list of strings.")
    if not isinstance(append_dim, str):
        raise TypeError("append_dim must be a string.")
    if (grid_filepath is not None) and (not isinstance(grid_filepath, str)):
        raise TypeError("grid_filepath must be a string.")
    if (update_coords is not None) and (not isinstance(update_coords, dict)):
        raise TypeError("update_coords must be a dictionary.")
    if (rechunk is not None) and (not isinstance(rechunk, dict)):
        raise TypeError("rechunk must be a dictionary.")
    if (attrs is not None) and (not isinstance(attrs, dict)):
        raise TypeError("attrs must be a dictionary.")
    if not isinstance(parallel, bool):
        raise TypeError("parallel must be a boolean.")
    if not isinstance(zarr_version, int):
        raise TypeError("zarr_version must be an integer.")


def _check_zarr_store(obj_store: ObjectStoreS3, url: str) -> bool:
    """
    Check if a Zarr store exists at a specified URL path.

    Parameters
    ----------
    obj_store : ObjectStoreS3
        Object store filesystem.
    url : str
        URL path to Zarr store.

    Returns
    -------
    bool
        True if the store exists, False otherwise.
    """
    return obj_store.exists(url.replace("s3://", ""))


def _check_zarr_compatibility(
    data: xr.DataArray | xr.Dataset,
    obj_store: ObjectStoreS3,
    url: str,
    append_dim: str = "time_counter",
    rechunk: dict[str, int] | None = None,
    version: int = 3,
) -> None:
    """
    Check compatibility of data to update an existing Zarr store.

    Parameters
    ----------
    data : xarray.DataArray | xarray.Dataset
        Data used to update the existing Zarr store.
    obj_store : ObjectStoreS3
        Object store filesystem.
    url : str
        URL path to Zarr store.
    append_dim : str, default "time_counter"
        Dimension along which data is appended to the Zarr store.
    rechunk : dict[str, int] | None, default None
        Mapping of dimension names to requested chunk sizes.
    version : int, default 3
        Zarr format version of the store.

    Raises
    ------
    ObjectNotFound
        If no store exists at ``url``.
    FileNotFoundError
        If the store cannot be opened with the given Zarr format version.
    DimensionSizeError
        If a non-append dimension differs in size from the store.
    DimensionNotFound
        If a non-append dimension is missing from the store.
    AppendDimensionError
        If ``data`` starts before the store along ``append_dim``.
    ChunkSizeError
        If ``rechunk`` differs from the store chunks.
    """
    # 1. Check if the object exists:
    if not _check_zarr_store(obj_store=obj_store, url=url):
        raise ObjectNotFound(object_name=url)

    # 2. Check Zarr store compatibility:
    try:
        ds_store = xr.open_zarr(
            store=url,
            storage_options=obj_store.get_storage_options(set_async=True),
            zarr_format=version,
        )
    except FileNotFoundError as e:
        raise FileNotFoundError(f"zarr version {version} is not compatible with the store: {e}") from e

    # 3. Check if core dimensions exist & sizes are compatible:
    dims_data = {dim: data.sizes[dim] for dim in data.dims if dim != append_dim}
    for dim, value in dims_data.items():
        if dim in ds_store.dims:
            if value != ds_store.sizes[dim]:
                raise DimensionSizeError(dim=dim, size=value, expected_size=ds_store.sizes[dim])
        else:
            raise DimensionNotFound(dim=dim, object_name=url)

    # 4. Check if append dimension values are compatible:
    if data[append_dim][0] < ds_store[append_dim][0]:
        raise AppendDimensionError(dim=append_dim)

    # 5. Check if specified chunks are compatible:
    if rechunk is not None:
        for dim, value in rechunk.items():
            if (dim in ds_store.dims) and (value != ds_store.chunks[dim][0]):
                raise ChunkSizeError(chunks=rechunk, store_chunks=ds_store.chunks)


# ======== Define Zarr Writer Functions ======== #
def _write_to_zarr(
    data: xr.DataArray | xr.Dataset,
    obj_store: ObjectStoreS3,
    url: str,
    version: int = 3,
) -> None:
    """
    Write data to a new Zarr store in cloud object storage.

    If a store already exists at ``url``, writing is skipped.

    Parameters
    ----------
    data : xarray.DataArray | xarray.Dataset
        Data to write to the Zarr store.
    obj_store : ObjectStoreS3
        Object store filesystem.
    url : str
        URL path to Zarr store.
    version : int, default 3
        Zarr format version of the store.
    """
    # Convert DataArrays to Datasets:
    if isinstance(data, xr.DataArray):
        var = data.name
        data = data.to_dataset()
    else:
        var = None

    if _check_zarr_store(obj_store=obj_store, url=url):
        logger.info("Skipping Variable: Store already exists at %s", url)
    else:
        with Timer(action="send", dest=url, var=var), warnings.catch_warnings():
            # Catch consolidated metadata warnings:
            warnings.simplefilter(action="ignore", category=UserWarning)
            data.to_zarr(
                store=url,
                storage_options=obj_store.get_storage_options(set_async=True),
                mode="w",
                zarr_format=version,
            )


def _append_to_zarr(
    data: xr.DataArray | xr.Dataset,
    obj_store: ObjectStoreS3,
    url: str,
    append_dim: str = "time_counter",
    version: int = 3,
) -> None:
    """
    Append data to an existing Zarr store in cloud object storage.

    Parameters
    ----------
    data : xarray.DataArray | xarray.Dataset
        Data to append to the existing Zarr store.
    obj_store : ObjectStoreS3
        Object store filesystem.
    url : str
        URL path to Zarr store.
    append_dim : str, default "time_counter"
        Dimension along which to append data.
    version : int, default 3
        Zarr format version of the store.
    """
    with Timer(action="append", dest=url), warnings.catch_warnings():
        # Catch consolidated metadata warnings:
        warnings.simplefilter(action="ignore", category=UserWarning)
        data.to_zarr(
            store=url,
            storage_options=obj_store.get_storage_options(set_async=True),
            append_dim=append_dim,
            zarr_format=version,
        )


def _replace_in_zarr(
    data: xr.Dataset,
    obj_store: ObjectStoreS3,
    url: str,
    region: dict[str, slice],
    version: int = 3,
) -> None:
    """
    Replace a region of an existing Zarr store in cloud object storage.

    Variables which do not include the region dimension are dropped
    before writing.

    Parameters
    ----------
    data : xarray.Dataset
        Data used to replace values in the existing Zarr store.
    obj_store : ObjectStoreS3
        Object store filesystem.
    url : str
        URL path to Zarr store.
    region : dict[str, slice]
        Mapping of the append dimension name to the index slice of the
        Zarr store to replace.
    version : int, default 3
        Zarr format version of the store.
    """
    # Drop variables w/o append dimension:
    append_dim = next(iter(region.keys()))
    drop_list = [var for var in data.variables if append_dim not in data[var].dims]
    data = data.drop_vars(drop_list)

    with Timer(action="replace", dest=url), warnings.catch_warnings():
        # Catch consolidated metadata warnings:
        warnings.simplefilter(action="ignore", category=UserWarning)
        data.to_zarr(
            store=url,
            storage_options=obj_store.get_storage_options(set_async=True),
            region=region,
            zarr_format=version,
        )


def _update_zarr_store(
    data: xr.DataArray | xr.Dataset,
    obj_store: ObjectStoreS3,
    url: str,
    append_dim: str = "time_counter",
    rechunk: dict[str, int] | None = None,
    version: int = 3,
) -> None:
    """
    Update an existing Zarr store by replacing and/or appending values.

    Source values which overlap the store along ``append_dim`` are
    replaced and remaining source values are appended. A DataArray whose
    variable does not exist in the store is written as a new variable.

    Parameters
    ----------
    data : xarray.DataArray | xarray.Dataset
        Data used to update the existing Zarr store.
    obj_store : ObjectStoreS3
        Object store filesystem.
    url : str
        URL path to Zarr store.
    append_dim : str, default "time_counter"
        Dimension along which to replace and/or append data.
    rechunk : dict[str, int] | None, default None
        Mapping of dimension names to requested chunk sizes.
    version : int, default 3
        Zarr format version of the store.

    Raises
    ------
    AppendDimensionSizeError
        If overlapping source values are not all found in the store.
    """
    # Convert DataArrays to Datasets:
    if isinstance(data, xr.DataArray):
        var = data.name
        ds_source = data.to_dataset()
    else:
        var = None
        ds_source = data

    # Check source Dataset compatibility with existing store:
    _check_zarr_compatibility(
        data=ds_source,
        obj_store=obj_store,
        url=url,
        append_dim=append_dim,
        rechunk=rechunk,
        version=version,
    )
    logger.info("Passed Compatibility Checks for store %s", url)

    ds_target = xr.open_zarr(
        store=url,
        storage_options=obj_store.get_storage_options(set_async=True),
        zarr_format=version,
    )

    if (var in ds_target.data_vars) or (var is None):
        # === Update existing Zarr store === #
        # Extract source & target append dimension values:
        target_append_dim = ds_target[append_dim].values
        source_append_dim = ds_source[append_dim].values

        # Determine intersection between source & target append dimensions:
        intersect_append_dim = np.intersect1d(source_append_dim, target_append_dim)

        if intersect_append_dim.size != 0:
            # == Intersection exists -> replace overlapping values in target store == #

            # Ensure all overlapping values exist along target append dimension:
            overlap_append_dim = (source_append_dim <= target_append_dim[-1]).sum()
            if intersect_append_dim.size != overlap_append_dim:
                raise AppendDimensionSizeError(
                    dim=append_dim, size=overlap_append_dim, expected_size=intersect_append_dim.size
                )

            # Determine source and target append dimension indices of overlap:
            target_ind_min = np.flatnonzero(target_append_dim == source_append_dim[0])[0]
            target_ind_max = target_append_dim.size
            source_ind_min = 0
            source_ind_max = target_ind_max - target_ind_min
            source_ind_size = source_append_dim.size

            # 1. Replace overlapping values in target store:
            logger.info(
                "Updating %s along %s from %s to %s.",
                url,
                append_dim,
                target_append_dim[target_ind_min],
                target_append_dim[target_ind_max - 1],
            )
            _replace_in_zarr(
                data=ds_source.isel({append_dim: slice(source_ind_min, source_ind_max)}),
                obj_store=obj_store,
                url=url,
                region={append_dim: slice(target_ind_min, target_ind_max)},
                version=version,
            )

            # 2. Append new values to target store:
            if source_ind_size > source_ind_max:
                logger.info(
                    "Appending to %s along %s from %s to %s.",
                    url,
                    append_dim,
                    source_append_dim[source_ind_max],
                    source_append_dim[source_ind_size - 1],
                )
                _append_to_zarr(
                    data=ds_source.isel({append_dim: slice(source_ind_max, source_ind_size)}),
                    obj_store=obj_store,
                    url=url,
                    append_dim=append_dim,
                    version=version,
                )

        else:
            # == No intersection -> append all source values to target store == #
            _append_to_zarr(
                data=ds_source,
                obj_store=obj_store,
                url=url,
                append_dim=append_dim,
                version=version,
            )
    else:
        # == Add new variable to Zarr store == #
        logger.info("Sending Variable %s", var)
        _write_to_zarr(
            data=ds_source,
            obj_store=obj_store,
            url=url,
            version=version,
        )


def _send_to_zarr(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    variables: list[str] | None = None,
    append_dim: str = "time_counter",
    grid_filepath: str | None = None,
    update_coords: dict[str, str] | None = None,
    rechunk: dict[str, int] | None = None,
    attrs: dict[str, Any] | None = None,
    parallel: bool = False,
    zarr_version: int = 3,
) -> None:
    """
    Write data to a new Zarr store in cloud object storage.

    See ``send_to_zarr`` for a description of the parameters.
    ``parallel`` determines whether files are opened and preprocessed
    in parallel using ``dask.delayed``.
    """
    _validate_inputs(
        file=file,
        bucket=bucket,
        object_prefix=object_prefix,
        store_credentials_json=store_credentials_json,
        variables=variables,
        append_dim=append_dim,
        grid_filepath=grid_filepath,
        update_coords=update_coords,
        rechunk=rechunk,
        attrs=attrs,
        parallel=parallel,
        zarr_version=zarr_version,
    )

    # === Initialise Synchronous Object Store === #
    logger.info("Reading object store credentials from %s", store_credentials_json)
    obj_store = ObjectStoreS3(anon=False, asynchronous=False, store_credentials_json=store_credentials_json)

    # === Preprocess Data === #
    ds_filepath = _preprocess_dataset(
        file=file,
        rechunk=rechunk,
        append_dim=append_dim,
        update_coords=update_coords,
        grid_filepath=grid_filepath,
        attrs=attrs,
        parallel=parallel,
    )
    if variables is None:
        variables = list(ds_filepath.data_vars)

    # === Send Dataset to Zarr store === #
    url = f"s3://{bucket}/{object_prefix}"
    logger.info("Sending Dataset to %s", url)
    _write_to_zarr(
        data=ds_filepath[variables],
        obj_store=obj_store,
        url=url,
        version=zarr_version,
    )

    # Release resources to avoid memory leaks:
    ds_filepath.close()


def _update_zarr(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    append_dim: str,
    variables: list[str] | None = None,
    grid_filepath: str | None = None,
    update_coords: dict[str, str] | None = None,
    rechunk: dict[str, int] | None = None,
    attrs: dict[str, Any] | None = None,
    parallel: bool = False,
    zarr_version: int = 3,
) -> None:
    """
    Update an existing Zarr store in cloud object storage.

    See ``update_zarr`` for a description of the parameters.
    ``parallel`` determines whether files are opened and preprocessed
    in parallel using ``dask.delayed``.
    """
    _validate_inputs(
        file=file,
        bucket=bucket,
        object_prefix=object_prefix,
        store_credentials_json=store_credentials_json,
        variables=variables,
        append_dim=append_dim,
        grid_filepath=grid_filepath,
        update_coords=update_coords,
        rechunk=rechunk,
        attrs=attrs,
        parallel=parallel,
        zarr_version=zarr_version,
    )

    # === Initialise Synchronous Object Store === #
    logger.info("Reading object store credentials from %s", store_credentials_json)
    obj_store = ObjectStoreS3(anon=False, asynchronous=False, store_credentials_json=store_credentials_json)

    # === Preprocess Data === #
    ds_filepath = _preprocess_dataset(
        file=file,
        rechunk=rechunk,
        append_dim=append_dim,
        update_coords=update_coords,
        grid_filepath=grid_filepath,
        attrs=attrs,
        parallel=parallel,
    )

    if variables is None:
        variables = list(ds_filepath.data_vars)
    # Consider variables with append dimension only:
    variables = [var for var in variables if append_dim in ds_filepath[var].dims]

    # === Update Existing Zarr store === #
    url = f"s3://{bucket}/{object_prefix}"
    logger.info("Updating Dataset at %s", url)
    _update_zarr_store(
        data=ds_filepath[variables],
        obj_store=obj_store,
        url=url,
        append_dim=append_dim,
        rechunk=rechunk,
        version=zarr_version,
    )

    # Release resources to avoid memory leaks:
    ds_filepath.close()


# ============ Define Public Functions ============ #
def send_to_zarr(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    variables: list[str] | None = None,
    append_dim: str | None = None,
    grid_filepath: str | None = None,
    update_coords: dict[str, str] | None = None,
    rechunk: dict[str, int] | None = None,
    attrs: dict[str, Any] | None = None,
    client: Client | None = None,
    dask_config_kwargs: dict[str, Any] | None = None,
    dask_cluster_kwargs: dict[str, Any] | None = None,
    zarr_version: int = 3,
) -> None:
    """
    Write data to a new Zarr store in cloud object storage.

    Optionally uses an existing dask Client or a new dask LocalCluster to
    open, preprocess and write data. If a store already exists at the
    destination, writing is skipped.

    Parameters
    ----------
    file : list[str] | str | xarray.Dataset
        Glob pattern, filepath or list of filepaths to netCDF file(s).
        Users can also pass a single xarray.Dataset directly.
    bucket : str
        Name of the bucket in the object store. Bucket names can contain only
        lowercase letters, numbers, dots (.), and hyphens (-).
    object_prefix : str
        Prefix of the Zarr store in the bucket.
    store_credentials_json : str
        Path to the JSON file containing the object store credentials.
    variables : list[str] | None, default None
        Variables to send. If None, all data variables will be sent.
    append_dim : str | None, default None
        Name of the dimension along which to concatenate multi-file
        datasets. If None, 'time_counter' is used.
    grid_filepath : str | None, default None
        Path to the model grid file used to update coordinate variables.
    update_coords : dict[str, str] | None, default None
        Mapping of dataset coordinate variable names to model grid file
        variable names used to update coordinates.
    rechunk : dict[str, int] | None, default None
        Mapping of dimension names to chunk sizes. If None, on-disk
        chunks are used.
    attrs : dict[str, Any] | None, default None
        Global attributes to add to the dataset.
    client : dask.distributed.Client | None, default None
        Existing dask Client. Note that this client is shut down on completion.
    dask_config_kwargs : dict[str, Any] | None, default None
        Dask configuration settings passed to ``dask.config.set()``.
        Ignored if ``client`` is provided.
    dask_cluster_kwargs : dict[str, Any] | None, default None
        Keyword arguments passed to ``dask.distributed.LocalCluster()``.
        Ignored if ``client`` is provided. If both are None, dask is not
        used to parallelise the workflow.
    zarr_version : int, default 3
        Zarr format version of the store (2 or 3).

    Raises
    ------
    TypeError
        If any input has an invalid type.
    ValueError
        If a filepath does not have a .nc extension or ``update_coords``
        is given without ``grid_filepath``.
    FileNotFoundError
        If a glob pattern matches no files.
    """
    # === Default Arguments === #
    if append_dim is None:
        append_dim = "time_counter"

    send_kwargs = {
        "file": file,
        "bucket": bucket,
        "object_prefix": object_prefix,
        "store_credentials_json": store_credentials_json,
        "variables": variables,
        "append_dim": append_dim,
        "grid_filepath": grid_filepath,
        "update_coords": update_coords,
        "rechunk": rechunk,
        "attrs": attrs,
        "zarr_version": zarr_version,
    }

    if client is not None:
        # === Send to Zarr store with existing Dask Client === #
        logger.info("Using existing Dask Cluster @ Client: %s", client.dashboard_link)
        # Register plugins: capture UserWarnings when rechunking data & close aiohttp.ClientSessions:
        client.register_plugin(CaptureWarningsPlugin())
        client.register_plugin(CloseClientSessionPlugin())

        _send_to_zarr(**send_kwargs, parallel=True)

        client.shutdown()
        logger.info("Existing Dask Client has been shutdown.")

    elif dask_cluster_kwargs is not None:
        # === Send to Zarr store with Dask === #
        if dask_config_kwargs is not None:
            dask.config.set(dask_config_kwargs)
            logger.info("Updated dask configuration settings.")

        with LocalCluster(**dask_cluster_kwargs) as cluster, Client(cluster) as local_client:
            logger.info(
                "Created LocalCluster with %s workers @ Client: %s",
                dask_cluster_kwargs["n_workers"],
                local_client.dashboard_link,
            )
            # Register plugins: capture UserWarnings when rechunking data & close aiohttp.ClientSessions:
            local_client.register_plugin(CaptureWarningsPlugin())
            local_client.register_plugin(CloseClientSessionPlugin())

            _send_to_zarr(**send_kwargs, parallel=True)

        logger.info("Dask Cluster has been shutdown.")

    else:
        # === Send to Zarr store without Dask === #
        _send_to_zarr(**send_kwargs, parallel=False)


def update_zarr(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    variables: list[str] | None = None,
    append_dim: str | None = None,
    grid_filepath: str | None = None,
    update_coords: dict[str, str] | None = None,
    rechunk: dict[str, int] | None = None,
    attrs: dict[str, Any] | None = None,
    client: Client | None = None,
    dask_config_kwargs: dict[str, Any] | None = None,
    dask_cluster_kwargs: dict[str, Any] | None = None,
    zarr_version: int = 3,
) -> None:
    """
    Update data in an existing Zarr store in cloud object storage.

    Source values overlapping the store along ``append_dim`` are
    replaced and remaining values are appended. Only variables including
    ``append_dim`` are updated. Optionally uses an existing dask Client
    or a new dask LocalCluster.

    Parameters
    ----------
    file : list[str] | str | xarray.Dataset
        Glob pattern, filepath or list of filepaths to netCDF file(s).
        Users can also pass a single xarray.Dataset directly.
    bucket : str
        Name of the bucket in the object store. Bucket names can contain only
        lowercase letters, numbers, dots (.), and hyphens (-).
    object_prefix : str
        Prefix of the Zarr store in the bucket.
    store_credentials_json : str
        Path to the JSON file containing the object store credentials.
    variables : list[str] | None, default None
        Variables to update. If None, all data variables including
        ``append_dim`` will be updated.
    append_dim : str | None, default None
        Name of the dimension along which to replace and/or append data.
        If None, 'time_counter' is used.
    grid_filepath : str | None, default None
        Path to the model grid file used to update coordinate variables.
    update_coords : dict[str, str] | None, default None
        Mapping of dataset coordinate variable names to model grid file
        variable names used to update coordinates.
    rechunk : dict[str, int] | None, default None
        Mapping of dimension names to chunk sizes. Must be consistent
        with the chunks of the existing store.
    attrs : dict[str, Any] | None, default None
        Global attributes to add to the dataset.
    client : dask.distributed.Client | None, default None
        Existing dask Client. Note that this client is shut down on completion.
    dask_config_kwargs : dict[str, Any] | None, default None
        Dask configuration settings passed to ``dask.config.set()``.
        Ignored if ``client`` is provided.
    dask_cluster_kwargs : dict[str, Any] | None, default None
        Keyword arguments passed to ``dask.distributed.LocalCluster()``.
        Ignored if ``client`` is provided. If both are None, dask is not
        used to parallelise the workflow.
    zarr_version : int, default 3
        Zarr format version of the store (2 or 3).

    Raises
    ------
    ObjectNotFound
        If no store exists at the destination.
    DimensionSizeError
        If a non-append dimension differs in size from the store.
    DimensionNotFound
        If a non-append dimension is missing from the store.
    AppendDimensionError
        If the source data starts before the store along ``append_dim``.
    AppendDimensionSizeError
        If overlapping source values are not all found in the store.
    ChunkSizeError
        If ``rechunk`` differs from the store chunks.
    """
    # === Default Arguments === #
    if append_dim is None:
        append_dim = "time_counter"

    update_kwargs = {
        "file": file,
        "bucket": bucket,
        "object_prefix": object_prefix,
        "store_credentials_json": store_credentials_json,
        "variables": variables,
        "append_dim": append_dim,
        "grid_filepath": grid_filepath,
        "update_coords": update_coords,
        "rechunk": rechunk,
        "attrs": attrs,
        "zarr_version": zarr_version,
    }

    if client is not None:
        # === Update Zarr store with existing Dask Client === #
        logger.info("Using existing Dask Cluster @ Client: %s", client.dashboard_link)
        # Register plugins: capture UserWarnings when rechunking data & close aiohttp.ClientSessions:
        client.register_plugin(CaptureWarningsPlugin())
        client.register_plugin(CloseClientSessionPlugin())

        _update_zarr(**update_kwargs, parallel=True)

        client.shutdown()
        logger.info("Existing Dask Client has been shutdown.")

    elif dask_cluster_kwargs is not None:
        # === Update Zarr store with Dask === #
        if dask_config_kwargs is not None:
            dask.config.set(dask_config_kwargs)
            logger.info("Updated dask configuration settings.")

        with LocalCluster(**dask_cluster_kwargs) as cluster, Client(cluster) as local_client:
            logger.info(
                "Created LocalCluster with %s workers @ Client: %s",
                dask_cluster_kwargs["n_workers"],
                local_client.dashboard_link,
            )
            # Register plugins: capture UserWarnings when rechunking data & close aiohttp.ClientSessions:
            local_client.register_plugin(CaptureWarningsPlugin())
            local_client.register_plugin(CloseClientSessionPlugin())

            _update_zarr(**update_kwargs, parallel=True)

        logger.info("Dask Cluster has been shutdown.")

    else:
        # === Update Zarr store without Dask === #
        _update_zarr(**update_kwargs, parallel=False)
