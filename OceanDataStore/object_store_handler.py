"""
object_store_handler.py

Description:
This module defines the functions to send and update data
to an object store.

Authors:
    - Ollie Tooth
    - Tobias Ferreira
    - Joao Morado
"""
# -- Import Python Modules -- #
import glob
import time
import logging
import asyncio
import warnings
from typing import Optional

import zarr
import icechunk
import icechunk.xarray as icechunk_xr
import numpy as np
import xarray as xr

import dask
from dask.distributed import Client, LocalCluster
from dask.distributed.diagnostics.plugin import WorkerPlugin

# -- Import OceanDataStore Modules -- #
from .object_store import ObjectStoreS3

from .exceptions import (
    ObjectNotFound,
    DimensionNotFound,
    DimensionSizeError,
    AppendDimensionError,
    AppendDimensionSizeError,
    ChunkSizeError,
)

# -- Define WorkerPlugin -- #
class CaptureWarningsPlugin(WorkerPlugin):
    def setup(self, worker):
        # Used to catch UserWarnings when rechunking:
        logging.captureWarnings(True)
    def teardown(self, worker):
        logging.captureWarnings(False)

# -- Define timing context manager -- #
class timer():
    """
    Timer context manager class to return time
    taken to write variables & datasets to an
    object store.

    Parameters
    ----------
    action : str
        Action to be performed. Options are 'send' or 'update'.
    dest : str
        Destination path in the object store.
    var : Optional[str], default=None
        Name of variable to be sent or updated to store.
    """
    def __init__(self, action: str, dest: str, var: Optional[str] = None) -> None:
        # Define class attributes:
        if action == 'send':
            if var is not None:
                self.action = f'Sent {var} to'
            else:
                self.action = 'Sent dataset to'
        elif action == 'replace':
            if var is not None:
                self.action = f'Updated {var} in'
            else:
                self.action = 'Updated'
        elif action == 'append':
            if var is not None:
                self.action = f'Appended {var} to'
            else:
                self.action = 'Appended to'
        else:
            raise ValueError("Invalid action: must be 'send', 'replace' or 'append'.")
        self.dest = dest

    def __enter__(self):
        self.t_start = time.time()

    def __exit__(self, type, value, traceback):
        self.t_end = time.time()
        logging.info(
            f"Completed: {self.action} store s3://{self.dest} in {(self.t_end - self.t_start):.2f} seconds"
            )

# -- Define OceanDataStore Core Functions -- #
async def _check_zarr_store(obj_store: ObjectStoreS3,
                            path: str
                            ) -> bool:
    """
    Check if a zarr store exists at a specified path
    in the object store.

    Parameters
    ----------
    obj_store
        ObjectStoreS3 remote filesystem.
    path
        Path to zarr store in the object store.
    
    Returns
    -------
    bool
        True if the store exists, False otherwise.
    """
    store = zarr.storage.FsspecStore(fs=obj_store, path=path)
    status = await store.exists("")
    await _close_session(obj_store=obj_store)

    return status


async def _check_zarr_compatibility(data: xr.DataArray | xr.Dataset,
                               obj_store: ObjectStoreS3,
                               dest: str,
                               append_dim: str = "time_counter",
                               rechunk: Optional[dict] = None,
                               version: int = 3,
                               ) -> None:
    """
    Check compatibility of DataArray or Dataset to update existing
    zarr store in cloud object storage.

    Parameters
    ----------
    data: xr.DataArray | xr.Dataset
        DataArray or DataSet to update existing zarr store with.
    obj_store: ObjectStoreS3
        ObjectStoreS3 remote filesystem.
    dest: str
        Destination path in the object store.
    append_dim: bool, default="time_counter"
        Dimension to append data to existing zarr store.
    rechunk: Optional[dict], default=None
        Mapping to rechunk dimensions.
    version: int, default=3
        Zarr version to use.
    """
    # === Initialise store using fsspec === #
    store = zarr.storage.FsspecStore(fs=obj_store, path=dest)

    # 1. Check if the store exists:
    if not await _check_zarr_store(obj_store=obj_store, path=dest):
        await _close_session(obj_store=obj_store)
        raise ObjectNotFound(object_name=dest)
    
    # 2. Check zarr store compatibility:
    try:
        ds_store = xr.open_zarr(store, zarr_format=version)
    except Exception as e:
        await _close_session(obj_store=obj_store)
        raise FileNotFoundError(f"zarr version {version} is not compatible with the store: {e}")
    
    # 3. Check if core dimensions exist & size are compatible:
    dims_store = {dim : ds_store.sizes[dim] for dim in ds_store.dims if dim != append_dim}
    for dim in dims_store:
        if dim in data.dims:
            if data.sizes[dim] != dims_store[dim]:
                await _close_session(obj_store=obj_store)
                raise DimensionSizeError(dim=dim, size=data.sizes[dim], expected_size=dims_store[dim])
        else:
            await _close_session(obj_store=obj_store)
            raise DimensionNotFound(dim=dim, object_name=dest)

    # 4. Check if append dimension values are compatible:
    if (data[append_dim][0] < ds_store[append_dim][0]):
        await _close_session(obj_store=obj_store)
        raise AppendDimensionError(dim=append_dim)
    
    # 5. Check if specified chunks are compatible:
    if rechunk is not None:
        for dim in rechunk:
            if dim in ds_store.dims:
                if rechunk[dim] != ds_store.chunks[dim][0]:
                    await _close_session(obj_store=obj_store)
                    raise ChunkSizeError(chunks=rechunk, store_chunks=ds_store.chunks)

    await _close_session(obj_store=obj_store)


def _check_icechunk_compatibility(data: xr.DataArray | xr.Dataset,
                                  dest: str,
                                  repo: icechunk.Repository,
                                  branch: str,
                                  append_dim: str,
                                  rechunk: dict,
                                  ) -> None:
    """
    Check compatibility of DataArray or Dataset to update existing
    IcechunkStore in cloud object storage.

    Parameters
    ----------
    data: xr.DataArray | xr.Dataset
        DataArray or DataSet to update existing zarr store with.
    dest: str
        Path to Icechunk repository in the object store.
    repo: icechunk.Repository
        Icechunk repository in which to write data to IcechunkStore.
    branch: str
        Branch on which to write data to IcechunkStore.
    append_dim: str
        Dimension to append data to existing IcechunkStore.
    rechunk: dict
        Mapping to rechunk dimensions.
    """
    # === Initialise IcechunkStore from session === #
    store = repo.readonly_session(branch=branch).store

    # 1. Check if IcechunkStore exists:
    try:
        ds_store = xr.open_zarr(store, consolidated=False)
    except Exception as e:
        raise FileNotFoundError(f"IcechunkStore not found in repository: {e}")

    # 2. Check if core dimensions exist in IcechunkStore & sizes are consistent:
    dims_data = {dim : data.sizes[dim] for dim in data.dims if dim != append_dim}
    for dim in dims_data:
        if dim in ds_store.dims:
            if dims_data[dim] != ds_store.sizes[dim]:
                raise DimensionSizeError(dim=dim, size=data.sizes[dim], expected_size=ds_store.sizes[dim])
        else:
            raise DimensionNotFound(dim=dim, object_name=dest)

    # 3. Check if append dimension values are consistent:
    if (data[append_dim][0] < ds_store[append_dim][0]):
        raise AppendDimensionError(dim=append_dim)
    
    # 4. Check if specified chunks are consistent:
    if rechunk is not None:
        for dim in rechunk:
            if dim in ds_store.dims:
                if rechunk[dim] != ds_store.chunks[dim][0]:
                    raise ChunkSizeError(chunks=rechunk, store_chunks=ds_store.chunks)


async def _close_session(obj_store: ObjectStoreS3) -> None:
    """
    Close the current Object Store aiohttp session.

    Parameters
    ----------
    obj_store
        ObjectStoreS3 remote filesystem.
    """
    if hasattr(obj_store, '_s3creator'):
        await obj_store._s3creator._client._endpoint.http_session.close()


async def _write_to_zarr(data: xr.DataArray | xr.Dataset,
                         obj_store: ObjectStoreS3,
                         dest: str,
                         version: int = 3,
                         ) -> None:
    """
    Write DataArray or Dataset to zarr store in cloud
    object storage.

    Parameters
    ----------
    data: xr.DataArray | xr.Dataset
        DataArray or DataSet to write to zarr store.
    obj_store: ObjectStoreS3
        ObjectStoreS3 remote filesystem.
    dest: str
        Path to zarr store in the object store.
    version: int, default=3
        Zarr version to use.
    """
    # === Verify Inputs === #
    if not isinstance(data, (xr.DataArray, xr.Dataset)):
        raise TypeError("data must be a DataArray or Dataset.")
    if not isinstance(obj_store, ObjectStoreS3):
        raise TypeError("obj_store must be an ObjectStoreS3 instance.")
    if not isinstance(dest, str):
        raise TypeError("dest must be a string.")
    if not isinstance(version, int):
        raise TypeError("version must be an integer.")

    # === Initialise store using fsspec === #
    store = zarr.storage.FsspecStore(fs=obj_store, path=dest)

    # Convert DataArrays to Datasets:
    if isinstance(data, xr.DataArray):
        var = data.name
        data = data.to_dataset()
    else:
        var = None

    # Write Dataset to Zarr store in Object Store:
    if await _check_zarr_store(obj_store=obj_store, path=dest):
        logging.info(f"Skipping Variable: Store already exists at {dest}")

    else:
        with timer(action='send', dest=dest, var=var):
            # Catch consolidated metadata warnings:
            with warnings.catch_warnings():
                warnings.simplefilter(action="ignore", category=UserWarning)
                data.to_zarr(store=store, mode="w", zarr_format=version)

                await _close_session(obj_store=obj_store)


def _write_to_icechunk(data: xr.DataArray | xr.Dataset,
                       dest: str,
                       repo: icechunk.Repository,
                       commit_message: str,
                       branch: Optional[str] = "main",
                       ) -> None:
    """
    Write DataArray or Dataset to IcechunkStore in cloud
    object storage.

    Parameters
    ----------
    data: xr.DataArray | xr.Dataset
        DataArray or DataSet to write to IcechunkStore.
    dest: str
        Path to Icechunk repository in the object store.
    repo: icechunk.Repository
        Icechunk repository in which to write data to
        IcechunkStore.
    commit_message: str
        Commit message when updating the Icechunk repository.
    branch: str, default="main"
        Branch on which to write data to IcechunkStore.
    """
    # === Convert DataArrays to Datasets === #
    if isinstance(data, xr.DataArray):
        var = data.name
        data = data.to_dataset()
    else:
        var = None

    # === Write Data to IcechunkStore & Commit === #
    with timer(action='send', dest=dest, var=var):
        session = repo.writable_session(branch=branch)
        icechunk_xr.to_icechunk(data, session, mode='a')
        session.commit(message=commit_message)


async def _append_to_zarr(data: xr.DataArray | xr.Dataset,
                          obj_store: ObjectStoreS3,
                          dest: str,
                          append_dim: str = "time_counter",
                          version: int = 3,
                          ) -> None:
    """
    Append DataArray or Dataset to existing zarr store in
    cloud object storage.

    Parameters
    ----------
    data: xr.DataArray | xr.Dataset
        DataArray or DataSet to append to existing zarr store.
    obj_store: ObjectStoreS3
        ObjectStoreS3 remote filesystem.
    dest: str
        Path to zarr store in the object store.
    append_dim: str, default="time_counter"
        Dimension to append data to existing zarr store.
    version: int, default=3
        Zarr version to use.
    """
    # === Initialise store using fsspec === #
    store = zarr.storage.FsspecStore(fs=obj_store, path=dest)

    with timer(action='append', dest=dest):
        # Catch consolidated metadata warnings:
        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore", category=UserWarning)
            data.to_zarr(store=store, append_dim=append_dim, zarr_format=version)

            await _close_session(obj_store=obj_store)


def _append_to_icechunk(data: xr.DataArray | xr.Dataset,
                        dest: str,
                        repo: icechunk.Repository,
                        commit_message: str,
                        branch: Optional[str] = "main",
                        append_dim: str = "time_counter",
                        ) -> None:
    """
    Append DataArray or Dataset to existing IcechunkStore in
    cloud object storage.

    Parameters
    ----------
    data: xr.DataArray | xr.Dataset
        DataArray or DataSet to append to existing IcechunkStore.
    dest: str
        Path to Icechunk repository in the object store.
    repo: icechunk.Repository
        Icechunk repository in which to write data to
        IcechunkStore.
    commit_message: str
        Commit message when updating the Icechunk repository.
    branch: str, default="main"
        Branch on which to write data to IcechunkStore.
    append_dim: str, default="time_counter"
        Dimension to append data to existing IcechunkStore.
    """
    # === Convert DataArrays to Datasets === #
    if isinstance(data, xr.DataArray):
        data = data.to_dataset()

    # === Append Data to IcechunkStore & Commit === #
    with timer(action='append', dest=dest):
        session = repo.writable_session(branch=branch)
        icechunk_xr.to_icechunk(obj=data, session=session, append_dim=append_dim)
        session.commit(message=commit_message)


async def _replace_in_zarr(data: xr.DataArray | xr.Dataset,
                           obj_store: ObjectStoreS3,
                           dest: str,
                           region: dict,
                           version: int = 3,
                           ) -> None:
    """
    Append DataArray or Dataset to existing zarr store in
    cloud object storage.

    Parameters
    ----------
    data: xr.DataArray | xr.Dataset
        DataArray or DataSet to append to existing zarr store.
    obj_store: ObjectStoreS3
        ObjectStoreS3 remote filesystem.
    dest: str
        Path to zarr store in the object store.
    region: dict
        Region of existing zarr store to replace data.
    version: int, default=3
        Zarr version to use.
    """
    # === Initialise store using fsspec === #
    store = zarr.storage.FsspecStore(fs=obj_store, path=dest)

    # Drop variables w/o append dimension:
    append_dim = list(region.keys())[0]
    drop_list = [var for var in data.variables if append_dim not in data[var].dims]
    data = data.drop_vars(drop_list)

    with timer(action='replace', dest=dest):
        # Catch consolidated metadata warnings:
        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore", category=UserWarning)
            data.to_zarr(store=store, region=region, zarr_format=version)

            await _close_session(obj_store=obj_store)


def _replace_in_icechunk(data: xr.DataArray | xr.Dataset,
                         dest: str,
                         region: dict,
                         repo: icechunk.Repository,
                         commit_message: str,
                         branch: Optional[str] = "main",
                         ) -> None:
    """
    Replace data in existing IcechunkStore in cloud object storage.

    Parameters
    ----------
    data: xr.DataArray | xr.Dataset
        DataArray or Dataset used to replace data in existing IcechunkStore.
    dest: str
        Path to Icechunk repository in the object store.
    region: dict
        Region of existing IcechunkStore to replace data.
    repo: icechunk.Repository
        Icechunk repository in which to replace data in IcechunkStore.
    commit_message: str
        Commit message when updating the Icechunk repository.
    branch: str, default="main"
        Branch on which to write data to IcechunkStore.
    """
    # === Convert DataArrays to Datasets === #
    if isinstance(data, xr.DataArray):
        data = data.to_dataset()

    # Drop variables w/o append dimension:
    append_dim = list(region.keys())[0]
    drop_list = [var for var in data.variables if append_dim not in data[var].dims]
    data = data.drop_vars(drop_list)

    # === Write Data to IcechunkStore & Commit === #
    with timer(action='replace', dest=dest):
        session = repo.writable_session(branch=branch)
        icechunk_xr.to_icechunk(obj=data, session=session, region=region)
        session.commit(message=commit_message)


async def _update_zarr(data: xr.DataArray | xr.Dataset,
                       obj_store: ObjectStoreS3,
                       dest: str,
                       append_dim: str = "time_counter",
                       rechunk: Optional[dict] = None,
                       version: int = 3,
                       ) -> None:
    """
    Update an existing zarr store in object storage by replacing
    existing values and/or appending new values.

    Parameters
    ----------
    data: xr.DataArray | xr.Dataset
        DataArray or DataSet to update existing zarr store with.
    obj_store: ObjectStoreS3
        ObjectStoreS3 remote filesystem.
    dest: str
        Path to zarr store in the object store.
    append_dim: bool, default="time_counter"
        Dimension to append data to existing zarr store.
    rechunk: Optional[dict], default=None
        Mapping to rechunk dimensions.
    version: int, default=3
        Zarr version to use.
    """
    # === Verify Inputs === #
    if not isinstance(data, (xr.DataArray, xr.Dataset)):
        raise TypeError("data must be a DataArray or Dataset.")
    if not isinstance(obj_store, ObjectStoreS3):
        raise TypeError("obj_store must be an ObjectStoreS3 instance.")
    if not isinstance(dest, str):
        raise TypeError("dest must be a string.")
    if not isinstance(append_dim, str):
        raise TypeError("append_dim must be a string.")
    if rechunk is not None:
        if not isinstance(rechunk, dict):
            raise TypeError("rechunk must be a dictionary.")
    if not isinstance(version, int):
        raise TypeError("version must be an integer.")

    # === Store compatability checks === #
    store = zarr.storage.FsspecStore(fs=obj_store, path=dest)

    # Convert DataArrays to Datasets:
    if isinstance(data, xr.DataArray):
        ds_source = data.to_dataset()

    # Check source Dataset compatibility with existing store:
    await _check_zarr_compatibility(data=ds_source,
                                    obj_store=obj_store,
                                    dest=dest,
                                    append_dim=append_dim,
                                    rechunk=rechunk,
                                    version=version
                                    )
    logging.info(f"Passed Compatibility Checks for store {dest}")

    # === Updating existing zarr store === #
    # Extract source & target append dimension values:
    ds_target = xr.open_zarr(store, zarr_format=version)
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
        logging.info(f"Updating {dest} along {append_dim} from {target_append_dim[target_ind_min]} to {target_append_dim[target_ind_max - 1]}.")
        await _replace_in_zarr(data=ds_source.isel({append_dim : slice(source_ind_min, source_ind_max)}),
                               obj_store=obj_store,
                               dest=dest,
                               region={append_dim : slice(target_ind_min, target_ind_max)},
                               version=version,
                               )

        # 2. Append new values to target store:
        if source_ind_size > source_ind_max:
            logging.info(f"Appending to {dest} along {append_dim} from {source_append_dim[source_ind_max]} to {source_append_dim[source_ind_size - 1]}.")
            await _append_to_zarr(data=ds_source.isel({append_dim : slice(source_ind_max, source_ind_size)}),
                                  obj_store=obj_store,
                                  dest=dest,
                                  append_dim=append_dim,
                                  version=version,
                                  )

    else:
        # == No intersection -> append all source values to target store == #
        await _append_to_zarr(data=ds_source,
                              obj_store=obj_store,
                              dest=dest,
                              append_dim=append_dim,
                              version=version,
                              )

    await _close_session(obj_store=obj_store)


def _update_icechunk_store(data: xr.DataArray | xr.Dataset,
                           dest: str,
                           repo: icechunk.Repository,
                           commit_message: str,
                           branch: Optional[str] = "main",
                           append_dim: str = "time_counter",
                           rechunk: Optional[dict] = None,
                           ) -> None:
    """
    Update an existing IcechunkStore in object storage by replacing
    existing values and/or appending new values.

    Parameters
    ----------
    data: xr.DataArray | xr.Dataset
        DataArray or DataSet to append to existing IcechunkStore.
    dest: str
        Path to Icechunk repository in the object store.
    repo: icechunk.Repository
        Icechunk repository in which to write data to
        IcechunkStore.
    commit_message: str
        Commit message when updating the Icechunk repository.
    branch: str, default="main"
        Branch on which to write data to IcechunkStore.
    append_dim: bool, default="time_counter"
        Dimension to append data to existing IcechunkStore.
    rechunk: Optional[dict], default=None
        Mapping to rechunk dimensions.
    """
    # Convert DataArrays to Datasets:
    if isinstance(data, xr.DataArray):
        var = data.name
        ds_source = data.to_dataset()
    else:
        var = None
        ds_source = data

    # Extract source & target append dimension values:
    store = repo.readonly_session(branch=branch).store
    ds_target = xr.open_zarr(store, consolidated=False)
    target_append_dim = ds_target[append_dim].values
    source_append_dim = ds_source[append_dim].values

    # === Update existing variable in IcechunkStore === #
    if (var in ds_target.data_vars) or (var is None):
        # Check source Dataset compatibility with existing store:
        _check_icechunk_compatibility(data=ds_source,
                                    dest=dest,
                                    repo=repo,
                                    branch=branch,
                                    append_dim=append_dim,
                                    rechunk=rechunk,
                                    )
        logging.info(f"Passed Compatibility Checks for IcechunkStore {dest}")

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

            # 1. Replace overlapping values in target IcechunkStore:
            logging.info(f"Updating {dest} along {append_dim} from {target_append_dim[target_ind_min]} to {target_append_dim[target_ind_max - 1]}.")
            if var is not None:
                rep_commit_message = f"{commit_message} -> Updated {var} along {append_dim} from {target_append_dim[target_ind_min]} to {target_append_dim[target_ind_max - 1]}."
            else:
                rep_commit_message = f"{commit_message} -> Updated {dest} along {append_dim} from {target_append_dim[target_ind_min]} to {target_append_dim[target_ind_max - 1]}."

            _replace_in_icechunk(data=ds_source.isel({append_dim : slice(source_ind_min, source_ind_max)}),
                                repo=repo,
                                dest=dest,
                                region={append_dim : slice(target_ind_min, target_ind_max)},
                                commit_message=rep_commit_message,
                                branch=branch
                                )

            # 2. Append new values to target IcechunkStore:
            if source_ind_size > source_ind_max:
                logging.info(f"Appending to {dest} along {append_dim} from {source_append_dim[source_ind_max]} to {source_append_dim[source_ind_size - 1]}.")
                if var is not None:
                    app_commit_message = f"{commit_message} -> Appended to {var} along {append_dim} from {source_append_dim[source_ind_max]} to {source_append_dim[source_ind_size - 1]}."
                else:
                    app_commit_message = f"{commit_message} -> Appended to {dest} along {append_dim} from {source_append_dim[source_ind_max]} to {source_append_dim[source_ind_size - 1]}."

                _append_to_icechunk(data=ds_source.isel({append_dim : slice(source_ind_max, source_ind_size)}),
                                    repo=repo,
                                    dest=dest,
                                    commit_message=app_commit_message,
                                    branch=branch,
                                    append_dim=append_dim
                                    )
        else:
            # == No intersection -> append all source values to target IcechunkStore == #
            _append_to_icechunk(data=ds_source,
                                repo=repo,
                                dest=dest,
                                commit_message=commit_message,
                                branch=branch,
                                append_dim=append_dim
                                )
    else:
        # == Add new variable to IcechunkStore == #
        logging.info(f"Sending Variable {var}")
        snd_commit_message = f"{commit_message} -> Sent {var} along {append_dim} from {source_append_dim[0]} to {source_append_dim[-1]}."
        _write_to_icechunk(data=ds_source,
                           dest=dest,
                           repo=repo,
                           commit_message=snd_commit_message,
                           branch=branch,
                           )


def _preprocess_dataset(file: list[str] | str | xr.Dataset,
                        rechunk: Optional[dict] = None,
                        append_dim: str = "time_counter",
                        update_coords: Optional[dict] = None,
                        grid_filepath: Optional[str] = None,
                        attrs: Optional[dict] = None,
                        parallel: bool = False,
                        ) -> xr.Dataset:
    """
    Preprocess the dataset to be sent to the object store.

    Returns
    -------
    xr.Dataset
        Preprocessed (multifile) dataset with optionally
        updated coordinates, chunksizes and attributes.

    """
    # == Verify Inputs == #
    if not isinstance(file, (list, str, xr.Dataset)):
        raise TypeError("filepaths must be a list, a string or an xarray Dataset.")
    if isinstance(file, list):
        for fpath in file:
            if not isinstance(fpath, str):
                raise TypeError("filepaths must be a list of strings.")
            if not fpath.endswith('.nc'):
                raise ValueError("Invalid file extension: only .nc files are supported.")
    elif isinstance(file, str):
        if not file.endswith('.nc'):
            raise ValueError("Invalid file extension: only .nc files are supported.")
    if rechunk is not None:
        if not isinstance(rechunk, dict):
            raise TypeError("rechunk must be a dictionary.")
    if not isinstance(append_dim, str):
        raise TypeError("append_dim must be a string.")
    if update_coords is not None:
        if not isinstance(update_coords, dict):
            raise TypeError("update_coords must be a dictionary.")
    if grid_filepath is not None:
        if not isinstance(grid_filepath, str):
            raise TypeError("grid_filepath must be a string.")
    if attrs is not None:
        if not isinstance(attrs, dict):
            raise TypeError("attrs must be a dictionary.")
    if not isinstance(parallel, bool):
        raise TypeError("parallel must be a boolean.")

    # === Load netCDF dataset === #
    if rechunk is None:
        # Default to dask chunks equal to on-disk chunks:
        rechunk = {}

    # File names from str / regular expression:
    if isinstance(file, str):
        if '*' in file:
            filepaths = sorted(glob.glob(file))
            if len(filepaths) == 0:
                raise FileNotFoundError(f"No files found at {filepaths}")
        else:
            filepaths = [file]
    # File names from list:
    elif isinstance(file, list):
        filepaths = file

    # Use input dataset:
    if isinstance(file, xr.Dataset):
        ds_filepath = file
        if rechunk is not None:
            ds_filepath = ds_filepath.chunk(rechunk)
    else:
        # Open multi-file dataset:
        if len(filepaths) > 1:
            ds_filepath = xr.open_mfdataset(filepaths,
                                            engine='h5netcdf',
                                            chunks=rechunk,
                                            parallel=parallel,
                                            concat_dim=append_dim,
                                            combine='nested',
                                            data_vars='minimal',
                                            coords='minimal',
                                            compat='override'
                                            )
        else:
            # Open single file dataset:
            ds_filepath = xr.open_dataset(filepaths[0], chunks=rechunk)

    # === Update coordinates using model grid file === #
    if update_coords is not None:
        if grid_filepath is None:
            raise ValueError(
                "grid_filepath must be specified to update coordinate variables."
                )
        else:
            ds_grid = xr.open_dataset(grid_filepath)
        # Update coordinate vars using model grid file:
        for key in update_coords.keys():
            coord_data = ds_grid[update_coords[key]].squeeze(drop=True)
            # Rechunk dimensions to user specified chunks:
            if rechunk is not None:
                coord_chunks = {dim: rechunk[dim] for dim in coord_data.dims}
                ds_filepath = ds_filepath.assign_coords(
                    {key: coord_data.chunk(coord_chunks)}
                    )
            else:
                ds_filepath = ds_filepath.assign_coords(
                    {key: coord_data}
                    )
        logging.info('Completed: Updated coordinate variables.')

    # === Update Attributes === #
    if attrs is not None:
        ds_filepath = ds_filepath.assign_attrs(attrs)

    return ds_filepath


def send(
        file: list[str] | str | xr.Dataset,
        bucket: str,
        object_prefix: str,
        store_credentials_json: str,
        variables: list[str] | str = 'all',
        send_vars_indep: bool = True,
        append_dim: str = "time_counter",
        grid_filepath: Optional[str] = None,
        update_coords: Optional[dict] = None,
        rechunk: Optional[dict] = None,
        attrs: Optional[dict] = None,
        zarr_version: int = 3
        ) -> None:
    """
    Write data in serial to new zarr store in cloud object storage.

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
    variables: list, default='all'
        List of variables to send to Zarr stores.
        If None, all variables will be sent.
    send_vars_indep: bool, default=True
        Whether to send variables as separate objects.
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
    zarr_version: int, default=3
        Zarr version to use.
    """
    # === Initialise Asynchronous Object Store === #
    logging.info("Reading object store credentials from %s", store_credentials_json)
    obj_store = ObjectStoreS3(anon=False,
                              asynchronous=True,
                              store_credentials_json=store_credentials_json
                              )

    # === Preprocess Data === #
    ds_filepath = _preprocess_dataset(file=file,
                                      rechunk=rechunk,
                                      append_dim=append_dim,
                                      update_coords=update_coords,
                                      grid_filepath=grid_filepath,
                                      attrs=attrs,
                                      parallel=False,
                                      )
    if variables is None:
        variables = list(ds_filepath.data_vars)

    # === Send Variables to Individual Zarr Stores === #
    if send_vars_indep:
        for var in variables:
            logging.info(f"Sending Variable {var}")
            dest = f"{bucket}/{object_prefix}/{var}"
            asyncio.run(
                _write_to_zarr(data=ds_filepath[var],
                               obj_store=obj_store,
                               dest=dest,
                               version=zarr_version
                               )
                        )
    
        # Release resources to avoid memory leaks:
        ds_filepath.close()
        
    else:
        # === Send Dataset to Zarr Store === #
        # Write to zarr store:
        dest = f"{bucket}/{object_prefix}"
        logging.info(f"Sending Dataset to {dest}")
        asyncio.run(
            _write_to_zarr(data=ds_filepath[variables],
                           obj_store=obj_store,
                           dest=dest,
                           version=zarr_version
                           )
                    )
        
        # Release resources to avoid memory leaks:
        ds_filepath.close()


def send_with_dask(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    variables: list[str] | str = 'all',
    send_vars_indep: bool = True,
    append_dim: str = "time_counter",
    grid_filepath: Optional[str] = None,
    update_coords: Optional[dict] = None,
    rechunk: Optional[dict] = None,
    attrs: Optional[dict] = None,
    dask_config_kwargs: Optional[dict] = None,
    dask_cluster_kwargs: Optional[dict] = None,
    zarr_version: int = 3
    ) -> None:
    """
    Write data in parallel to new zarr store in cloud object storage
    using dask.

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
    variables: list | str, default="all"
        List of variables to send. If None, all variables will be sent.
    send_vars_indep: bool, default=True
        Whether to send variables as separate objects, by default True.
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
    dask_config_kwargs: Dict[str,str], optional
        Dask configuration settings passed to dask.config.set().
    dask_cluster_kwargs: dict, optional
        Dask cluster configuration settings passed to LocalCluster().
    zarr_version: int, default=3
        Zarr version to use.
    """
    # === Configure Cluster === #
    # Update dask configuration settings:
    if dask_config_kwargs is not None:
        dask.config.set(dask_config_kwargs)
        logging.info("Updated dask configuration settings.")

    # Create local dask cluster & client:
    with LocalCluster(**dask_cluster_kwargs) as cluster, Client(cluster, asynchronous=False) as client:
        logging.info(f"Created LocalCluster with {dask_cluster_kwargs["n_workers"]} workers @ Client: {client.dashboard_link}")

        # === Register Dask Worker Plugin === #
        # Catch UserWarnings when rechunking:
        client.register_worker_plugin(CaptureWarningsPlugin())

        # === Initialise Asynchronous Object Store === #
        logging.info("Reading object store credentials from %s", store_credentials_json)
        obj_store = ObjectStoreS3(anon=False,
                                  asynchronous=True,
                                  store_credentials_json=store_credentials_json
                                  )

        # === Preprocess Data === #
        ds_filepath = _preprocess_dataset(file=file,
                                          rechunk=rechunk,
                                          append_dim=append_dim,
                                          update_coords=update_coords,
                                          grid_filepath=grid_filepath,
                                          attrs=attrs,
                                          parallel=True,
                                          )
        if variables is None:
            variables = list(ds_filepath.data_vars)
        
        # === Send Variables to Individual Zarr Stores === #
        if send_vars_indep:
            for var in variables:
                logging.info(f"Sending Variable {var}")
                dest = f"{bucket}/{object_prefix}/{var}"
                asyncio.run(
                    _write_to_zarr(data=ds_filepath[var],
                                   obj_store=obj_store,
                                   dest=dest,
                                   version=zarr_version
                                   )
                            )

            # Release resources to avoid memory leaks:
            ds_filepath.close()
            
        else:
            # === Send Dataset to Object Store === #
            # Write to zarr store:
            dest = f"{bucket}/{object_prefix}"
            logging.info(f"Sending Dataset to {dest}")
            asyncio.run(
                _write_to_zarr(data=ds_filepath[variables],
                               obj_store=obj_store,
                               dest=dest,
                               version=zarr_version
                               )
                        )

            # Release resources to avoid memory leaks:
            ds_filepath.close()
            
        # === Shutdown Store & Dask Cluster === #
        client.run(_close_session, (obj_store), wait=True)
        client.shutdown()
        client.close()
        logging.info("Dask Cluster has been shutdown.")


def send_to_zarr(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    variables: list[str] | str = 'all',
    send_vars_indep: bool = True,
    append_dim: str = "time_counter",
    grid_filepath: Optional[str] = None,
    update_coords: Optional[dict] = None,
    rechunk: Optional[dict] = None,
    attrs: Optional[dict] = None,
    dask_config_kwargs: Optional[dict] = None,
    dask_cluster_kwargs: Optional[dict] = None,
    zarr_version: int = 3
    ) -> None:
    """
    Send files to new zarr store in cloud object storage
    in serial or in parallel using a dask local cluster.

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
    variables: list | str, default="all"
        List of variables to send. If None, all variables will be sent.
    send_vars_indep: bool, default=True
        Whether to send variables as separate objects, by default True.
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
    dask_config_kwargs: Dict[str,str], optional
        Dask configuration settings passed to dask.config.set().
    dask_cluster_kwargs: dict, optional
        Dask cluster configuration settings passed to LocalCluster().
    zarr_version: int, default=3
        Zarr version to use.
    """
    # == Send files to zarr store without dask == #
    if (dask_config_kwargs is None) and (dask_cluster_kwargs is None):
        send(file,
             bucket,
             object_prefix,
             store_credentials_json,
             variables,
             send_vars_indep,
             append_dim,
             grid_filepath,
             update_coords,
             rechunk,
             attrs,
             zarr_version
             )

    # == Send files to zarr store with dask == #
    else:
        send_with_dask(file,
                       bucket,
                       object_prefix,
                       store_credentials_json,
                       variables,
                       send_vars_indep,
                       append_dim,
                       grid_filepath,
                       update_coords,
                       rechunk,
                       attrs,
                       dask_config_kwargs,
                       dask_cluster_kwargs,
                       zarr_version
                       )


def _send_to_icechunk(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    variables: list[str] | str = 'all',
    send_vars_indep: bool = True,
    append_dim: Optional[str] = 'time_counter',
    grid_filepath: Optional[str] = None,
    update_coords: Optional[dict] = None,
    rechunk: Optional[dict] = None,
    attrs: Optional[dict] = None,
    branch: str = "main",
    commit_message: str = "Add new data to my Icechunk repository",
    variable_commits: bool = False,
    icechunk_config: Optional[dict] = None,
    ) -> None:
    """
    Write data to new Icechunk repository in cloud object storage.

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
    variables: list | str, default="all"
        List of variables to send. If None, all variables will be sent.
    send_vars_indep: bool, default=True
        Whether to send variables as separate objects, by default True.
    append_dim: str, default='time_counter'
        Name of the dimension to append multifile datasets.
    grid_filepath: str, optional
        Path to file containing model grid parameter.
    update_coords: dict, optional
        Dictionary of coordinate variables to update.
    rechunk: dict, optional
        Rechunk strategy dictionary, by default None.
    attrs: dict, optional
        Attributes to add to the dataset.
    branch: str, default="main"
        Branch on which to write data to IcechunkStore.
    commit_message: str, default="Initial commit"
        Commit message when updating the Icechunk repository.
    variable_commits: bool, default=False
        Whether to write each variable to Icechunk repository using
        separate commits.
    icechunk_config: dict, optional
        Icechunk repository configuration.
    """
    # === Initialise Synchronous Object Store === #
    logging.info("Reading object store credentials from %s", store_credentials_json)
    obj_store = ObjectStoreS3(anon=False,
                              asynchronous=False,
                              store_credentials_json=store_credentials_json
                              )

    if icechunk_config is None:
        icechunk_config = {"storage_config_kwargs":{},
                           "repository_config_kwargs":{},
                           "storage_settings_kwargs":{}
                           }

    # === Preprocess Data === #
    ds_filepath = _preprocess_dataset(file=file,
                                      rechunk=rechunk,
                                      append_dim=append_dim,
                                      update_coords=update_coords,
                                      grid_filepath=grid_filepath,
                                      attrs=attrs,
                                      parallel=True,
                                      )

    # Consider variables with append dimension only:
    if variables is None:
        variables = list(ds_filepath.data_vars)
    variables = [var for var in variables if append_dim in ds_filepath[var].dims]

    # Extract append dimension values:
    source_append_dim = ds_filepath[append_dim].values

    # === Send Variables to Individual Icechunk Repos === #
    if send_vars_indep:
        for var in variables:
            logging.info(f"Sending Variable {var}")
            try:
                # Create new Icechunk repo:
                repo = obj_store.create_icechunk_repo(bucket=bucket,
                                                      prefix=f"{object_prefix}/{var}",
                                                      storage_config_kwargs=icechunk_config["storage_config_kwargs"],
                                                      repository_config_kwargs=icechunk_config["repository_config_kwargs"],
                                                      storage_settings_kwargs=icechunk_config["storage_settings_kwargs"],
                                                      )
                # Write data and commit to the repo:
                snd_commit_message = f"{commit_message} -> Sent {var} along {append_dim} from {source_append_dim[0]} to {source_append_dim[-1]}."
                _write_to_icechunk(data=ds_filepath[var],
                                   dest=f"{bucket}/{object_prefix}/{var}",
                                   repo=repo,
                                   commit_message=snd_commit_message,
                                   branch=branch,
                                   )
            except icechunk.IcechunkError:
                logging.info(f"Skipping Variable: Icechunk repository already exists at {bucket}/{object_prefix}/{var}")

        # Release resources to avoid memory leaks:
        ds_filepath.close()

    else:
        # === Send Variables to Single Icechunk Repo === #
        try:
            # Create new Icechunk repo:
            repo = obj_store.create_icechunk_repo(bucket=bucket,
                                                prefix=object_prefix,
                                                storage_config_kwargs=icechunk_config["storage_config_kwargs"],
                                                repository_config_kwargs=icechunk_config["repository_config_kwargs"],
                                                storage_settings_kwargs=icechunk_config["storage_settings_kwargs"],
                                                )
            if variable_commits:
                for var in variables:
                    logging.info(f"Sending Variable {var}")
                    snd_commit_message = f"{commit_message} -> Sent {var} along {append_dim} from {source_append_dim[0]} to {source_append_dim[-1]}."
                    # Write each variable using separate commits to the repo:
                    _write_to_icechunk(data=ds_filepath[var],
                                       dest=f"{bucket}/{object_prefix}",
                                       repo=repo,
                                       commit_message=snd_commit_message,
                                       branch=branch,
                                       )
            else:
                # Write all variables using single commit to the repo:
                logging.info(f"Sending Dataset {object_prefix}")
                snd_commit_message = f"{commit_message} -> Sent dataset along {append_dim} from {source_append_dim[0]} to {source_append_dim[-1]}."
                _write_to_icechunk(data=ds_filepath[variables],
                                   dest=f"{bucket}/{object_prefix}",
                                   repo=repo,
                                   commit_message=snd_commit_message,
                                   branch=branch,
                                   )
        except icechunk.IcechunkError:
            if variable_commits:
                logging.info(f"Skipping Dataset: Icechunk repository already exists at {bucket}/{object_prefix}/{var}")
            else:
                logging.info(f"Skipping Dataset: Icechunk repository already exists at {bucket}/{object_prefix}")

        # Release resources to avoid memory leaks:
        ds_filepath.close()


def send_to_icechunk(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    variables: Optional[list[str]] = None,
    send_vars_indep: bool = True,
    append_dim: Optional[str] = 'time_counter',
    grid_filepath: Optional[str] = None,
    update_coords: Optional[dict] = None,
    rechunk: Optional[dict] = None,
    attrs: Optional[dict] = None,
    branch: str = "main",
    commit_message: str = "Add new data to my Icechunk repository",
    variable_commits: bool = False,
    dask_config_kwargs: Optional[dict] = None,
    dask_cluster_kwargs: Optional[dict] = None,
    icechunk_config: Optional[dict] = None,
    ) -> None:
    """
    Write data to new Icechunk repository in cloud object storage with
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
    variables: list[str], default=None
        List of variables to send. If None, all variables will be sent.
    send_vars_indep: bool, default=True
        Whether to send variables as separate objects, by default True.
    append_dim: str, default='time_counter'
        Name of the dimension to append multifile datasets.
    grid_filepath: str, optional
        Path to file containing model grid parameter.
    update_coords: dict, optional
        Dictionary of coordinate variables to update.
    rechunk: dict, optional
        Rechunk strategy dictionary, by default None.
    attrs: dict, optional
        Attributes to add to the dataset.
    branch: str, default="main"
        Branch on which to write data to IcechunkStore.
    commit_message: str, default="Initial commit"
        Commit message when updating the Icechunk repository.
    variable_commits: bool, default=False
        Whether to write each variable to Icechunk repository using
        separate commits.
    dask_config_kwargs: dict, optional
        Dask configuration settings passed to dask.config.set().
    dask_cluster_kwargs: dict, optional
        Dask cluster configuration settings passed to LocalCluster().
    icechunk_config: dict, optional
        Icechunk repository configuration.
    """
    # === Send to Icechunk repo(s) with Dask === #
    if dask_cluster_kwargs is not None:
        if dask_config_kwargs is not None:
            dask.config.set(dask_config_kwargs)
            logging.info("Updated dask configuration settings.")

        # Create local dask cluster & client:
        with LocalCluster(**dask_cluster_kwargs) as cluster, Client(cluster) as client:
            logging.info(f"Created LocalCluster with {dask_cluster_kwargs["n_workers"]} workers @ Client: {client.dashboard_link}")

            # Catch UserWarnings when rechunking data:
            client.register_worker_plugin(CaptureWarningsPlugin())

            _send_to_icechunk(file=file,
                              bucket=bucket,
                              object_prefix=object_prefix,
                              store_credentials_json=store_credentials_json,
                              variables=variables,
                              send_vars_indep=send_vars_indep,
                              append_dim=append_dim,
                              grid_filepath=grid_filepath,
                              update_coords=update_coords,
                              rechunk=rechunk,
                              attrs=attrs,
                              branch=branch,
                              commit_message=commit_message,
                              variable_commits=variable_commits,
                              icechunk_config=icechunk_config
                              )

            # --- Shutdown Store & Dask Cluster --- #
            client.shutdown()
            client.close()
            logging.info("Dask Cluster has been shutdown.")
    
    else:
        # === Send to Icechunk repo(s) without Dask === #
        _send_to_icechunk(file=file,
                          bucket=bucket,
                          object_prefix=object_prefix,
                          store_credentials_json=store_credentials_json,
                          variables=variables,
                          send_vars_indep=send_vars_indep,
                          append_dim=append_dim,
                          grid_filepath=grid_filepath,
                          update_coords=update_coords,
                          rechunk=rechunk,
                          attrs=attrs,
                          branch=branch,
                          commit_message=commit_message,
                          variable_commits=variable_commits,
                          icechunk_config=icechunk_config
                          )


def update(
        file: list[str] | str | xr.Dataset,
        bucket: str,
        object_prefix: str,
        store_credentials_json: str,
        variables: list[str] | str = 'all',
        send_vars_indep: bool = True,
        append_dim: str = "time_counter",
        grid_filepath: Optional[str] = None,
        update_coords: Optional[dict] = None,
        rechunk: Optional[dict] = None,
        attrs: Optional[dict] = None,
        zarr_version: int = 3
        ) -> None:
    """
    Update existing zarr store in cloud object storage
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
    variables: list, default='all'
        List of variables to send to Zarr stores.
        If None, all variables will be sent.
    send_vars_indep: bool, default=True
        Whether to send variables as separate objects.
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
    zarr_version: int, default=3
        Zarr version to use.
    """
    # === Initialise Asynchronous Object Store === #
    logging.info("Reading object store credentials from %s", store_credentials_json)
    obj_store = ObjectStoreS3(anon=False,
                              asynchronous=True,
                              store_credentials_json=store_credentials_json
                              )

    # === Preprocess Data === #
    ds_filepath = _preprocess_dataset(file=file,
                                      rechunk=rechunk,
                                      append_dim=append_dim,
                                      update_coords=update_coords,
                                      grid_filepath=grid_filepath,
                                      attrs=attrs,
                                      parallel=False
                                      )

    # === Update Variables in Existing Zarr Store === #
    if send_vars_indep:
        if variables is None:
            variables = list(ds_filepath.data_vars)

        for var in variables:
            if append_dim not in ds_filepath[var].dims:
                logging.info(f"Skipping Variable: append dimension {append_dim} not found.")
            else:
                logging.info(f"Updating Variable {var}")
                dest = f"{bucket}/{object_prefix}/{var}"
                asyncio.run(
                    _update_zarr(data=ds_filepath[var],
                                 obj_store=obj_store,
                                 dest=dest,
                                 append_dim=append_dim,
                                 rechunk=rechunk,
                                 version=zarr_version
                                )
                            )
    
        # Release resources to avoid memory leaks:
        ds_filepath.close()
        
    else:
        # === Update Existing Zarr Store === #
        # Write to zarr store:
        dest = f"{bucket}/{object_prefix}"
        logging.info(f"Updating Dataset at {dest}")
        asyncio.run(
            _update_zarr(data=ds_filepath,
                         obj_store=obj_store,
                         dest=dest,
                         append_dim=append_dim,
                         rechunk=rechunk,
                         version=zarr_version
                        )
                    )
        
        # Release resources to avoid memory leaks:
        ds_filepath.close()


def update_with_dask(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    variables: list[str] | str = 'all',
    send_vars_indep: bool = True,
    append_dim: str = "time_counter",
    grid_filepath: Optional[str] = None,
    update_coords: Optional[dict] = None,
    rechunk: Optional[dict] = None,
    attrs: Optional[dict] = None,
    dask_config_kwargs: Optional[dict] = None,
    dask_cluster_kwargs: Optional[dict] = None,
    zarr_version: int = 3
    ) -> None:
    """
    Update existing zarr store in cloud object storage
    in parallel using dask.

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
    variables: list, default='all'
        List of variables to send to zarr stores.
        If None, all variables will be sent.
    send_vars_indep: bool, default=True
        Whether to send variables as separate objects.
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
    dask_config_kwargs: dict, optional
        Dask configuration settings passed to dask.config.set().
    dask_cluster_kwargs: dict, optional
        Dask cluster configuration settings passed to LocalCluster().
    zarr_version: int, default=3
        zarr version to use.
    """
    # === Configure Cluster === #
    # Update dask configuration settings:
    if dask_config_kwargs is not None:
        dask.config.set(dask_config_kwargs)
        logging.info("Updated dask configuration settings.")

    # Create local dask cluster & client:
    with LocalCluster(**dask_cluster_kwargs) as cluster, Client(cluster, asynchronous=False) as client:
        logging.info(f"Created LocalCluster with {dask_cluster_kwargs["n_workers"]} workers @ Client: {client.dashboard_link}")

        # === Register Dask Worker Plugin === #
        # Catch UserWarnings when rechunking:
        client.register_worker_plugin(CaptureWarningsPlugin())

        # === Initialise asynchronous object store === #
        logging.info("Reading object store credentials from %s", store_credentials_json)
        obj_store = ObjectStoreS3(anon=False,
                                  asynchronous=True,
                                  store_credentials_json=store_credentials_json
                                  )

        # === Preprocess data === #
        ds_filepath = _preprocess_dataset(file=file,
                                          rechunk=rechunk,
                                          append_dim=append_dim,
                                          update_coords=update_coords,
                                          grid_filepath=grid_filepath,
                                          attrs=attrs,
                                          parallel=True
                                          )
        
        # === Send variables to individual zarr stores === #
        if send_vars_indep:
            if variables is None:
                variables = list(ds_filepath.data_vars)

            for var in variables:
                if append_dim not in ds_filepath[var].dims:
                    logging.info(f"Skipping Variable: append dimension {append_dim} not found.")
                else:
                    logging.info(f"Updating Variable {var}")
                    dest = f"{bucket}/{object_prefix}/{var}"
                    asyncio.run(
                        _update_zarr(data=ds_filepath[var],
                                     obj_store=obj_store,
                                     dest=dest,
                                     append_dim=append_dim,
                                     rechunk=rechunk,
                                     version=zarr_version
                                    )
                                )

            # Release resources to avoid memory leaks:
            ds_filepath.close()
            
        else:
            # === Send Dataset to Object Store === #
            # Write to zarr store:
            dest = f"{bucket}/{object_prefix}"
            logging.info(f"Updating Dataset at {dest}")
            asyncio.run(
                _update_zarr(data=ds_filepath,
                             obj_store=obj_store,
                             dest=dest,
                             append_dim=append_dim,
                             rechunk=rechunk,
                             version=zarr_version
                            )
                        )

            # Release resources to avoid memory leaks:
            ds_filepath.close()
            
        # === Shutdown Store & Dask Cluster === #
        client.run(_close_session, (obj_store), wait=True)
        client.shutdown()
        client.close()
        logging.info("Dask Cluster has been shutdown.")


def update_zarr(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    variables: list[str] | str = 'all',
    send_vars_indep: bool = True,
    append_dim: str = "time_counter",
    grid_filepath: Optional[str] = None,
    update_coords: Optional[dict] = None,
    rechunk: Optional[dict] = None,
    attrs: Optional[dict] = None,
    dask_config_kwargs: Optional[dict] = None,
    dask_cluster_kwargs: Optional[dict] = None,
    zarr_version: int = 3
    ) -> None:
    """
    Update existing zarr store in cloud object storage
    in serial or in parallel using a dask local cluster.

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
    variables: list, default='all'
        List of variables to send to zarr stores.
        If None, all variables will be sent.
    send_vars_indep: bool, default=True
        Whether to send variables as separate objects.
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
    dask_config_kwargs: Dict[str,str], optional
        Dask configuration settings passed to dask.config.set().
    dask_cluster_kwargs: dict, optional
        Dask cluster configuration settings passed to LocalCluster().
    zarr_version: int, default=3
        zarr version to use.
    """
    # === Update zarr store without dask === #
    if (dask_config_kwargs is None) and (dask_cluster_kwargs is None):
        update(file,
               bucket,
               object_prefix,
               store_credentials_json,
               variables,
               send_vars_indep,
               append_dim,
               grid_filepath,
               update_coords,
               rechunk,
               attrs,
               zarr_version
               )
    # === Update zarr store with dask === #
    else:
        update_with_dask(file,
                         bucket,
                         object_prefix,
                         store_credentials_json,
                         variables,
                         send_vars_indep,
                         append_dim,
                         grid_filepath,
                         update_coords,
                         rechunk,
                         attrs,
                         dask_config_kwargs,
                         dask_cluster_kwargs,
                         zarr_version
                         )


def _update_icechunk(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    variables: list[str] | str = 'all',
    send_vars_indep: bool = True,
    append_dim: Optional[str] = 'time_counter',
    grid_filepath: Optional[str] = None,
    update_coords: Optional[dict] = None,
    rechunk: Optional[dict] = None,
    attrs: Optional[dict] = None,
    branch: str = "main",
    commit_message: str = "Update data in my Icechunk repository",
    variable_commits: bool = False,
    icechunk_config: Optional[dict] = None,
    ) -> None:
    """
    Update data in existing Icechunk repository in cloud object storage.

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
    variables: list | str, default="all"
        List of variables to send. If None, all variables will be sent.
    send_vars_indep: bool, default=True
        Whether to send variables as separate objects, by default True.
    append_dim: str, default='time_counter'
        Name of the dimension to append multifile datasets.
    grid_filepath: str, optional
        Path to file containing model grid parameter.
    update_coords: dict, optional
        Dictionary of coordinate variables to update.
    rechunk: dict, optional
        Rechunk strategy dictionary, by default None.
    attrs: dict, optional
        Attributes to add to the dataset.
    branch: str, default="main"
        Branch on which to write data to IcechunkStore.
    commit_message: str, default="Update commit"
        Commit message when updating the Icechunk repository.
    variable_commits: bool, default=False
        Whether to write each variable to Icechunk repository using
        separate commits.
    icechunk_config: dict, optional
        Icechunk repository configuration.
    """
    # === Initialise Synchronous Object Store === #
    logging.info("Reading object store credentials from %s", store_credentials_json)
    obj_store = ObjectStoreS3(anon=False,
                              asynchronous=False,
                              store_credentials_json=store_credentials_json
                              )

    if icechunk_config is None:
        icechunk_config = {"storage_config_kwargs":{},
                           "repository_config_kwargs":{},
                           "storage_settings_kwargs":{}
                           }

    # === Preprocess Data === #
    ds_filepath = _preprocess_dataset(file=file,
                                      rechunk=rechunk,
                                      append_dim=append_dim,
                                      update_coords=update_coords,
                                      grid_filepath=grid_filepath,
                                      attrs=attrs,
                                      parallel=True,
                                      )

    if variables is None:
        variables = list(ds_filepath.data_vars)
    # Consider variables with append dimension only:
    variables = [var for var in variables if append_dim in ds_filepath[var].dims]

    # === Update Variables in Individual Icechunk Repos === #
    if send_vars_indep:
        for var in variables:
            logging.info(f"Updating Variable {var}")
            try:
                # Open existing Icechunk repo:
                repo = obj_store.open_icechunk_repo(bucket=bucket,
                                                    prefix=f"{object_prefix}/{var}",
                                                    storage_config_kwargs=icechunk_config["storage_config_kwargs"],
                                                    repository_config_kwargs=icechunk_config["repository_config_kwargs"],
                                                    storage_settings_kwargs=icechunk_config["storage_settings_kwargs"],
                                                    )
                # Update and commit to the repo:
                _update_icechunk_store(data=ds_filepath[var],
                                       dest=f"{bucket}/{object_prefix}/{var}",
                                       repo=repo,
                                       commit_message=commit_message,
                                       branch=branch,
                                       append_dim=append_dim,
                                       rechunk=rechunk,
                                       )
            except icechunk.IcechunkError:
                logging.info(f"Skipping Variable: Icechunk repository does not exist at {bucket}/{object_prefix}/{var}")

        # Release resources to avoid memory leaks:
        ds_filepath.close()

    else:
        # === Update Variables in Single Icechunk Repo === #
        try:
            # Open existing Icechunk repo:
            repo = obj_store.open_icechunk_repo(bucket=bucket,
                                                prefix=object_prefix,
                                                storage_config_kwargs=icechunk_config["storage_config_kwargs"],
                                                repository_config_kwargs=icechunk_config["repository_config_kwargs"],
                                                storage_settings_kwargs=icechunk_config["storage_settings_kwargs"],
                                                )

            if variable_commits:
                for var in variables:
                    logging.info(f"Updating Variable {var}")
                    # Update each variable using separate commits to the repo:
                    _update_icechunk_store(data=ds_filepath[var],
                                           dest=f"{bucket}/{object_prefix}",
                                           repo=repo,
                                           commit_message=commit_message,
                                           branch=branch,
                                           append_dim=append_dim,
                                           rechunk=rechunk,
                                           )
            else:
                # Update dataset using single commit to the repo:
                logging.info(f"Updating Dataset {object_prefix}")
                _update_icechunk_store(data=ds_filepath,
                                       dest=f"{bucket}/{object_prefix}",
                                       repo=repo,
                                       commit_message=commit_message,
                                       branch=branch,
                                       append_dim=append_dim,
                                       rechunk=rechunk,
                                       )

        except icechunk.IcechunkError:
            logging.info(f"Skipping Dataset: Icechunk repository does not exist at {bucket}/{object_prefix}/{var}")

        # Release resources to avoid memory leaks:
        ds_filepath.close()


def update_icechunk(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    variables: list[str] | str = 'all',
    send_vars_indep: bool = True,
    append_dim: Optional[str] = 'time_counter',
    grid_filepath: Optional[str] = None,
    update_coords: Optional[dict] = None,
    rechunk: Optional[dict] = None,
    attrs: Optional[dict] = None,
    branch: str = "main",
    commit_message: str = "Update data in my Icechunk repository",
    variable_commits: bool = False,
    dask_config_kwargs: Optional[dict] = None,
    dask_cluster_kwargs: Optional[dict] = None,
    icechunk_config: Optional[dict] = None,
    ) -> None:
    """
    Update data in existing Icechunk repository in cloud object
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
    variables: list | str, default="all"
        List of variables to send. If None, all variables will be sent.
    send_vars_indep: bool, default=True
        Whether to send variables as separate objects, by default True.
    append_dim: str, default='time_counter'
        Name of the dimension to append multifile datasets.
    grid_filepath: str, optional
        Path to file containing model grid parameter.
    update_coords: dict, optional
        Dictionary of coordinate variables to update.
    rechunk: dict, optional
        Rechunk strategy dictionary, by default None.
    attrs: dict, optional
        Attributes to add to the dataset.
    branch: str, default="main"
        Branch on which to write data to IcechunkStore.
    commit_message: str, default="Initial commit"
        Commit message when updating the Icechunk repository.
    variable_commits: bool, default=False
        Whether to write each variable to Icechunk repository using
        separate commits.
    dask_config_kwargs: dict, optional
        Dask configuration settings passed to dask.config.set().
    dask_cluster_kwargs: dict, optional
        Dask cluster configuration settings passed to LocalCluster().
    icechunk_config: dict, optional
        Icechunk repository configuration.
    """
    # === Update Icechunk repo(s) with Dask === #
    if dask_cluster_kwargs is not None:
        if dask_config_kwargs is not None:
            dask.config.set(dask_config_kwargs)
            logging.info("Updated dask configuration settings.")

        # Create local dask cluster & client:
        with LocalCluster(**dask_cluster_kwargs) as cluster, Client(cluster) as client:
            logging.info(f"Created LocalCluster with {dask_cluster_kwargs["n_workers"]} workers @ Client: {client.dashboard_link}")

            # Catch UserWarnings when rechunking data:
            client.register_worker_plugin(CaptureWarningsPlugin())

            _update_icechunk(file=file,
                             bucket=bucket,
                             object_prefix=object_prefix,
                             store_credentials_json=store_credentials_json,
                             variables=variables,
                             send_vars_indep=send_vars_indep,
                             append_dim=append_dim,
                             grid_filepath=grid_filepath,
                             update_coords=update_coords,
                             rechunk=rechunk,
                             attrs=attrs,
                             branch=branch,
                             commit_message=commit_message,
                             variable_commits=variable_commits,
                             icechunk_config=icechunk_config
                             )

            # --- Shutdown Store & Dask Cluster --- #
            client.shutdown()
            client.close()
            logging.info("Dask Cluster has been shutdown.")
    
    else:
        # === Update Icechunk repo(s) without Dask === #
        _update_icechunk(file=file,
                         bucket=bucket,
                         object_prefix=object_prefix,
                         store_credentials_json=store_credentials_json,
                         variables=variables,
                         send_vars_indep=send_vars_indep,
                         append_dim=append_dim,
                         grid_filepath=grid_filepath,
                         update_coords=update_coords,
                         rechunk=rechunk,
                         attrs=attrs,
                         branch=branch,
                         commit_message=commit_message,
                         variable_commits=variable_commits,
                         icechunk_config=icechunk_config
                         )


def list_objects(
    dest: str,
    store_credentials_json: str,
    ) -> list[str]:
    """
    List the objects contained inside a bucket / object.

    Parameters
    ----------
    dest: str
        Destination path in the object store.
    store_credentials_json: str
        Path to the JSON file containing the object store credentials.

    Returns
    -------
    list[str]
        List of objects contained inside the bucket / object.
    """
    # === Initialise synchronous object store === #
    logging.info("Reading object store credentials from %s", store_credentials_json)
    obj_store = ObjectStoreS3(anon=False,
                              asynchronous=False,
                              store_credentials_json=store_credentials_json
                              )

    logging.info(obj_store.ls(dest))
