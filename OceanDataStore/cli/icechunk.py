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
This module defines the functions to send and update Icechunk repositories
in cloud object storage.

Authors:
    - Ollie Tooth
"""

import copy
import logging
from typing import Any

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
from OceanDataStore.cli.object_store import DEFAULT_ICECHUNK_CONFIG, ObjectStoreS3
from OceanDataStore.cli.utils import (
    CaptureWarningsPlugin,
    Timer,
    _preprocess_dataset,
)

logger = logging.getLogger(__name__)


# ======== Define Icechunk Validation Functions ======== #
def _check_icechunk_compatibility(
    data: xr.DataArray | xr.Dataset,
    dest: str,
    repo: icechunk.Repository,
    branch: str,
    append_dim: str,
    rechunk: dict[str, int] | None,
    group: str | None = None,
) -> None:
    """
    Check compatibility of data to update an existing IcechunkStore.

    Parameters
    ----------
    data : xarray.DataArray | xarray.Dataset
        Data used to update the existing IcechunkStore.
    dest : str
        Path to Icechunk repository in the object store.
    repo : icechunk.Repository
        Icechunk repository containing the IcechunkStore.
    branch : str
        Branch of the Icechunk repository to read.
    append_dim : str
        Dimension along which data is appended to the IcechunkStore.
    rechunk : dict[str, int] | None
        Mapping of dimension names to requested chunk sizes.
    group : str | None, default None
        Group in IcechunkStore to update.

    Raises
    ------
    FileNotFoundError
        If the IcechunkStore (group) does not exist on the branch.
    DimensionSizeError
        If a non-append dimension differs in size from the IcechunkStore.
    DimensionNotFound
        If a non-append dimension is missing from the IcechunkStore.
    AppendDimensionError
        If ``data`` starts before the IcechunkStore along ``append_dim``.
    ChunkSizeError
        If ``rechunk`` differs from the IcechunkStore chunks.
    """
    # === Initialise IcechunkStore from session === #
    store = repo.readonly_session(branch=branch).store

    # 1. Check if IcechunkStore exists:
    try:
        ds_store = xr.open_zarr(store, group=group, consolidated=False)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"IcechunkStore not found in repository: {e}") from e

    # 2. Check if core dimensions exist in IcechunkStore & sizes are consistent:
    dims_data = {dim: data.sizes[dim] for dim in data.dims if dim != append_dim}
    for dim, value in dims_data.items():
        if dim in ds_store.dims:
            if value != ds_store.sizes[dim]:
                raise DimensionSizeError(dim=dim, size=value, expected_size=ds_store.sizes[dim])
        else:
            raise DimensionNotFound(dim=dim, object_name=dest)

    # 3. Check if append dimension values are consistent:
    if data[append_dim][0] < ds_store[append_dim][0]:
        raise AppendDimensionError(dim=append_dim)

    # 4. Check if specified chunks are consistent:
    if rechunk is not None:
        for dim, value in rechunk.items():
            if (dim in ds_store.dims) and (value != ds_store.chunks[dim][0]):
                raise ChunkSizeError(chunks=rechunk, store_chunks=ds_store.chunks)


# ======== Define Icechunk Writer Functions ======== #
def _write_to_icechunk(
    data: xr.DataArray | xr.Dataset,
    dest: str,
    repo: icechunk.Repository,
    commit_message: str,
    branch: str = "main",
    group: str | None = None,
) -> None:
    """
    Write data to an IcechunkStore and commit to the repository.

    Parameters
    ----------
    data : xarray.DataArray | xarray.Dataset
        Data to write to the IcechunkStore.
    dest : str
        Path to Icechunk repository in the object store.
    repo : icechunk.Repository
        Icechunk repository in which to write data.
    commit_message : str
        Commit message recorded in the Icechunk repository.
    branch : str, default "main"
        Branch on which to commit data.
    group : str | None, default None
        Group in IcechunkStore to write data to.
    """
    # === Convert DataArrays to Datasets === #
    if isinstance(data, xr.DataArray):
        var = data.name
        data = data.to_dataset()
    else:
        var = None

    # === Write Data to IcechunkStore & Commit === #
    with Timer(action="send", dest=dest, var=var):
        session = repo.writable_session(branch=branch)
        icechunk_xr.to_icechunk(data, session=session, group=group, mode="a")
        session.commit(message=commit_message)


def _append_to_icechunk(
    data: xr.DataArray | xr.Dataset,
    dest: str,
    repo: icechunk.Repository,
    commit_message: str,
    branch: str = "main",
    group: str | None = None,
    append_dim: str = "time_counter",
) -> None:
    """
    Append data to an existing IcechunkStore and commit to the repository.

    Parameters
    ----------
    data : xarray.DataArray | xarray.Dataset
        Data to append to the existing IcechunkStore.
    dest : str
        Path to Icechunk repository in the object store.
    repo : icechunk.Repository
        Icechunk repository in which to append data.
    commit_message : str
        Commit message recorded in the Icechunk repository.
    branch : str, default "main"
        Branch on which to commit data.
    group : str | None, default None
        Group in IcechunkStore to append data to.
    append_dim : str, default "time_counter"
        Dimension along which to append data.
    """
    # === Convert DataArrays to Datasets === #
    if isinstance(data, xr.DataArray):
        data = data.to_dataset()

    # === Append Data to IcechunkStore & Commit === #
    with Timer(action="append", dest=dest):
        session = repo.writable_session(branch=branch)
        icechunk_xr.to_icechunk(obj=data, session=session, group=group, append_dim=append_dim)
        session.commit(message=commit_message)


def _replace_in_icechunk(
    data: xr.DataArray | xr.Dataset,
    dest: str,
    region: dict[str, slice],
    repo: icechunk.Repository,
    commit_message: str,
    branch: str = "main",
    group: str | None = None,
) -> None:
    """
    Replace a region of an existing IcechunkStore and commit to the repository.

    Variables which do not include the region dimension are dropped
    before writing.

    Parameters
    ----------
    data : xarray.DataArray | xarray.Dataset
        Data used to replace values in the existing IcechunkStore.
    dest : str
        Path to Icechunk repository in the object store.
    region : dict[str, slice]
        Mapping of the append dimension name to the index slice of the
        IcechunkStore to replace.
    repo : icechunk.Repository
        Icechunk repository in which to replace data.
    commit_message : str
        Commit message recorded in the Icechunk repository.
    branch : str, default "main"
        Branch on which to commit data.
    group : str | None, default None
        Group in IcechunkStore in which to replace data.
    """
    # === Convert DataArrays to Datasets === #
    if isinstance(data, xr.DataArray):
        data = data.to_dataset()

    # Drop variables w/o append dimension:
    append_dim = next(iter(region.keys()))
    drop_list = [var for var in data.variables if append_dim not in data[var].dims]
    data = data.drop_vars(drop_list)

    # === Write Data to IcechunkStore & Commit === #
    with Timer(action="replace", dest=dest):
        session = repo.writable_session(branch=branch)
        icechunk_xr.to_icechunk(obj=data, session=session, region=region, group=group)
        session.commit(message=commit_message)


def _update_icechunk_store(
    data: xr.DataArray | xr.Dataset,
    dest: str,
    repo: icechunk.Repository,
    commit_message: str,
    branch: str = "main",
    group: str | None = None,
    append_dim: str = "time_counter",
    rechunk: dict[str, int] | None = None,
) -> None:
    """
    Update an existing IcechunkStore by replacing and/or appending values.

    Source values which overlap the IcechunkStore along ``append_dim`` are
    replaced (one commit) and remaining source values are appended (one
    commit). A DataArray whose variable does not exist in the store is
    written as a new variable.

    Parameters
    ----------
    data : xarray.DataArray | xarray.Dataset
        Data used to update the existing IcechunkStore.
    dest : str
        Path to Icechunk repository in the object store.
    repo : icechunk.Repository
        Icechunk repository containing the IcechunkStore.
    commit_message : str
        Commit message prefix recorded in the Icechunk repository.
    branch : str, default "main"
        Branch on which to commit data.
    group : str | None, default None
        Group in IcechunkStore to update.
    append_dim : str, default "time_counter"
        Dimension along which to replace and/or append data.
    rechunk : dict[str, int] | None, default None
        Mapping of dimension names to requested chunk sizes.

    Raises
    ------
    AppendDimensionSizeError
        If overlapping source values are not all found in the IcechunkStore.
    """
    # Convert DataArrays to Datasets:
    if isinstance(data, xr.DataArray):
        var = data.name
        ds_source = data.to_dataset()
    else:
        var = None
        ds_source = data
    label = var if var is not None else dest

    # Extract source & target append dimension values:
    store = repo.readonly_session(branch=branch).store
    ds_target = xr.open_zarr(store, group=group, consolidated=False)
    target_append_dim = ds_target[append_dim].values
    source_append_dim = ds_source[append_dim].values

    if (var in ds_target.data_vars) or (var is None):
        # === Update existing variable in IcechunkStore === #
        _check_icechunk_compatibility(
            data=ds_source,
            dest=dest,
            repo=repo,
            branch=branch,
            append_dim=append_dim,
            rechunk=rechunk,
            group=group,
        )
        logger.info("Passed Compatibility Checks for IcechunkStore %s", dest)

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

            # 1. Replace overlapping values in target IcechunkStore:
            rep_start = target_append_dim[target_ind_min]
            rep_end = target_append_dim[target_ind_max - 1]
            logger.info("Updating %s along %s from %s to %s.", dest, append_dim, rep_start, rep_end)
            rep_commit_message = (
                f"{commit_message} -> Updated {label} along {append_dim} from {rep_start} to {rep_end}."
            )

            _replace_in_icechunk(
                data=ds_source.isel({append_dim: slice(source_ind_min, source_ind_max)}),
                repo=repo,
                dest=dest,
                region={append_dim: slice(target_ind_min, target_ind_max)},
                commit_message=rep_commit_message,
                branch=branch,
                group=group,
            )

            # 2. Append new values to target IcechunkStore:
            if source_ind_size > source_ind_max:
                app_start = source_append_dim[source_ind_max]
                app_end = source_append_dim[source_ind_size - 1]
                logger.info("Appending to %s along %s from %s to %s.", dest, append_dim, app_start, app_end)
                app_commit_message = (
                    f"{commit_message} -> Appended to {label} along {append_dim} from {app_start} to {app_end}."
                )

                _append_to_icechunk(
                    data=ds_source.isel({append_dim: slice(source_ind_max, source_ind_size)}),
                    repo=repo,
                    dest=dest,
                    commit_message=app_commit_message,
                    branch=branch,
                    group=group,
                    append_dim=append_dim,
                )
        else:
            # == No intersection -> append all source values to target IcechunkStore == #
            app_start = source_append_dim[0]
            app_end = source_append_dim[-1]
            logger.info("Appending to %s along %s from %s to %s.", dest, append_dim, app_start, app_end)
            if var is not None:
                app_commit_message = (
                    f"{commit_message} -> Appended {var} along {append_dim} from {app_start} to {app_end}."
                )
            else:
                app_commit_message = (
                    f"{commit_message} -> Appended to {dest} along {append_dim} from {app_start} to {app_end}."
                )

            _append_to_icechunk(
                data=ds_source,
                repo=repo,
                dest=dest,
                commit_message=app_commit_message,
                branch=branch,
                group=group,
                append_dim=append_dim,
            )
    else:
        # == Add new variable to IcechunkStore == #
        logger.info("Sending Variable %s", var)
        snd_commit_message = (
            f"{commit_message} -> Sent {var} along {append_dim} from {source_append_dim[0]} to {source_append_dim[-1]}."
        )
        _write_to_icechunk(
            data=ds_source,
            dest=dest,
            repo=repo,
            commit_message=snd_commit_message,
            branch=branch,
            group=group,
        )


def _send_to_icechunk(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    exists: bool = False,
    group: str | None = None,
    variables: list[str] | None = None,
    append_dim: str = "time_counter",
    grid_filepath: str | None = None,
    update_coords: dict[str, str] | None = None,
    rechunk: dict[str, int] | None = None,
    attrs: dict[str, Any] | None = None,
    parallel: bool = False,
    branch: str = "main",
    commit_message: str = "Sent data to Icechunk repository",
    variable_commits: bool = False,
    icechunk_config: dict[str, dict[str, Any]] | None = None,
) -> None:
    """
    Write data to an Icechunk repository in cloud object storage.

    See ``send_to_icechunk`` for a description of the parameters.
    ``parallel`` determines whether files are opened and preprocessed
    in parallel using ``dask.delayed``.
    """
    # === Initialise Synchronous Object Store === #
    logger.info("Reading object store credentials from %s", store_credentials_json)
    obj_store = ObjectStoreS3(anon=False, asynchronous=False, store_credentials_json=store_credentials_json)

    if icechunk_config is None:
        icechunk_config = copy.deepcopy(DEFAULT_ICECHUNK_CONFIG)

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

    # Extract append dimension values:
    if append_dim in ds_filepath.dims:
        source_append_dim = ds_filepath[append_dim].values
        append_range = f"along {append_dim} from {source_append_dim[0]} to {source_append_dim[-1]}"

    # === Send Variables to Icechunk Repo === #
    repo_kwargs = {
        "bucket": bucket,
        "prefix": object_prefix,
        "storage_config_kwargs": icechunk_config["storage_config_kwargs"],
        "repository_config_kwargs": icechunk_config["repository_config_kwargs"],
        "storage_settings_kwargs": icechunk_config["storage_settings_kwargs"],
    }
    if exists:
        # Open existing Icechunk repo:
        try:
            repo = obj_store.open_icechunk_repo(**repo_kwargs)
        except icechunk.IcechunkError:
            logger.info("Failed to open existing Icechunk repository at %s/%s", bucket, object_prefix)
    else:
        # Create new Icechunk repo:
        try:
            repo = obj_store.create_icechunk_repo(**repo_kwargs)
        except icechunk.IcechunkError:
            logger.info("Failed to create new Icechunk repository at %s/%s", bucket, object_prefix)

    dest = f"{bucket}/{object_prefix}"
    if variable_commits:
        # Write each variable using separate commits to the repo:
        for var in variables:
            logger.info("Sending Variable: %s", var)
            if append_dim in ds_filepath[var].dims:
                snd_commit_message = f"{commit_message} -> Sent {var} {append_range}."
            else:
                snd_commit_message = f"{commit_message} -> Sent {var}."

            _write_to_icechunk(
                data=ds_filepath[var],
                dest=dest,
                repo=repo,
                commit_message=snd_commit_message,
                branch=branch,
                group=group,
            )
    else:
        # Write all variables using single commit to the repo:
        logger.info("Sending Dataset: %s", object_prefix)
        if append_dim in ds_filepath.dims:
            snd_commit_message = f"{commit_message} -> Sent dataset {append_range}."
        else:
            snd_commit_message = f"{commit_message} -> Sent dataset."

        _write_to_icechunk(
            data=ds_filepath[variables],
            dest=dest,
            repo=repo,
            commit_message=snd_commit_message,
            branch=branch,
            group=group,
        )

    # Release resources to avoid memory leaks:
    ds_filepath.close()


def _update_icechunk(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    group: str | None = None,
    variables: list[str] | None = None,
    append_dim: str = "time_counter",
    grid_filepath: str | None = None,
    update_coords: dict[str, str] | None = None,
    rechunk: dict[str, int] | None = None,
    attrs: dict[str, Any] | None = None,
    parallel: bool = False,
    branch: str = "main",
    commit_message: str = "Updated data in Icechunk repository",
    icechunk_config: dict[str, dict[str, Any]] | None = None,
) -> None:
    """
    Update data in an existing Icechunk repository in cloud object storage.

    See ``update_icechunk`` for a description of the parameters.
    ``parallel`` determines whether files are opened and preprocessed
    in parallel using ``dask.delayed``.
    """
    # === Initialise Synchronous Object Store === #
    logger.info("Reading object store credentials from %s", store_credentials_json)
    obj_store = ObjectStoreS3(anon=False, asynchronous=False, store_credentials_json=store_credentials_json)

    if icechunk_config is None:
        icechunk_config = copy.deepcopy(DEFAULT_ICECHUNK_CONFIG)

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

    # === Update Variables in Icechunk Repo === #
    try:
        # Open existing Icechunk repo:
        repo = obj_store.open_icechunk_repo(
            bucket=bucket,
            prefix=object_prefix,
            storage_config_kwargs=icechunk_config["storage_config_kwargs"],
            repository_config_kwargs=icechunk_config["repository_config_kwargs"],
            storage_settings_kwargs=icechunk_config["storage_settings_kwargs"],
        )

        # Update dataset using single commit to the repo:
        logger.info("Updating Dataset %s", object_prefix)
        _update_icechunk_store(
            data=ds_filepath[variables],
            dest=f"{bucket}/{object_prefix}",
            repo=repo,
            commit_message=commit_message,
            branch=branch,
            group=group,
            append_dim=append_dim,
            rechunk=rechunk,
        )

    except icechunk.IcechunkError:
        logger.info("Skipping Dataset: Icechunk repository does not exist at %s/%s", bucket, object_prefix)

    # Release resources to avoid memory leaks:
    ds_filepath.close()


# ============ Define Public Functions ============ #
def send_to_icechunk(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    exists: bool = False,
    group: str | None = None,
    variables: list[str] | None = None,
    append_dim: str | None = None,
    grid_filepath: str | None = None,
    update_coords: dict[str, str] | None = None,
    rechunk: dict[str, int] | None = None,
    attrs: dict[str, Any] | None = None,
    branch: str | None = None,
    commit_message: str | None = None,
    variable_commits: bool = False,
    dask_config_kwargs: dict[str, Any] | None = None,
    dask_cluster_kwargs: dict[str, Any] | None = None,
    icechunk_config: dict[str, dict[str, Any]] | None = None,
) -> None:
    """
    Write data to an Icechunk repository in cloud object storage.

    Optionally uses a dask LocalCluster to open, preprocess and write data.

    Parameters
    ----------
    file : list[str] | str | xarray.Dataset
        Glob pattern, filepath or list of filepaths to netCDF file(s).
        Users can also pass a single xarray.Dataset directly.
    bucket : str
        Name of the bucket in the object store. Bucket names can contain only
        lowercase letters, numbers, dots (.), and hyphens (-).
    object_prefix : str
        Prefix of the Icechunk repository in the bucket.
    store_credentials_json : str
        Path to the JSON file containing the object store credentials.
    exists : bool, default False
        Whether to write to an existing Icechunk repository (True) or
        create a new repository (False).
    group : str | None, default None
        Group in Icechunk repository to write data to.
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
    branch : str | None, default None
        Branch on which to commit data. If None, 'main' is used.
    commit_message : str | None, default None
        Commit message prefix recorded in the Icechunk repository.
        If None, 'Sent data to Icechunk repository' is used.
    variable_commits : bool, default False
        Whether to write each variable to the Icechunk repository using
        a separate commit.
    dask_config_kwargs : dict[str, Any] | None, default None
        Dask configuration settings passed to ``dask.config.set()``.
        Only used when ``dask_cluster_kwargs`` is provided.
    dask_cluster_kwargs : dict[str, Any] | None, default None
        Keyword arguments passed to ``dask.distributed.LocalCluster()``.
        If None, dask is not used to parallelise the workflow.
    icechunk_config : dict[str, dict[str, Any]] | None, default None
        Icechunk configuration containing the keys ``storage_config_kwargs``,
        ``repository_config_kwargs`` and ``storage_settings_kwargs``.
        If None, ``DEFAULT_ICECHUNK_CONFIG`` is used.

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
    if branch is None:
        branch = "main"
    if commit_message is None:
        commit_message = "Sent data to Icechunk repository"

    send_kwargs = {
        "file": file,
        "bucket": bucket,
        "object_prefix": object_prefix,
        "store_credentials_json": store_credentials_json,
        "exists": exists,
        "group": group,
        "variables": variables,
        "append_dim": append_dim,
        "grid_filepath": grid_filepath,
        "update_coords": update_coords,
        "rechunk": rechunk,
        "attrs": attrs,
        "branch": branch,
        "commit_message": commit_message,
        "variable_commits": variable_commits,
        "icechunk_config": icechunk_config,
    }

    if dask_cluster_kwargs is not None:
        # === Send to Icechunk repo with Dask === #
        if dask_config_kwargs is not None:
            dask.config.set(dask_config_kwargs)
            logger.info("Updated dask configuration settings.")

        with LocalCluster(**dask_cluster_kwargs) as cluster, Client(cluster) as client:
            logger.info(
                "Created LocalCluster with %s workers @ Client: %s",
                dask_cluster_kwargs["n_workers"],
                client.dashboard_link,
            )
            # Catch UserWarnings when rechunking data:
            client.register_plugin(CaptureWarningsPlugin())

            _send_to_icechunk(**send_kwargs, parallel=True)

        logger.info("Dask Cluster has been shutdown.")

    else:
        # === Send to Icechunk repo without Dask === #
        _send_to_icechunk(**send_kwargs, parallel=False)


def update_icechunk(
    file: list[str] | str | xr.Dataset,
    bucket: str,
    object_prefix: str,
    store_credentials_json: str,
    group: str | None = None,
    variables: list[str] | None = None,
    append_dim: str | None = None,
    grid_filepath: str | None = None,
    update_coords: dict[str, str] | None = None,
    rechunk: dict[str, int] | None = None,
    attrs: dict[str, Any] | None = None,
    branch: str | None = None,
    commit_message: str | None = None,
    dask_config_kwargs: dict[str, Any] | None = None,
    dask_cluster_kwargs: dict[str, Any] | None = None,
    icechunk_config: dict[str, dict[str, Any]] | None = None,
) -> None:
    """
    Update data in an existing Icechunk repository in cloud object storage.

    Source values overlapping the repository along ``append_dim`` are
    replaced and remaining values are appended. Only variables including
    ``append_dim`` are updated. Optionally uses a dask LocalCluster.

    Parameters
    ----------
    file : list[str] | str | xarray.Dataset
        Glob pattern, filepath or list of filepaths to netCDF file(s).
        Users can also pass a single xarray.Dataset directly.
    bucket : str
        Name of the bucket in the object store. Bucket names can contain only
        lowercase letters, numbers, dots (.), and hyphens (-).
    object_prefix : str
        Prefix of the Icechunk repository in the bucket.
    store_credentials_json : str
        Path to the JSON file containing the object store credentials.
    group : str | None, default None
        Group in Icechunk repository to update.
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
        with the chunks of the existing repository.
    attrs : dict[str, Any] | None, default None
        Global attributes to add to the dataset.
    branch : str | None, default None
        Branch on which to commit data. If None, 'main' is used.
    commit_message : str | None, default None
        Commit message prefix recorded in the Icechunk repository.
        If None, 'Updated data in Icechunk repository' is used.
    dask_config_kwargs : dict[str, Any] | None, default None
        Dask configuration settings passed to ``dask.config.set()``.
        Only used when ``dask_cluster_kwargs`` is provided.
    dask_cluster_kwargs : dict[str, Any] | None, default None
        Keyword arguments passed to ``dask.distributed.LocalCluster()``.
        If None, dask is not used to parallelise the workflow.
    icechunk_config : dict[str, dict[str, Any]] | None, default None
        Icechunk configuration containing the keys ``storage_config_kwargs``,
        ``repository_config_kwargs`` and ``storage_settings_kwargs``.
        If None, ``DEFAULT_ICECHUNK_CONFIG`` is used.

    Raises
    ------
    FileNotFoundError
        If a glob pattern matches no files or the store does not exist.
    DimensionSizeError
        If a non-append dimension differs in size from the repository.
    DimensionNotFound
        If a non-append dimension is missing from the repository.
    AppendDimensionError
        If the source data starts before the repository along ``append_dim``.
    AppendDimensionSizeError
        If overlapping source values are not all found in the repository.
    ChunkSizeError
        If ``rechunk`` differs from the repository chunks.
    """
    # === Default Arguments === #
    if append_dim is None:
        append_dim = "time_counter"
    if branch is None:
        branch = "main"
    if commit_message is None:
        commit_message = "Updated data in Icechunk repository"

    update_kwargs = {
        "file": file,
        "bucket": bucket,
        "object_prefix": object_prefix,
        "store_credentials_json": store_credentials_json,
        "group": group,
        "variables": variables,
        "append_dim": append_dim,
        "grid_filepath": grid_filepath,
        "update_coords": update_coords,
        "rechunk": rechunk,
        "attrs": attrs,
        "branch": branch,
        "commit_message": commit_message,
        "icechunk_config": icechunk_config,
    }

    if dask_cluster_kwargs is not None:
        # === Update Icechunk repo with Dask === #
        if dask_config_kwargs is not None:
            dask.config.set(dask_config_kwargs)
            logger.info("Updated dask configuration settings.")

        with LocalCluster(**dask_cluster_kwargs) as cluster, Client(cluster) as client:
            logger.info(
                "Created LocalCluster with %s workers @ Client: %s",
                dask_cluster_kwargs["n_workers"],
                client.dashboard_link,
            )
            # Catch UserWarnings when rechunking data:
            client.register_plugin(CaptureWarningsPlugin())

            _update_icechunk(**update_kwargs, parallel=True)

        logger.info("Dask Cluster has been shutdown.")

    else:
        # === Update Icechunk repo without Dask === #
        _update_icechunk(**update_kwargs, parallel=False)
