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
# -- Import Python Modules -- #
import time
import logging
from typing import Optional

import glob
import xarray as xr

from dask.distributed.diagnostics.plugin import WorkerPlugin

# -- Import OceanDataStore Modules -- #
from OceanDataStore.cli.object_store import ObjectStoreS3


# -- Define Dask WorkerPlugins -- #
class CaptureWarningsPlugin(WorkerPlugin):
    def setup(self, worker):
        # Used to catch UserWarnings when rechunking:
        logging.captureWarnings(True)
    def teardown(self, worker):
        logging.captureWarnings(False)


class CloseClientSessionPlugin(WorkerPlugin):
    async def teardown(self, worker):
        import s3fs
        for fs in list(s3fs.S3FileSystem._cache.values()):
            try:
                if hasattr(fs, '_s3') and fs._s3 is not None:
                    await fs._s3.close()
            except Exception:
                pass
        s3fs.S3FileSystem.clear_instance_cache()


# -- Utility Classes & Functions -- #
class timer():
    """
    Timer context manager class to return time
    taken to write variables & datasets to an
    object store.

    Parameters
    ----------
    action : str
        Action to be performed. Options are 'send' or 'update'.
    url : str
        URL path in the object store.
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
            f"Completed: {self.action} store s3://{self.dest.replace('s3://', '')} in {(self.t_end - self.t_start):.2f} seconds"
            )


def _preprocess_dataset(file: list[str] | str | xr.Dataset,
                        rechunk: Optional[dict] = None,
                        append_dim: Optional[str] = "time_counter",
                        update_coords: Optional[dict] = None,
                        grid_filepath: Optional[str] = None,
                        attrs: Optional[dict] = None,
                        parallel: bool = False,
                        ) -> xr.Dataset:
    """
    Preprocess the dataset to be sent to the object store.

    Parameters
    ----------
    file: list | str | xarray.Dataset
        Regular expression or list of filepaths to netCDF file(s).
        Users can also pass a single xarray.Dataset directly.
    rechunk: Optional[dict], default=None
        Mapping to rechunk dimensions. If None, dask chunks
        will be set to on-disk chunks.
    append_dim: str, default='time_counter'
        Name of the dimension to append multi-file datasets.
    update_coords: Optional[dict], default=None
        Mapping of coordinate variables to update using model
        grid file. Keys are coordinate variable names in the
        dataset to be sent, and values are the corresponding
        variable names in the model grid file. If None, no 
        coordinates will be updated.
    grid_filepath: Optional[str], default=None
        Filepath to the model grid file to update coordinate
        variables. Required if update_coords is not None.
    attrs: Optional[dict], default=None
        Dictionary of attributes to add to the dataset.
        If None, no attributes will be added.
    parallel: bool, default=False
        Whether to open and preprocess the dataset in parallel
        using `dask.delayed`.

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


# -- Command Line Interface Utility Functions -- #
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
