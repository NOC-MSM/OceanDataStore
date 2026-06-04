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
icechunk.py

Description:
This module defines the functions to send and update Icechunk Repositories
in cloud object storage.

Authors:
    - Ollie Tooth
"""
# -- Import Python Modules -- #
import logging
from typing import Optional

import dask
import icechunk
import icechunk.xarray as icechunk_xr
import numpy as np
import xarray as xr
from dask.distributed import Client, LocalCluster

from OceanDataStore.cli.exceptions import (
    AppendDimensionError,
    AppendDimensionSizeError,
    ChunkSizeError,
    DimensionNotFound,
    DimensionSizeError,
)
from OceanDataStore.cli.object_store import ObjectStoreS3
from OceanDataStore.cli.utils import (
    CaptureWarningsPlugin,
    _preprocess_dataset,
    timer,
)


# ======== Define Icechunk Validation Functions ======== #
def _check_icechunk_compatibility(
    data: xr.DataArray | xr.Dataset,
    dest: str,
    repo: icechunk.Repository,
    branch: str,
    append_dim: str,
    rechunk: dict,
    group: Optional[str] = None,
) -> None:
    """
    Check compatibility of DataArray or Dataset to update existing
    IcechunkStore in cloud object storage.

    Parameters
    ----------
    data: xr.DataArray | xr.Dataset
        DataArray or DataSet to update existing IcechunkStore.
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
    group: Optional[str], default=None
        Group in IcechunkStore to update.
    """
    # === Initialise IcechunkStore from session === #
    store = repo.readonly_session(branch=branch).store

    # 1. Check if IcechunkStore exists:
    try:
        ds_store = xr.open_zarr(store, group=group, consolidated=False)
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


# ======== Define Icechunk Writer Functions ======== #
def _write_to_icechunk(
    data: xr.DataArray | xr.Dataset,
    dest: str,
    repo: icechunk.Repository,
    commit_message: str,
    branch: Optional[str] = "main",
    group: Optional[str] = None,
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
    branch: Optional[str], default="main"
        Branch on which to write data to IcechunkStore.
    group: Optional[str], default=None
        Group in IcechunkStore to write data to.
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
        icechunk_xr.to_icechunk(data, session=session, group=group, mode='a')
        session.commit(message=commit_message)


def _append_to_icechunk(
    data: xr.DataArray | xr.Dataset,
    dest: str,
    repo: icechunk.Repository,
    commit_message: str,
    branch: Optional[str] = "main",
    group: Optional[str] = None,
    append_dim: Optional[str] = "time_counter",
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
    branch: Optional[str], default="main"
        Branch on which to write data to IcechunkStore.
    group: Optional[str], default=None
        Group in IcechunkStore to append data to.
    append_dim: Optional[str], default="time_counter"
        Dimension to append data to existing IcechunkStore.
    """
    # === Convert DataArrays to Datasets === #
    if isinstance(data, xr.DataArray):
        data = data.to_dataset()

    # === Append Data to IcechunkStore & Commit === #
    with timer(action='append', dest=dest):
        session = repo.writable_session(branch=branch)
        icechunk_xr.to_icechunk(obj=data, session=session, group=group, append_dim=append_dim)
        session.commit(message=commit_message)


def _replace_in_icechunk(
    data: xr.DataArray | xr.Dataset,
    dest: str,
    region: dict,
    repo: icechunk.Repository,
    commit_message: str,
    branch: Optional[str] = "main",
    group: Optional[str] = None,
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
    branch: Optional[str], default="main"
        Branch on which to write data to IcechunkStore.
    group: Optional[str], default=None
        Group in IcechunkStore to replace data in.
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
        icechunk_xr.to_icechunk(obj=data, session=session, region=region, group=group)
        session.commit(message=commit_message)


def _update_icechunk_store(
    data: xr.DataArray | xr.Dataset,
    dest: str,
    repo: icechunk.Repository,
    commit_message: str,
    branch: Optional[str] = "main",
    group: Optional[str] = None,
    append_dim: Optional[str] = "time_counter",
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
    group: Optional[str], default=None
        Group in IcechunkStore to update.
    append_dim: Optional[str], default="time_counter"
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
    ds_target = xr.open_zarr(store, group=group, consolidated=False)
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
                                    group=group
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
                                branch=branch,
                                group=group
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
                                    group=group,
                                    append_dim=append_dim
                                    )
        else:
            # == No intersection -> append all source values to target IcechunkStore == #
            logging.info(f"Appending to {dest} along {append_dim} from {source_append_dim[0]} to {source_append_dim[-1]}.")
            if var is not None:
                app_commit_message = f"{commit_message} -> Appended {var} along {append_dim} from {source_append_dim[0]} to {source_append_dim[-1]}."
            else:
                app_commit_message = f"{commit_message} -> Appended to {dest} along {append_dim} from {source_append_dim[0]} to {source_append_dim[-1]}."

            _append_to_icechunk(data=ds_source,
                                repo=repo,
                                dest=dest,
                                commit_message=app_commit_message,
                                branch=branch,
                                group=group,
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
                           group=group
                           )


def _send_to_icechunk(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    exists: Optional[bool] = False,
    group: Optional[str] = None,
    variables: Optional[list[str]] = None,
    append_dim: Optional[str] = 'time_counter',
    grid_filepath: Optional[str] = None,
    update_coords: Optional[dict] = None,
    rechunk: Optional[dict] = None,
    attrs: Optional[dict] = None,
    parallel: Optional[bool] = False,
    branch: Optional[str] = "main",
    commit_message: Optional[str] = "Add new data to my Icechunk repository",
    variable_commits: Optional[bool] = False,
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
    exists: Optional[bool], default=False
        Whether to write to an existing Icechunk repository or create a new repository.
    group: Optional[str], default=None
        Group in Icechunk repository to write data to.
    variables: Optional[list[str]], default=None
        List of variables to send. If None, all variables will be sent.
    append_dim: Optional[str], default='time_counter'
        Name of the dimension to append multifile datasets.
    grid_filepath: Optional[str], default=None
        Path to file containing model grid parameter.
    update_coords: Optional[dict], default=None
        Dictionary of coordinate variables to update.
    rechunk: Optional[dict], default=None
        Rechunk strategy dictionary, by default None.
    attrs: Optional[dict], default=None
        Attributes to add to the dataset.
    parallel: Optional[bool], default=False
        Whether to perform open and preprocess steps in parallel using
        `dask.delayed`.
    branch: Optional[str], default="main"
        Branch on which to write data to IcechunkStore.
    commit_message: Optional[str], default="Initial commit"
        Commit message when updating the Icechunk repository.
    variable_commits: Optional[bool], default=False
        Whether to write each variable to Icechunk repository using
        separate commits.
    icechunk_config: Optional[dict], default=None
        Icechunk repository configuration.
    """
    # === Initialise Synchronous Object Store === #
    logging.info("Reading object store credentials from %s", store_credentials_json)
    obj_store = ObjectStoreS3(anon=False,
                              asynchronous=False,
                              store_credentials_json=store_credentials_json
                              )

    if icechunk_config is None:
        icechunk_config = {"storage_config_kwargs": {'region': 'us-east-1', 'force_path_style': True},
                           "repository_config_kwargs": {},
                           "storage_settings_kwargs": {'unsafe_use_conditional_update': False, 'unsafe_use_conditional_create': False},
                           }

    # === Preprocess Data === #
    ds_filepath = _preprocess_dataset(file=file,
                                      rechunk=rechunk,
                                      append_dim=append_dim,
                                      update_coords=update_coords,
                                      grid_filepath=grid_filepath,
                                      attrs=attrs,
                                      parallel=parallel,
                                      )

    # Consider variables with append dimension only:
    if variables is None:
        variables = list(ds_filepath.data_vars)
    
    # Extract append dimension values:
    if append_dim in ds_filepath.dims:
        source_append_dim = ds_filepath[append_dim].values

    # === Send Variables to Icechunk Repo === #
    if exists:
    # Open existing Icechunk repo:
        try:
            repo = obj_store.open_icechunk_repo(bucket=bucket,
                                                prefix=object_prefix,
                                                storage_config_kwargs=icechunk_config["storage_config_kwargs"],
                                                repository_config_kwargs=icechunk_config["repository_config_kwargs"],
                                                storage_settings_kwargs=icechunk_config["storage_settings_kwargs"],
                                                )
        except icechunk.IcechunkError:
            logging.info(f"Failed to open existing Icechunk repository at {bucket}/{object_prefix}")

    else:
        try:
            # Create new Icechunk repo:
            repo = obj_store.create_icechunk_repo(bucket=bucket,
                                                prefix=object_prefix,
                                                storage_config_kwargs=icechunk_config["storage_config_kwargs"],
                                                repository_config_kwargs=icechunk_config["repository_config_kwargs"],
                                                storage_settings_kwargs=icechunk_config["storage_settings_kwargs"],
                                                )
        except icechunk.IcechunkError:
            logging.info(f"Failed to create new Icechunk repository at {bucket}/{object_prefix}")

    # Write data to Icechunk repository:
    if variable_commits:
        for var in variables:
            logging.info(f"Sending Variable: {var}")
            if append_dim in ds_filepath[var].dims:
                snd_commit_message = f"{commit_message} -> Sent {var} along {append_dim} from {source_append_dim[0]} to {source_append_dim[-1]}."
            else:
                snd_commit_message = f"{commit_message} -> Sent {var}."

            # Write each variable using separate commits to the repo:
            _write_to_icechunk(data=ds_filepath[var],
                                dest=f"{bucket}/{object_prefix}",
                                repo=repo,
                                commit_message=snd_commit_message,
                                branch=branch,
                                group=group
                                )
    else:
        # Write all variables using single commit to the repo:
        logging.info(f"Sending Dataset: {object_prefix}")
        if append_dim in ds_filepath.dims:
            snd_commit_message = f"{commit_message} -> Sent dataset along {append_dim} from {source_append_dim[0]} to {source_append_dim[-1]}."
        else:
            snd_commit_message = f"{commit_message} -> Sent dataset."

        _write_to_icechunk(data=ds_filepath[variables],
                            dest=f"{bucket}/{object_prefix}",
                            repo=repo,
                            commit_message=snd_commit_message,
                            branch=branch,
                            group=group
                            )

    # Release resources to avoid memory leaks:
    ds_filepath.close()


def _update_icechunk(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    group: Optional[str] = None,
    variables: Optional[list[str]] = None,
    append_dim: Optional[str] = 'time_counter',
    grid_filepath: Optional[str] = None,
    update_coords: Optional[dict] = None,
    rechunk: Optional[dict] = None,
    attrs: Optional[dict] = None,
    parallel: bool = False,
    branch: str = "main",
    commit_message: str = "Update data in my Icechunk repository",
    icechunk_config: Optional[dict] = None,
) -> None:
    """
    Update data in existing Icechunk repository in cloud object storage
    by replacing and/or appending data.

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
    group: Optional[str], default=None
        Group in Icechunk repository to write data to.
    variables: Optional[list[str]], default=None
        List of variables to send. If None, all variables will be sent.
    append_dim: Optional[str], default='time_counter'
        Name of the dimension to append multifile datasets.
    grid_filepath: Optional[str], default=None
        Path to file containing model grid parameter.
    update_coords: Optional[dict], default=None
        Dictionary of coordinate variables to update.
    rechunk: Optional[dict], default=None
        Rechunk strategy dictionary, by default None.
    attrs: Optional[dict], default=None
        Attributes to add to the dataset.
    parallel: Optional[bool], default=False
        Whether to perform open and preprocess steps in parallel using
        `dask.delayed`.
    branch: Optional[str], default="main"
        Branch on which to write data to IcechunkStore.
    commit_message: Optional[str], default="Update commit"
        Commit message when updating the Icechunk repository.
    icechunk_config: Optional[dict], default=None
        Icechunk repository configuration.
    """
    # === Initialise Synchronous Object Store === #
    logging.info("Reading object store credentials from %s", store_credentials_json)
    obj_store = ObjectStoreS3(anon=False,
                              asynchronous=False,
                              store_credentials_json=store_credentials_json
                              )

    if icechunk_config is None:
        icechunk_config = {"storage_config_kwargs": {'region': 'us-east-1', 'force_path_style': True},
                           "repository_config_kwargs": {},
                           "storage_settings_kwargs": {'unsafe_use_conditional_update': False, 'unsafe_use_conditional_create': False},
                           }

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

    # === Update Variables in Icechunk Repo === #
    try:
        # Open existing Icechunk repo:
        repo = obj_store.open_icechunk_repo(bucket=bucket,
                                            prefix=object_prefix,
                                            storage_config_kwargs=icechunk_config["storage_config_kwargs"],
                                            repository_config_kwargs=icechunk_config["repository_config_kwargs"],
                                            storage_settings_kwargs=icechunk_config["storage_settings_kwargs"],
                                            )

        # Update dataset using single commit to the repo:
        logging.info(f"Updating Dataset {object_prefix}")
        _update_icechunk_store(data=ds_filepath[variables],
                                dest=f"{bucket}/{object_prefix}",
                                repo=repo,
                                commit_message=commit_message,
                                branch=branch,
                                group=group,
                                append_dim=append_dim,
                                rechunk=rechunk,
                                )

    except icechunk.IcechunkError:
        logging.info(f"Skipping Dataset: Icechunk repository does not exist at {bucket}/{object_prefix}")

    # Release resources to avoid memory leaks:
    ds_filepath.close()


# ============ Define Public Functions ============ #
def send_to_icechunk(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    exists: Optional[bool] = False,
    group: Optional[str] = None,
    variables: Optional[list[str]] = None,
    append_dim: Optional[str] = 'time_counter',
    grid_filepath: Optional[str] = None,
    update_coords: Optional[dict] = None,
    rechunk: Optional[dict] = None,
    attrs: Optional[dict] = None,
    branch: Optional[str] = "main",
    commit_message: Optional[str] = "Add new data to my Icechunk repository",
    variable_commits: Optional[bool] = False,
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
    exists: Optional[bool], default=False
        Whether to write to an existing Icechunk repository or create a new repository.
    group: Optional[str], default=None
        Group in Icechunk repository to write data to.
    variables: Optional[list[str]], default=None
        List of variables to send. If None, all variables will be sent.
    append_dim: Optional[str], default='time_counter'
        Name of the dimension to append multifile datasets.
    grid_filepath: Optional[str], default=None
        Path to file containing model grid parameter.
    update_coords: Optional[dict], default=None
        Dictionary of coordinate variables to update.
    rechunk: Optional[dict], default=None
        Rechunk strategy dictionary, by default None.
    attrs: Optional[dict], default=None
        Attributes to add to the dataset.
    branch: Optional[str], default="main"
        Branch on which to write data to IcechunkStore.
    commit_message: Optional[str], default="Initial commit"
        Commit message when updating the Icechunk repository.
    variable_commits: Optional[bool], default=False
        Whether to write each variable to Icechunk repository using
        separate commits.
    dask_config_kwargs: Optional[dict], default=None
        Dask configuration settings passed to dask.config.set().
    dask_cluster_kwargs: Optional[dict], default=None
        Dask cluster configuration settings passed to LocalCluster().
    icechunk_config: Optional[dict], default=None
        Icechunk repository configuration.
    """
    if dask_cluster_kwargs is not None:
        # === Send to Icechunk repo(s) with Dask === #
        if dask_config_kwargs is not None:
            dask.config.set(dask_config_kwargs)
            logging.info("Updated dask configuration settings.")

        # Create local dask cluster & client:
        with LocalCluster(**dask_cluster_kwargs) as cluster, Client(cluster) as client:
            logging.info(f"Created LocalCluster with {dask_cluster_kwargs['n_workers']} workers @ Client: {client.dashboard_link}")

            # Catch UserWarnings when rechunking data:
            client.register_worker_plugin(CaptureWarningsPlugin())

            _send_to_icechunk(file=file,
                              bucket=bucket,
                              object_prefix=object_prefix,
                              store_credentials_json=store_credentials_json,
                              exists=exists,
                              group=group,
                              variables=variables,
                              append_dim=append_dim,
                              grid_filepath=grid_filepath,
                              update_coords=update_coords,
                              rechunk=rechunk,
                              attrs=attrs,
                              parallel=True,
                              branch=branch,
                              commit_message=commit_message,
                              variable_commits=variable_commits,
                              icechunk_config=icechunk_config
                              )

            # --- Shutdown Store & Dask Cluster --- #
            cluster.close()
            client.shutdown()
            logging.info("Dask Cluster has been shutdown.")
    
    else:
        # === Send to Icechunk repo(s) without Dask === #
        _send_to_icechunk(file=file,
                          bucket=bucket,
                          object_prefix=object_prefix,
                          store_credentials_json=store_credentials_json,
                          exists=exists,
                          group=group,
                          variables=variables,
                          append_dim=append_dim,
                          grid_filepath=grid_filepath,
                          update_coords=update_coords,
                          rechunk=rechunk,
                          attrs=attrs,
                          parallel=False,
                          branch=branch,
                          commit_message=commit_message,
                          variable_commits=variable_commits,
                          icechunk_config=icechunk_config
                          )


def update_icechunk(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    group: Optional[str] = None,
    variables: Optional[list[str]] = None,
    append_dim: Optional[str] = 'time_counter',
    grid_filepath: Optional[str] = None,
    update_coords: Optional[dict] = None,
    rechunk: Optional[dict] = None,
    attrs: Optional[dict] = None,
    branch: Optional[str] = "main",
    commit_message: Optional[str] = "Update data in my Icechunk repository",
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
    group: Optional[str], default=None
        Group in Icechunk repository to write data to.
    variables: Optional[list[str]], default=None
        List of variables to send. If None, all variables will be sent.
    append_dim: Optional[str], default='time_counter'
        Name of the dimension to append multifile datasets.
    grid_filepath: Optional[str], default=None
        Path to file containing model grid parameter.
    update_coords: Optional[dict], default=None
        Dictionary of coordinate variables to update.
    rechunk: Optional[dict], default=None
        Rechunk strategy dictionary, by default None.
    attrs: Optional[dict], default=None
        Attributes to add to the dataset.
    branch: Optional[str], default="main"
        Branch on which to write data to IcechunkStore.
    commit_message: Optional[str], default="Initial commit"
        Commit message when updating the Icechunk repository.
    dask_config_kwargs: Optional[dict], default=None
        Dask configuration settings passed to dask.config.set().
    dask_cluster_kwargs: Optional[dict], default=None
        Dask cluster configuration settings passed to LocalCluster().
    icechunk_config: Optional[dict], default=None
        Icechunk repository configuration.
    """
    # === Update Icechunk repo(s) with Dask === #
    if dask_cluster_kwargs is not None:
        if dask_config_kwargs is not None:
            dask.config.set(dask_config_kwargs)
            logging.info("Updated dask configuration settings.")

        # Create local dask cluster & client:
        with LocalCluster(**dask_cluster_kwargs) as cluster, Client(cluster) as client:
            logging.info(f"Created LocalCluster with {dask_cluster_kwargs['n_workers']} workers @ Client: {client.dashboard_link}")

            # Catch UserWarnings when rechunking data:
            client.register_worker_plugin(CaptureWarningsPlugin())

            _update_icechunk(file=file,
                             bucket=bucket,
                             object_prefix=object_prefix,
                             store_credentials_json=store_credentials_json,
                             group=group,
                             variables=variables,
                             append_dim=append_dim,
                             grid_filepath=grid_filepath,
                             update_coords=update_coords,
                             rechunk=rechunk,
                             attrs=attrs,
                             parallel=True,
                             branch=branch,
                             commit_message=commit_message,
                             icechunk_config=icechunk_config
                             )

            # --- Shutdown Store & Dask Cluster --- #
            cluster.close()
            client.shutdown()
            logging.info("Dask Cluster has been shutdown.")
    
    else:
        # === Update Icechunk repo(s) without Dask === #
        _update_icechunk(file=file,
                         bucket=bucket,
                         object_prefix=object_prefix,
                         store_credentials_json=store_credentials_json,
                         group=group,
                         variables=variables,
                         append_dim=append_dim,
                         grid_filepath=grid_filepath,
                         update_coords=update_coords,
                         rechunk=rechunk,
                         attrs=attrs,
                         parallel=False,
                         branch=branch,
                         commit_message=commit_message,
                         icechunk_config=icechunk_config
                         )
