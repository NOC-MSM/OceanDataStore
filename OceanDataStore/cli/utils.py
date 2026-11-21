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
utils.py

Description:
This module defines utility functions and classes for the OceanDataStore CLI.

Authors:
    - Ollie Tooth
"""

from __future__ import annotations

import glob
import logging
import time
from types import TracebackType
from typing import TYPE_CHECKING, Any, Literal

import s3fs
import xarray as xr
from distributed.diagnostics.plugin import WorkerPlugin

from OceanDataStore.cli.object_store import ObjectStoreS3

if TYPE_CHECKING:
    from dask.distributed import Worker

logger = logging.getLogger(__name__)


# -- Define Dask WorkerPlugins -- #
class CaptureWarningsPlugin(WorkerPlugin):
    """Dask WorkerPlugin redirecting worker warnings (e.g., rechunking UserWarnings) to logging."""

    def setup(self, worker: Worker) -> None:
        """Enable capture of warnings by the logging system on the worker."""
        logging.captureWarnings(True)

    def teardown(self, worker: Worker) -> None:
        """Disable capture of warnings by the logging system on the worker."""
        logging.captureWarnings(False)


class CloseClientSessionPlugin(WorkerPlugin):
    """Dask WorkerPlugin closing cached s3fs client sessions on worker teardown."""

    async def teardown(self, worker: Worker) -> None:
        """Close the aiobotocore sessions of all cached s3fs filesystems & clear the cache."""
        for fs in list(s3fs.S3FileSystem._cache.values()):
            try:
                if getattr(fs, "_s3", None) is not None:
                    await fs._s3.close()
            except Exception:
                # Best-effort cleanup: failing to close a session must not fail teardown.
                logger.debug("Failed to close s3fs client session.", exc_info=True)
        s3fs.S3FileSystem.clear_instance_cache()


# -- Utility Classes & Functions -- #
class Timer:
    """
    Context manager logging the time taken to write data to an object store.

    Parameters
    ----------
    action : {'send', 'replace', 'append'}
        Action performed on the store.
    dest : str
        Destination path of the store in the object store.
    var : str | None, default None
        Name of the variable written to the store. If None, the
        whole dataset is assumed to be written.

    Raises
    ------
    ValueError
        If ``action`` is not one of 'send', 'replace' or 'append'.
    """

    def __init__(self, action: Literal["send", "replace", "append"], dest: str, var: str | None = None) -> None:
        if action == "send":
            self.action = f"Sent {var} to" if var is not None else "Sent dataset to"
        elif action == "replace":
            self.action = f"Updated {var} in" if var is not None else "Updated"
        elif action == "append":
            self.action = f"Appended {var} to" if var is not None else "Appended to"
        else:
            raise ValueError("Invalid action: must be 'send', 'replace' or 'append'.")
        self.dest = dest

    def __enter__(self) -> Timer:
        """Start the timer."""
        self.t_start = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Stop the timer and log the elapsed time (seconds)."""
        self.t_end = time.perf_counter()
        logger.info(
            "Completed: %s store s3://%s in %.2f seconds",
            self.action,
            self.dest.replace("s3://", ""),
            self.t_end - self.t_start,
        )


def _preprocess_dataset(
    file: list[str] | str | xr.Dataset,
    rechunk: dict[str, int] | None = None,
    append_dim: str | None = None,
    update_coords: dict[str, str] | None = None,
    grid_filepath: str | None = None,
    attrs: dict[str, Any] | None = None,
    parallel: bool = False,
) -> xr.Dataset:
    """
    Preprocess the dataset to be sent to the object store.

    Parameters
    ----------
    file : list[str] | str | xarray.Dataset
        Glob pattern, filepath or list of filepaths to netCDF file(s).
        Users can also pass a single xarray.Dataset directly.
    rechunk : dict[str, int] | None, default None
        Mapping of dimension names to dask chunk sizes. If None, dask
        chunks will be set to on-disk chunks.
    append_dim : str | None, default None
        Name of the dimension along which to concatenate multi-file
        datasets. If None, 'time_counter' is used.
    update_coords : dict[str, str] | None, default None
        Mapping of coordinate variables to update using the model
        grid file. Keys are coordinate variable names in the
        dataset to be sent, and values are the corresponding
        variable names in the model grid file. If None, no
        coordinates will be updated.
    grid_filepath : str | None, default None
        Filepath to the model grid file used to update coordinate
        variables. Required if ``update_coords`` is not None.
    attrs : dict[str, Any] | None, default None
        Global attributes to add to the dataset. If None, no
        attributes will be added.
    parallel : bool, default False
        Whether to open and preprocess the files in parallel
        using ``dask.delayed``.

    Returns
    -------
    xarray.Dataset
        Preprocessed (multi-file) dataset with optionally
        updated coordinates, chunk sizes and attributes.

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

    # === Verify Inputs === #
    if not isinstance(file, (list, str, xr.Dataset)):
        raise TypeError("filepaths must be a list, a string or an xarray Dataset.")
    if isinstance(file, list):
        for fpath in file:
            if not isinstance(fpath, str):
                raise TypeError("filepaths must be a list of strings.")
            if not fpath.endswith(".nc"):
                raise ValueError("Invalid file extension: only .nc files are supported.")
    elif isinstance(file, str) and not file.endswith(".nc"):
        raise ValueError("Invalid file extension: only .nc files are supported.")
    if (rechunk is not None) and (not isinstance(rechunk, dict)):
        raise TypeError("rechunk must be a dictionary.")
    if not isinstance(append_dim, str):
        raise TypeError("append_dim must be a string.")
    if (update_coords is not None) and (not isinstance(update_coords, dict)):
        raise TypeError("update_coords must be a dictionary.")
    if (grid_filepath is not None) and (not isinstance(grid_filepath, str)):
        raise TypeError("grid_filepath must be a string.")
    if (attrs is not None) and (not isinstance(attrs, dict)):
        raise TypeError("attrs must be a dictionary.")
    if not isinstance(parallel, bool):
        raise TypeError("parallel must be a boolean.")

    # === Load netCDF dataset === #
    if rechunk is None:
        # Default to dask chunks equal to on-disk chunks:
        rechunk = {}

    # File names from str / glob pattern:
    if isinstance(file, str):
        if "*" in file:
            filepaths = sorted(glob.glob(file))
            if len(filepaths) == 0:
                raise FileNotFoundError(f"No files found at {filepaths}")
        else:
            filepaths = [file]
    # File names from list:
    elif isinstance(file, list):
        filepaths = file

    if isinstance(file, xr.Dataset):
        # Use input dataset:
        ds_filepath = file
        if rechunk is not None:
            ds_filepath = ds_filepath.chunk(rechunk)
    elif len(filepaths) > 1:
        # Open multi-file dataset:
        ds_filepath = xr.open_mfdataset(
            filepaths,
            engine="h5netcdf",
            chunks=rechunk,
            parallel=parallel,
            concat_dim=append_dim,
            combine="nested",
            data_vars="minimal",
            coords="minimal",
            compat="override",
        )
    else:
        # Open single file dataset:
        ds_filepath = xr.open_dataset(filepaths[0], chunks=rechunk)

    # === Update coordinates using model grid file === #
    if update_coords is not None:
        if grid_filepath is None:
            raise ValueError("grid_filepath must be specified to update coordinate variables.")
        ds_grid = xr.open_dataset(grid_filepath)
        # Update coordinate variables using model grid file:
        for key, grid_var in update_coords.items():
            coord_data = ds_grid[grid_var].squeeze(drop=True)
            # Rechunk dimensions to user specified chunks:
            if rechunk is not None:
                coord_chunks = {dim: rechunk[dim] for dim in coord_data.dims}
                ds_filepath = ds_filepath.assign_coords({key: coord_data.chunk(coord_chunks)})
            else:
                ds_filepath = ds_filepath.assign_coords({key: coord_data})
        logger.info("Completed: Updated coordinate variables.")

    # === Update Attributes === #
    if attrs is not None:
        ds_filepath = ds_filepath.assign_attrs(attrs)

    return ds_filepath


# -- Command Line Interface Utility Functions -- #
def list_objects(dest: str, store_credentials_json: str) -> list[str]:
    """
    List the objects contained inside a bucket / object prefix.

    The listing is also written to the log.

    Parameters
    ----------
    dest : str
        Destination path in the object store (``bucket`` or ``bucket/prefix``).
    store_credentials_json : str
        Path to the JSON file containing the object store credentials.

    Returns
    -------
    list[str]
        Paths of the objects contained inside the bucket / object prefix.
    """
    # === Initialise synchronous object store === #
    logger.info("Reading object store credentials from %s", store_credentials_json)
    obj_store = ObjectStoreS3(anon=False, asynchronous=False, store_credentials_json=store_credentials_json)

    objects = obj_store.ls(dest)
    logger.info(objects)

    return objects
