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
    version : int, default=3
        Zarr version to use.
    """
    def __init__(self, action: str, dest : str, version: int = 3) -> None:
        # Define class attributes:
        if action == 'send':
            self.action = 'Sent'
        elif action == 'replace':
            self.action = 'Updated'
        elif action == 'append':
            self.action = 'Appended to'
        else:
            raise ValueError("Invalid action: must be 'send', 'replace' or 'append'.")
        self.dest = dest
        self.version = version

    def __enter__(self):
        self.t_start = time.time()

    def __exit__(self, type, value, traceback):
        self.t_end = time.time()
        logging.info(
            f"Completed: {self.action} zarr v{self.version} store s3://{self.dest} in {(self.t_end - self.t_start):.2f} seconds"
            )

# -- Define OceanDataStore Core Functions -- #
async def _check_store(obj_store: ObjectStoreS3,
                       dest: str
                       ) -> bool:
    """
    Check if a destination path exists in the
    object store.

    Parameters
    ----------
    obj_store
        ObjectStoreS3 remote filesystem.
    dest
        Destination path in the object store.
    
    Returns
    -------
    bool
        True if the store exists, False otherwise.
    """
    store = zarr.storage.FsspecStore(fs=obj_store, path=dest)
    status = await store.exists("")
    await _close_session(obj_store=obj_store)

    return status


async def _check_compatibility(data: xr.DataArray | xr.Dataset,
                               obj_store: ObjectStoreS3,
                               dest: str,
                               append_dim: str = "time_counter",
                               rechunk: Optional[dict] = None,
                               version: int = 3,
                               ) -> None:
    """
    Check compatibility of DataArray or Dataset to update existing
    zarr store in Object Store.

    Parameters
    ----------
    data: xr.DataArray | xr.Dataset
        DataArray or DataSet to update existing zarr store with.
    obj_store: ObjectStoreS3
        ObjectStoreS3 remote filesystem.
    dest: str
        Destination path in the object store.
    append_dim: bool, default="time_counter"
        Name of the dimension to append to existing zarr store.
    rechunk: Optional[dict], default=None
        Rechunk strategy dictionary.
    version: int, default=3
        Zarr version to use.
    """
    # === Initialise store using fsspec === #
    store = zarr.storage.FsspecStore(fs=obj_store, path=dest)

    # 1. Check if the store exists:
    if not await _check_store(obj_store=obj_store, dest=dest):
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
        Destination path in the object store.
    version: int, default=3
        zarr version to use.
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
        data = data.to_dataset()

    # Write Dataset to Zarr store in Object Store:
    if await _check_store(obj_store=obj_store, dest=dest):
        logging.info(f"Skipping Variable: Store already exists at {dest}")

    else:
        with timer(action='send', dest=dest, version=version):
            # Catch consolidated metadata warnings:
            with warnings.catch_warnings():
                warnings.simplefilter(action="ignore", category=UserWarning)
                data.to_zarr(store=store, mode="w", zarr_format=version)

                await _close_session(obj_store=obj_store)


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
        Destination path in the object store.
    append_dim: str, default="time_counter"
        Name of the dimension to append to existing zarr store.
    version: int, default=3
        Zarr version to use.
    """
    # === Initialise store using fsspec === #
    store = zarr.storage.FsspecStore(fs=obj_store, path=dest)

    with timer(action='append', dest=dest, version=version):
        # Catch consolidated metadata warnings:
        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore", category=UserWarning)
            data.to_zarr(store=store, append_dim=append_dim, zarr_format=version)

            await _close_session(obj_store=obj_store)


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
        Destination path in the object store.
    region: dict
        Region of existing zarr store to overwrite defined by
        a dictionary of coordinate slices.
    version: int, default=3
        Zarr version to use.
    """
    # === Initialise store using fsspec === #
    store = zarr.storage.FsspecStore(fs=obj_store, path=dest)

    # Drop variables w/o append dimension:
    append_dim = list(region.keys())[0]
    drop_list = [var for var in data.variables if append_dim not in data[var].dims]
    data = data.drop_vars(drop_list)

    with timer(action='replace', dest=dest, version=version):
        # Catch consolidated metadata warnings:
        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore", category=UserWarning)
            data.to_zarr(store=store, region=region, zarr_format=version)

            await _close_session(obj_store=obj_store)


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
        Destination path in the object store.
    append_dim: bool, default="time_counter"
        Name of the dimension to append to existing zarr store.
    rechunk: Optional[dict], default=None
        Rechunk strategy dictionary.
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
    await _check_compatibility(data=ds_source,
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
        Alternatively, users can pass an xarray.Dataset directly.
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

    # === Send Variables to Individual Zarr Stores === #
    if send_vars_indep:
        if variables is None:
            variables = list(ds_filepath.data_vars)

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
            _write_to_zarr(data=ds_filepath,
                           obj_store=obj_store,
                           dest=dest,
                           version=zarr_version
                           )
                    )
        
        # Release resources to avoid memory leaks:
        ds_filepath.close()


def send_with_dask(
    file: list[str] | str,
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
    using dask local cluster.

    Parameters
    ----------
    file: list | str
        Regular expression or list of filepaths to netCDF file(s).
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
        
        # === Send Variables to Individual Zarr Stores === #
        if send_vars_indep:
            if variables is None:
                variables = list(ds_filepath.data_vars)

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
                _write_to_zarr(data=ds_filepath,
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
    file: list[str] | str,
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
    file: list | str
        Regular expression or list of filepaths to netCDF file(s).
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


def update(
        file: list[str] | str,
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
    by appending data in serial.

    Parameters
    ----------
    file: list | str
        Regular expression or list of filepaths to netCDF file(s).
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
    file: list[str] | str,
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
    in parallel using dask local cluster.

    Parameters
    ----------
    file: list | str
        Regular expression or list of filepaths to netCDF file(s).
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
    # === Verify Inputs === #
    if dask_config_kwargs is not None:
        if not isinstance(dask_config_kwargs, dict):
            raise TypeError("dask_config_kwargs must be a dictionary.")
    if dask_cluster_kwargs is not None:
        if not isinstance(dask_cluster_kwargs, dict):
            raise TypeError("dask_cluster_kwargs must be a dictionary.")

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
    file: list[str] | str,
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
    file: list | str
        Regular expression or list of filepaths to netCDF file(s).
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
