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
# -- Import Python Modules -- #
import logging
import warnings
from typing import Optional

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
    _preprocess_dataset,
    timer,
)


# ======== Define Zarr Validation Functions ======== #
def _check_zarr_store(
    obj_store: ObjectStoreS3,
    url: str
) -> bool:
    """
    Check if a Zarr store exists at a specified URL path.

    Parameters
    ----------
    obj_store: ObjectStoreS3
        ObjectStoreS3 remote filesystem.
    url: str
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
    rechunk: Optional[dict] = None,
    version: int = 3,
) -> None:
    """
    Check compatibility of DataArray or Dataset to update existing
    Zarr store in cloud object storage.

    Parameters
    ----------
    data: xr.DataArray | xr.Dataset
        DataArray or DataSet to update existing Zarr store with.
    obj_store: ObjectStoreS3
        ObjectStoreS3 remote filesystem.
    url: str
        URL path to Zarr store.
    append_dim: bool, default="time_counter"
        Dimension to append data to existing Zarr store.
    rechunk: Optional[dict], default=None
        Mapping to rechunk dimensions.
    version: int, default=3
        Zarr version to use.
    """
    # 1. Check if the object exists:
    if not _check_zarr_store(obj_store=obj_store, url=url):
        raise ObjectNotFound(object_name=url)
    
    # 2. Check Zarr store compatibility:
    try:
        ds_store = xr.open_zarr(store=url,
                                storage_options=obj_store.get_storage_options(set_async=True),
                                zarr_format=version
                                )
    except Exception as e:
        raise FileNotFoundError(f"zarr version {version} is not compatible with the store: {e}")
    
    # 3. Check if core dimensions exist & size are compatible:
    dims_data = {dim : data.sizes[dim] for dim in data.dims if dim != append_dim}
    for dim in dims_data:
        if dim in ds_store.dims:
            if dims_data[dim] != ds_store.sizes[dim]:
                raise DimensionSizeError(dim=dim, size=dims_data[dim], expected_size=ds_store.sizes[dim])
        else:
            raise DimensionNotFound(dim=dim, object_name=url)

    # 4. Check if append dimension values are compatible:
    if (data[append_dim][0] < ds_store[append_dim][0]):
        raise AppendDimensionError(dim=append_dim)
    
    # 5. Check if specified chunks are compatible:
    if rechunk is not None:
        for dim in rechunk:
            if dim in ds_store.dims:
                if rechunk[dim] != ds_store.chunks[dim][0]:
                    raise ChunkSizeError(chunks=rechunk, store_chunks=ds_store.chunks)


# ======== Define Zarr Writer Functions ======== #
def _write_to_zarr(
    data: xr.DataArray | xr.Dataset,
    obj_store: ObjectStoreS3,
    url: str,
    version: int = 3,
) -> None:
    """
    Write DataArray or Dataset to Zarr store in cloud
    object storage.

    Parameters
    ----------
    data: xr.DataArray | xr.Dataset
        DataArray or DataSet to write to Zarr store.
    obj_store: ObjectStoreS3
        ObjectStoreS3 remote filesystem.
    url: str
        URL path to Zarr store.
    version: int, default=3
        Zarr version to use.
    """
    # Convert DataArrays to Datasets:
    if isinstance(data, xr.DataArray):
        var = data.name
        data = data.to_dataset()
    else:
        var = None

    # Write Dataset to Zarr store in Object Store:
    if _check_zarr_store(obj_store=obj_store, url=url):
        logging.info(f"Skipping Variable: Store already exists at {url}")

    else:
        with timer(action='send', dest=url, var=var):
            # Catch consolidated metadata warnings:
            with warnings.catch_warnings():
                warnings.simplefilter(action="ignore", category=UserWarning)
                data.to_zarr(store=url,
                             storage_options=obj_store.get_storage_options(set_async=True),
                             mode="w",
                             zarr_format=version
                             )


def _append_to_zarr(
    data: xr.DataArray | xr.Dataset,
    obj_store: ObjectStoreS3,
    url: str,
    append_dim: str = "time_counter",
    version: int = 3,
) -> None:
    """
    Append DataArray or Dataset to existing Zarr store in
    cloud object storage.

    Parameters
    ----------
    data: xr.DataArray | xr.Dataset
        DataArray or DataSet to append to existing Zarr store.
    obj_store: ObjectStoreS3
        ObjectStoreS3 remote filesystem.
    url: str
        URL path to Zarr store.
    append_dim: str, default="time_counter"
        Dimension to append data to existing Zarr store.
    version: int, default=3
        Zarr version to use.
    """
    with timer(action='append', dest=url):
        # Catch consolidated metadata warnings:
        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore", category=UserWarning)
            data.to_zarr(store=url,
                         storage_options=obj_store.get_storage_options(set_async=True),
                         append_dim=append_dim,
                         zarr_format=version
                         )


def _replace_in_zarr(
    data: xr.DataArray | xr.Dataset,
    obj_store: ObjectStoreS3,
    url: str,
    region: dict,
    version: int = 3,
) -> None:
    """
    Append DataArray or Dataset to existing Zarr store in
    cloud object storage.

    Parameters
    ----------
    data: xr.DataArray | xr.Dataset
        DataArray or DataSet to append to existing Zarr store.
    obj_store: ObjectStoreS3
        ObjectStoreS3 remote filesystem.
    url: str
        URL path to Zarr store.
    region: dict
        Region of existing Zarr store to replace data.
    version: int, default=3
        Zarr version to use.
    """
    # Drop variables w/o append dimension:
    append_dim = list(region.keys())[0]
    drop_list = [var for var in data.variables if append_dim not in data[var].dims]
    data = data.drop_vars(drop_list)

    with timer(action='replace', dest=url):
        # Catch consolidated metadata warnings:
        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore", category=UserWarning)
            data.to_zarr(store=url,
                         storage_options=obj_store.get_storage_options(set_async=True),
                         region=region,
                         zarr_format=version
                         )


def _update_zarr_store(
    data: xr.DataArray | xr.Dataset,
    obj_store: ObjectStoreS3,
    url: str,
    append_dim: str = "time_counter",
    rechunk: Optional[dict] = None,
    version: int = 3,
) -> None:
    """
    Update an existing Zarr store in object storage by replacing
    existing values and/or appending new values.

    Parameters
    ----------
    data: xr.DataArray | xr.Dataset
        DataArray or DataSet to update existing Zarr store with.
    obj_store: ObjectStoreS3
        ObjectStoreS3 remote filesystem.
    url: str
        URL path to Zarr store.
    append_dim: str, default="time_counter"
        Dimension to append data to existing Zarr store.
    rechunk: Optional[dict], default=None
        Mapping to rechunk dimensions.
    version: int, default=3
        Zarr version to use.
    """
    # Convert DataArrays to Datasets:
    if isinstance(data, xr.DataArray):
        var = data.name
        ds_source = data.to_dataset()
    else:
        var = None
        ds_source = data

    # Check source Dataset compatibility with existing store:
    _check_zarr_compatibility(data=ds_source,
                              obj_store=obj_store,
                              url=url,
                              append_dim=append_dim,
                              rechunk=rechunk,
                              version=version
                              )
    logging.info(f"Passed Compatibility Checks for store {url}")

    # === Update existing variable in Zarr Store === #
    # Extract source & target append dimension values:
    ds_target = xr.open_zarr(store=url,
                             storage_options=obj_store.get_storage_options(set_async=True),
                             zarr_format=version
                             )

    if (var in ds_target.data_vars) or (var is None):

        # === Updating existing Zarr store === #
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
                raise AppendDimensionSizeError(dim=append_dim, size=overlap_append_dim, expected_size=intersect_append_dim.size)
            
            # Determine source and target append dimension indices of overlap:
            target_ind_min = np.flatnonzero(target_append_dim == source_append_dim[0])[0]
            target_ind_max = target_append_dim.size
            source_ind_min = 0
            source_ind_max = target_ind_max - target_ind_min
            source_ind_size = source_append_dim.size

            # 1. Replace overlapping values in target store:
            logging.info(f"Updating {url} along {append_dim} from {target_append_dim[target_ind_min]} to {target_append_dim[target_ind_max - 1]}.")
            _replace_in_zarr(data=ds_source.isel({append_dim : slice(source_ind_min, source_ind_max)}),
                             obj_store=obj_store,
                             url=url,
                             region={append_dim : slice(target_ind_min, target_ind_max)},
                             version=version,
                             )

            # 2. Append new values to target store:
            if source_ind_size > source_ind_max:
                logging.info(f"Appending to {url} along {append_dim} from {source_append_dim[source_ind_max]} to {source_append_dim[source_ind_size - 1]}.")
                _append_to_zarr(data=ds_source.isel({append_dim : slice(source_ind_max, source_ind_size)}),
                                obj_store=obj_store,
                                url=url,
                                append_dim=append_dim,
                                version=version,
                                )

        else:
            # == No intersection -> append all source values to target store == #
            _append_to_zarr(data=ds_source,
                            obj_store=obj_store,
                            url=url,
                            append_dim=append_dim,
                            version=version,
                            )
    else:
        # == Add new variable to Zarr Store == #
        logging.info(f"Sending Variable {var}")
        _write_to_zarr(data=ds_source,
                       obj_store=obj_store,
                       url=url,
                       version=version,
                       )


def _send_to_zarr(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    variables: Optional[list[str]] = None,
    append_dim: str = "time_counter",
    grid_filepath: Optional[str] = None,
    update_coords: Optional[dict] = None,
    rechunk: Optional[dict] = None,
    attrs: Optional[dict] = None,
    parallel: bool = False,
    zarr_version: int = 3
) -> None:
    """
    Write data to new Zarr store in cloud object storage.

    Parameters
    ----------
    file: list | str | xarray.Dataset
        Regular expression or list of filepaths to netCDF file(s).
        Users can also pass a single xarray.Dataset directly.
    bucket: str
        Name of the bucket in the object store. Bucket names can contain only
        lowercase letters, numbers, dots (.), and hyphens (-).
    object_prefix: str
        Prefix to be added to the object names in the object store.
    store_credentials_json: str
        Path to the JSON file containing the object store credentials.
    variables: list[str], optional
        List of variables to send to Zarr stores.
        If None, all variables will be sent.
    append_dim: str, default='time_counter'
        Name of the dimension to append multifile datasets.
    grid_filepath: str, optional
        Path to file containing model grid parameter.
    update_coords: dict, optional
        Dictionary of coordinate variables to update.
    rechunk: dict, optional
        Rechunk strategy dictionary.
    attrs: dict, optional
        Attributes to add to the dataset.
    parallel: bool, default=False,
        Whether to perform open and preprocess steps in parallel using
        `dask.delayed`.
    zarr_version: int, default=3
        Zarr version to use.
    """
    # === Verify Inputs === #
    if not isinstance(file, (list, str, xr.Dataset)):
        raise TypeError("file must be a list of strings, a string, or an xarray.Dataset.")
    if not isinstance(bucket, str):
        raise TypeError("bucket must be a string.")
    if not isinstance(object_prefix, str):
        raise TypeError("object_prefix must be a string.")
    if not isinstance(store_credentials_json, str):
        raise TypeError("store_credentials_json must be a string.")
    if variables is not None:
        if not isinstance(variables, list):
            raise TypeError("variables must be a list of strings.")
        if not all(isinstance(var, str) for var in variables):
            raise TypeError("variables must be a list of strings.")
    if not isinstance(append_dim, str):
        raise TypeError("append_dim must be a string.")
    if grid_filepath is not None:
        if not isinstance(grid_filepath, str):
            raise TypeError("grid_filepath must be a string.")
    if update_coords is not None:
        if not isinstance(update_coords, dict):
            raise TypeError("update_coords must be a dictionary.")
    if rechunk is not None:
        if not isinstance(rechunk, dict):
            raise TypeError("rechunk must be a dictionary.")
    if attrs is not None:
        if not isinstance(attrs, dict):
            raise TypeError("attrs must be a dictionary.")
    if not isinstance(parallel, bool):
        raise TypeError("parallel must be a boolean.")
    if not isinstance(zarr_version, int):
        raise TypeError("zarr_version must be an integer.")

    # === Initialise Synchronous Object Store === #
    logging.info("Reading object store credentials from %s", store_credentials_json)
    obj_store = ObjectStoreS3(anon=False,
                              asynchronous=False,
                              store_credentials_json=store_credentials_json
                              )

    # === Preprocess Data === #
    ds_filepath = _preprocess_dataset(file=file,
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
    # Write to Zarr store:
    url = f"s3://{bucket}/{object_prefix}"
    logging.info(f"Sending Dataset to {url}")
    _write_to_zarr(data=ds_filepath[variables],
                   obj_store=obj_store,
                   url=url,
                   version=zarr_version
                   )

    # Release resources to avoid memory leaks:
    ds_filepath.close()


def send_to_zarr(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    variables: Optional[list[str]] = None,
    append_dim: str = "time_counter",
    grid_filepath: Optional[str] = None,
    update_coords: Optional[dict] = None,
    rechunk: Optional[dict] = None,
    attrs: Optional[dict] = None,
    client : Optional[Client] = None,
    dask_config_kwargs: Optional[dict] = None,
    dask_cluster_kwargs: Optional[dict] = None,
    zarr_version: int = 3
) -> None:
    """
    Write data to new Zarr store in cloud object storage with
    option of using dask.

    Parameters
    ----------
    file: list | str | xarray.Dataset
        Regular expression or list of filepaths to netCDF file(s).
        Users can also pass a single xarray.Dataset directly.
    bucket: str
        Name of the bucket in the object store. Bucket names can contain only
        lowercase letters, numbers, dots (.), and hyphens (-).
    object_prefix: str
        Prefix to be added to the object names in the object store.
    store_credentials_json: str
        Path to the JSON file containing the object store credentials.
    variables: list[str], optional
        List of variables to send. If None, all variables will be sent.
    append_dim: str, default="time_counter"
        Name of the append dimension, by default "time_counter".
    grid_filepath: str, optional
        Path to file containing model grid parameter.
    update_coords: dict, optional
        Dictionary of coordinate variables to update.
    rechunk: dict, optional
        Rechunk strategy dictionary, by default None.
    attrs: dict, optional
        Attributes to add to the dataset.
    client: dask.distributed.Client, optional
        Dask Distributed Client.
    dask_config_kwargs: dict[str,str], optional
        Dask configuration settings passed to dask.config.set().
        Ignored if dask client is provided.
    dask_cluster_kwargs: dict, optional
        Dask cluster configuration settings passed to LocalCluster().
        Ignored if dask client is provided.
    zarr_version: int, default=3
        Zarr version to use.
    """
    if client is not None:
        logging.info(f"Using existing Dask Cluster @ Client: {client.dashboard_link}")

        # Register plugins: capture UserWarnings when rechunking data:
        client.register_worker_plugin(CaptureWarningsPlugin())

        # Register plugins: close aiohttp.ClientSessions:
        client.register_worker_plugin(CloseClientSessionPlugin())

        _send_to_zarr(file=file,
                      bucket=bucket,
                      object_prefix=object_prefix,
                      store_credentials_json=store_credentials_json,
                      variables=variables,
                      append_dim=append_dim,
                      grid_filepath=grid_filepath,
                      update_coords=update_coords,
                      rechunk=rechunk,
                      attrs=attrs,
                      parallel=True,
                      zarr_version=zarr_version
                      )

        # --- Shutdown Dask Client --- #
        client.shutdown()
        logging.info("Existing Dask Client has been shutdown.")

    elif dask_cluster_kwargs is not None:
        # === Send to Zarr store with Dask === #
        if dask_config_kwargs is not None:
            dask.config.set(dask_config_kwargs)
            logging.info("Updated dask configuration settings.")

        # Create local dask cluster & client:
        with LocalCluster(**dask_cluster_kwargs) as cluster, Client(cluster) as client:
            logging.info(f"Created LocalCluster with {dask_cluster_kwargs['n_workers']} workers @ Client: {client.dashboard_link}")

            # Register plugins: capture UserWarnings when rechunking data:
            client.register_worker_plugin(CaptureWarningsPlugin())

            # Register plugins: close aiohttp.ClientSessions:
            client.register_worker_plugin(CloseClientSessionPlugin())

            _send_to_zarr(file=file,
                          bucket=bucket,
                          object_prefix=object_prefix,
                          store_credentials_json=store_credentials_json,
                          variables=variables,
                          append_dim=append_dim,
                          grid_filepath=grid_filepath,
                          update_coords=update_coords,
                          rechunk=rechunk,
                          attrs=attrs,
                          parallel=True,
                          zarr_version=zarr_version
                         )

            # --- Shutdown Store & Dask Cluster --- #
            cluster.close()
            client.shutdown()
            logging.info("Dask Cluster has been shutdown.")
    
    else:
        # === Send to Zarr store without Dask === #
        _send_to_zarr(file=file,
                      bucket=bucket,
                      object_prefix=object_prefix,
                      store_credentials_json=store_credentials_json,
                      variables=variables,
                      append_dim=append_dim,
                      grid_filepath=grid_filepath,
                      update_coords=update_coords,
                      rechunk=rechunk,
                      attrs=attrs,
                      parallel=False,
                      zarr_version=zarr_version
                      )


def _update_zarr(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    variables: Optional[list[str]] = None,
    append_dim: str = "time_counter",
    grid_filepath: Optional[str] = None,
    update_coords: Optional[dict] = None,
    rechunk: Optional[dict] = None,
    attrs: Optional[dict] = None,
    parallel: bool = False,
    zarr_version: int = 3
) -> None:
    """
    Update existing Zarr store in cloud object storage
    by replacing and/or appending data.

    Parameters
    ----------
    file: list | str
        Regular expression or list of filepaths to netCDF file(s).
        Users can also pass a single xarray.Dataset directly.
    bucket: str
        Name of the bucket in the object store. Bucket names can contain only
        lowercase letters, numbers, dots (.), and hyphens (-).
    object_prefix: str
        Prefix to be added to the object names in the object store.
    store_credentials_json: str
        Path to the JSON file containing the object store credentials.
    variables: list, optional
        List of variables to send to Zarr stores.
        If None, all variables will be sent.
    append_dim: str, default='time_counter'
        Name of the dimension to append multifile datasets.
    grid_filepath: str, optional
        Path to file containing model grid parameter.
    update_coords: dict, optional
        Dictionary of coordinate variables to update.
    rechunk: dict, optional
        Rechunk strategy dictionary.
    attrs: dict, optional
        Attributes to add to the dataset.
    parallel: bool, default=False
        Whether to perform open and preprocess steps in parallel using
        `dask.delayed`.
    zarr_version: int, default=3
        Zarr version to use.
    """
    # === Verify Inputs === #
    if not isinstance(file, (list, str, xr.Dataset)):
        raise TypeError("file must be a list of strings, a string, or an xarray.Dataset.")
    if not isinstance(bucket, str):
        raise TypeError("bucket must be a string.")
    if not isinstance(object_prefix, str):
        raise TypeError("object_prefix must be a string.")
    if not isinstance(store_credentials_json, str):
        raise TypeError("store_credentials_json must be a string.")
    if variables is not None:
        if not isinstance(variables, list):
            raise TypeError("variables must be a list of strings.")
        if not all(isinstance(var, str) for var in variables):
            raise TypeError("variables must be a list of strings.")
    if not isinstance(append_dim, str):
        raise TypeError("append_dim must be a string.")
    if grid_filepath is not None:
        if not isinstance(grid_filepath, str):
            raise TypeError("grid_filepath must be a string.")
    if update_coords is not None:
        if not isinstance(update_coords, dict):
            raise TypeError("update_coords must be a dictionary.")
    if rechunk is not None:
        if not isinstance(rechunk, dict):
            raise TypeError("rechunk must be a dictionary.")
    if attrs is not None:
        if not isinstance(attrs, dict):
            raise TypeError("attrs must be a dictionary.")
    if not isinstance(parallel, bool):
        raise TypeError("parallel must be a boolean.")
    if not isinstance(zarr_version, int):
        raise TypeError("zarr_version must be an integer.")

    # === Initialise Synchronous Object Store === #
    logging.info("Reading object store credentials from %s", store_credentials_json)
    obj_store = ObjectStoreS3(anon=False,
                              asynchronous=False,
                              store_credentials_json=store_credentials_json
                              )

    # === Preprocess Data === #
    ds_filepath = _preprocess_dataset(file=file,
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
    # Write to Zarr store:
    url = f"s3://{bucket}/{object_prefix}"
    logging.info(f"Updating Dataset at {url}")
    _update_zarr_store(data=ds_filepath[variables],
                       obj_store=obj_store,
                       url=url,
                       append_dim=append_dim,
                       rechunk=rechunk,
                       version=zarr_version
                       )

    # Release resources to avoid memory leaks:
    ds_filepath.close()


def update_zarr(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    variables: Optional[list[str]] = None,
    append_dim: str = "time_counter",
    grid_filepath: Optional[str] = None,
    update_coords: Optional[dict] = None,
    rechunk: Optional[dict] = None,
    attrs: Optional[dict] = None,
    client : Optional[Client] = None,
    dask_config_kwargs: Optional[dict] = None,
    dask_cluster_kwargs: Optional[dict] = None,
    zarr_version: int = 3
) -> None:
    """
    Update data in existing Zarr store in cloud object
    storage with option of using dask.

    Parameters
    ----------
    file: list | str | xarray.Dataset
        Regular expression or list of filepaths to netCDF file(s).
        Users can also pass a single xarray.Dataset directly.
    bucket: str
        Name of the bucket in the object store. Bucket names can contain only
        lowercase letters, numbers, dots (.), and hyphens (-).
    object_prefix: str
        Prefix to be added to the object names in the object store.
    store_credentials_json: str
        Path to the JSON file containing the object store credentials.
    variables: list, optional
        List of variables to send to Zarr stores.
        If None, all variables will be sent.
    append_dim: str, default='time_counter'
        Name of the dimension to append multifile datasets.
    grid_filepath: str, optional
        Path to file containing model grid parameter.
    update_coords: dict, optional
        Dictionary of coordinate variables to update.
    rechunk: dict, optional
        Rechunk strategy dictionary.
    attrs: dict, optional
        Attributes to add to the dataset.
    client: dask.distributed.Client, optional
        Dask Distributed Client.
    dask_config_kwargs: Dict[str,str], optional
        Dask configuration settings passed to dask.config.set().
        Ignored if dask client is provided.
    dask_cluster_kwargs: dict, optional
        Dask cluster configuration settings passed to LocalCluster().
        Ignored if dask client is provided.
    zarr_version: int, default=3
        zarr version to use.
    """
    if client is not None:
        logging.info(f"Using existing Dask Cluster @ Client: {client.dashboard_link}")

        # Register plugins: capture UserWarnings when rechunking data:
        client.register_worker_plugin(CaptureWarningsPlugin())

        # Register plugins: close aiohttp.ClientSessions:
        client.register_worker_plugin(CloseClientSessionPlugin())

        _update_zarr(file=file,
                     bucket=bucket,
                     object_prefix=object_prefix,
                     store_credentials_json=store_credentials_json,
                     variables=variables,
                     append_dim=append_dim,
                     grid_filepath=grid_filepath,
                     update_coords=update_coords,
                     rechunk=rechunk,
                     attrs=attrs,
                     parallel=True,
                     zarr_version=zarr_version
                     )

        # --- Shutdown Dask Client --- #
        client.shutdown()
        logging.info("Existing Dask Client has been shutdown.")

    elif dask_cluster_kwargs is not None:
        # === Update Zarr store with Dask === #
        if dask_config_kwargs is not None:
            dask.config.set(dask_config_kwargs)
            logging.info("Updated dask configuration settings.")

        # Create local dask cluster & client:
        with LocalCluster(**dask_cluster_kwargs) as cluster, Client(cluster) as client:
            logging.info(f"Created LocalCluster with {dask_cluster_kwargs['n_workers']} workers @ Client: {client.dashboard_link}")

            # Register plugins: capture UserWarnings when rechunking data:
            client.register_worker_plugin(CaptureWarningsPlugin())

            # Register plugins: close aiohttp.ClientSessions:
            client.register_worker_plugin(CloseClientSessionPlugin())

            _update_zarr(file=file,
                         bucket=bucket,
                         object_prefix=object_prefix,
                         store_credentials_json=store_credentials_json,
                         variables=variables,
                         append_dim=append_dim,
                         grid_filepath=grid_filepath,
                         update_coords=update_coords,
                         rechunk=rechunk,
                         attrs=attrs,
                         parallel=True,
                         zarr_version=zarr_version
                         )

            # --- Shutdown Store & Dask Cluster --- #
            cluster.close()
            client.shutdown()
            logging.info("Dask Cluster has been shutdown.")

    else:
        # === Update Zarr store without Dask === #
        _update_zarr(file=file,
                     bucket=bucket,
                     object_prefix=object_prefix,
                     store_credentials_json=store_credentials_json,
                     variables=variables,
                     append_dim=append_dim,
                     grid_filepath=grid_filepath,
                     update_coords=update_coords,
                     rechunk=rechunk,
                     attrs=attrs,
                     parallel=False,
                     zarr_version=zarr_version
                     )
