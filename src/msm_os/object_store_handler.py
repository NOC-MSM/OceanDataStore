"""Module for handling the object store."""

import logging
import os
from typing import Any, List, Optional

import numpy as np
import xarray as xr
import iris
import cartopy.crs as ccrs
import cf_units
import zarr
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from .exceptions import (
    DuplicatedAppendDimValue,
    ExpectedAttrsNotFound,
    DimensionMismatch,
    CheckSumMismatch,
)
from .object_store import ObjectStoreS3
from .sanity_checks import (
    calculate_metadata,
    check_destination_exists,
    check_duplicates,
    check_variable_exists,
    data_integrity_evaluation,
)

try:
    from dask.distributed import Client
    from dask.distributed import KilledWorker
except ImportError:
    logging.warning(
        "Dask is not installed. Please install it to use parallel features."
    )

retry_strategy = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10),
    retry=retry_if_exception_type(
        (ExpectedAttrsNotFound, DimensionMismatch, CheckSumMismatch, KilledWorker)
    ),
    reraise=True,
)

def update(
    filepaths: List[str],
    bucket: str,
    store_credentials_json: str,
    variables: Optional[List[str]] = None,
    append_dim: str = "time_counter",
    object_prefix: Optional[str] = None,
    to_zarr_kwargs: Optional[dict] = None,
) -> None:
    """
    Update/replace the object store with new data.

    Parameters
    ----------
    filepaths
        List of filepaths to the datasets to be updated.
    bucket
        Name of the bucket in the object store.
    store_credentials_json
        Path to the JSON file containing the object store credentials.
    variables
        List of variables to be updated. If None, all variables will be updated, by default None.
    append_dim
        Name of the append dimension, by default "time_counter".
    object_prefix :
        Prefix to be added to the object names in the object store, by default None.
    to_zarr_kwargs
        Additional keyword arguments passed to xr.Dataset.to_zarr(), by default None.
    """
    to_zarr_kwargs = to_zarr_kwargs or {}

    obj_store = ObjectStoreS3(anon=False, store_credentials_json=store_credentials_json)
    check_destination_exists(obj_store, bucket)

    for filepath in filepaths:
        logging.info("Updating using %s", filepath)
        object_prefix = _get_object_prefix(filepath, object_prefix)

        ds_filepath = xr.open_dataset(filepath)
        variables = _get_update_variables(ds_filepath, variables)

        for var in variables:
            dest = f"{bucket}/{object_prefix}/{var}.zarr"

            check_variable_exists(ds_filepath, var)
            check_destination_exists(obj_store, dest)

            mapper = obj_store.get_mapper(dest)
            ds_obj_store = xr.open_zarr(mapper)
            check_variable_exists(ds_obj_store, var)

            _update_data(ds_filepath, ds_obj_store, var, append_dim, mapper)

def send(
    filepaths: List[str],
    bucket: str,
    store_credentials_json: str,
    variables: Optional[List[str]] = None,
    send_vars_indep: bool = True,
    append_dim: str = "time_counter",
    object_prefix: Optional[str] = None,
    client: Optional[Client] = None,#
    rechunk: dict = None,
    reproject: bool = False,
    skip_integrity_check: bool = False,
    to_zarr_kwargs: Optional[dict] = None,
) -> None:
    """
    Send data to the object store.

    Parameters
    ----------
    filepaths
        List of filepaths to the datasets to be sent.
    bucket
        Name of the bucket in the object store. Bucket names can consist only of
        lowercase letters, numbers, dots (.), and hyphens (-).
    store_credentials_json
        Path to the JSON file containing the object store credentials.
    variables
        List of variables to send. If None, all variables will be sent, by default None.
    send_vars_indep
        Whether to send variables as separate objects, by default True.
    append_dim
        Name of the append dimension, by default "time_counter".
    object_prefix
        Prefix to be added to the object names in the object store, by default None.
    client
        Dask client, by default None.
    rechunk
        Rechunk strategy dictionary, by default None.
    reproject
        Whether to reproject the dataset, by default False.
    skip_integrity_check
        Whether to skip the data integrity check, by default False.
    to_zarr_kwargs
        Additional keyword arguments passed to xr.Dataset.to_zarr(), by default None.
    """
    to_zarr_kwargs = to_zarr_kwargs or {}

    obj_store = ObjectStoreS3(anon=False, store_credentials_json=store_credentials_json)

    if not obj_store.exists(bucket):
        logging.info("Bucket '%s' doesn't exist. Creating...", bucket)

    for filepath in filepaths:
        logging.info("Sending %s", filepath)
        ds_filepath = xr.open_dataset(filepath)

        prefix = _get_object_prefix(filepath, object_prefix)

        _send_data_to_store(
            obj_store,
            bucket,
            ds_filepath,
            prefix,
            variables,
            append_dim,
            send_vars_indep,
            client,
            rechunk,
            reproject,
            skip_integrity_check,
            to_zarr_kwargs,
        )


def _get_object_prefix(filepath: str, object_prefix: Optional[str]) -> str:
    """
    Get the object prefix from the filepath.

    Note
    ----
    Change this function if required.

    Parameters
    ----------
    filepath
        Filepath to the dataset.
    object_prefix
        Prefix to be added to the object names in the object store.

    Returns
    -------
    str
        The object prefix.
    """
    if not object_prefix:
        str_components = os.path.basename(filepath).split("_")

        if str_components[2] == "grid":
            object_prefix = str_components[3] + str_components[1]
        else:
            object_prefix = str_components[2] + str_components[1]

    return object_prefix


def _get_update_variables(ds_filepath: xr.Dataset, variables: List[str]) -> List[str]:
    """
    Get the variables to update.

    Parameters
    ----------
    ds_filepath
        Filepath to the dataset.
    variables
        List of variables to update. If None, all variables will be updated, by default None.

    Returns
    -------
    List[str]
        The list of variables to update.
    """
    variables = variables or [
        var for var in ds_filepath.variables if var not in ds_filepath.coords
    ]
    return variables


def _update_data(
    ds_filepath: xr.Dataset,
    ds_obj_store: xr.Dataset,
    var: str,
    append_dim: str,
    mapper: Any,
) -> None:
    """
    Update the data in the object store.

    Parameters
    ----------
    ds_filepath
        Filepath to the local dataset.
    ds_obj_store
        Dataset in the object store.
    var
        Variable to be updated.
    append_dim
        Name of the append dimension.
    mapper
        Object store mapper.
    """

    try:
        ds_filepath = check_duplicates(ds_filepath, ds_obj_store, append_dim)
    except DuplicatedAppendDimValue:
        logging.info("Updating %s", mapper.root)
        # Define region to write to
        dupl = np.where(np.isin(ds_obj_store[append_dim], ds_filepath[append_dim]))
        dupl_max = np.max(dupl) + 1
        dupl_min = np.min(dupl)
        region = {append_dim: slice(dupl_min, dupl_max, None)}

        # Write to zarr
        vars_to_drop = [
            var
            for var in ds_filepath.variables
            if not any(size in region for size in ds_filepath[var].sizes)
        ]

        ds_filepath = ds_filepath.drop_vars(vars_to_drop)
        ds_filepath[var].to_zarr(mapper, mode="r+", region=region)
        logging.info("Updated %s", mapper.root)

        return

    logging.info("Skipping %s because region not found in object store", mapper.root)


@retry_strategy
def _send_variable(
    ds_filepath: xr.Dataset,
    obj_store: ObjectStoreS3,
    var: str,
    bucket: str,
    object_prefix: str,
    append_dim: str,
    rechunk: dict,
    reproject: bool = False,
    skip_integrity_check: bool = True,
) -> None:
    """
    Send a single variable to the object store.

    Parameters
    ----------
    ds_filepath
        Filepath to the local dataset.
    obj_store
        Object store.
    var
        Variable to be sent.
    bucket
        Name of the bucket in the object store. Bucket names can consist only of
        lowercase letters, numbers, dots (.), and hyphens (-).
    object_prefix
        Prefix to be added to the object names in the object store.
    append_dim
        Name of the append dimension.
    rechunk
        Whether to rechunk the dataset.
    reproject
        Whether to reproject the dataset.
    skip_integrity_check
        Whether to skip the data integrity check.
    """
    check_variable_exists(ds_filepath, var)
    ds_filepath_var = ds_filepath[[var]]

    dest = f"{bucket}/{object_prefix}/{var}.zarr"
    mapper = obj_store.get_mapper(dest)

    try:
        check_destination_exists(obj_store, dest)

        if append_dim not in ds_filepath_var.dims:
            logging.info(
                "Skipping %s because %s is not in the dimensions of %s",
                dest,
                append_dim,
                var,
            )
            return

        logging.info("Appending to %s along the %s dimension", dest, append_dim)

        try:
            ds_obj_store = xr.open_zarr(mapper)
            ds_filepath_var = check_duplicates(ds_filepath_var, ds_obj_store, append_dim)
            if reproject:
                # Reproject the dataset to the expected projection
                ds_filepath_var = _reproject_ds(ds_filepath_var, var)

            # Calculate expected size, variables, chunks and checksum
            ds_filepath_var = calculate_metadata(
                ds_obj_store, ds_filepath_var, var, append_dim, reproject
            )

            # Rechunk the dataset
            if rechunk:
                actual_data_chunksize = {dim: chunk[0] for dim, chunk in zip(ds_obj_store[var].dims,
                                                                             ds_obj_store[var].chunks) if chunk}
                new_chunking = {
                    dim: size
                    for dim, size in rechunk.items()
                    if dim in ds_filepath[var].dims
                }

                chunks_differ = any(
                    dim in actual_data_chunksize and actual_data_chunksize[dim] != new_chunking[dim]
                    for dim in new_chunking
                )

                if chunks_differ:
                    logging.warning("The actual data on the object store has chunk size: %s", actual_data_chunksize)
                    logging.warning("And you are trying to rechunk it to: %s", new_chunking)
                    logging.warning("You can't rechunk the data on the object store")
                # ds_filepath_var = _rechunk_ds(ds_filepath_var, rechunk)

            # Append the variable to the object store
            ds_filepath_var.to_zarr(
                mapper, mode="a", append_dim=append_dim
            )
            first_file = False

        except DuplicatedAppendDimValue:
            logging.info(
                "Skipping %s due to duplicate values in the append dimension", dest
            )
            return
        except KeyError:
            logging.info(
                "Skipping %s due to no %s on data dimensions", dest, append_dim
            )
            return
    except FileNotFoundError:
        logging.info("Creating %s", dest)
        first_file = True

        if reproject:
            # Reproject the dataset to the expected projection
            ds_filepath_var = _reproject_ds(ds_filepath_var, var)

        ds_filepath_var = calculate_metadata(
            xr.Dataset(), ds_filepath_var, var, append_dim, reproject, first_file
        )
        if rechunk:
            ds_filepath_var = _rechunk_ds(ds_filepath_var, rechunk)

        ds_filepath_var.to_zarr(mapper, mode="a")

    if not skip_integrity_check:
        try:
            data_integrity_evaluation(var,
                                    append_dim,
                                    mapper,
                                    ds_filepath_var,
                                    dest,
                                    reproject,
                                    first_file)
        except (ExpectedAttrsNotFound, DimensionMismatch, CheckSumMismatch):
            if first_file:
                logging.warning("No previous version found. The object will be deleted.")
                obj_store.delete(dest)
            else:
                rollback_object(obj_store,
                                ds_filepath[append_dim].values,
                                bucket,
                                object_prefix,
                                var,
                                append_dim)
    else:
        logging.warning("As requested, skipping data integrity check for %s", dest)


def _rechunk_ds(ds_filepath: xr.Dataset, rechunk: dict) -> xr.Dataset:
    """ Rechunk the dataset.

    Args:
        ds_filepath (xr.Dataset): The dataset to be rechunked.

    Returns:
        xr.Dataset: The rechunked dataset.
    """
    # Apply custom chunking if the dimensions are present
    # chunking = {"x": 100, "y": 100, "time_counter": 1}
    variables = ds_filepath.variables
    for variable in variables:
        new_chunking = {
            dim: size
            for dim, size in rechunk.items()
            if dim in ds_filepath[variable].dims
        }
        if len(new_chunking.keys()) > 0:
            ds_filepath[variable] = ds_filepath[
                variable
            ].chunk(new_chunking)
            
    return ds_filepath

def _reproject_ds(ds_filepath: xr.Dataset, var: str) -> xr.Dataset:
    """
    Reproject the dataset to the expected projection.

    Parameters
    ----------
    ds_filepath : xr.Dataset
        The dataset to be reprojected.
    var : str
        The name of the variable to be reprojected.

    Returns
    -------
    xr.Dataset
        The reprojected dataset.
    """
    da_filepath = ds_filepath[var]

    list_dim = list(da_filepath.sizes)
    # logging.info("List dim: %s", list_dim)
    if "y" not in list_dim:
        combined_ds = xr.Dataset({var: da_filepath})
        return combined_ds

    index_of_y = list_dim.index("y")
    index_of_x = list_dim.index("x")

    standard_name = da_filepath.attrs.get("standard_name", None)
    if standard_name:
        da_filepath.attrs["standard_name"] = None
    units = da_filepath.attrs.get("units", None)
    if units:
        da_filepath.attrs["units"] = None

    cube = da_filepath.to_iris()
    for coord in cube.aux_coords:
        if coord.standard_name == "latitude":
            cube.remove_coord("latitude")
            latitude = iris.coords.AuxCoord(
                da_filepath["nav_lat"].values, standard_name="latitude", units="degrees"
            )
            cube.add_aux_coord(latitude, (index_of_y, index_of_x))

        if coord.standard_name == "longitude":
            cube.remove_coord("longitude")
            longitude = iris.coords.AuxCoord(
                da_filepath["nav_lon"].values,
                standard_name="longitude",
                units="degrees",
            )
            cube.add_aux_coord(longitude, (index_of_y, index_of_x))

    if units:
        try:
            cube.units = cf_units.Unit(units)
            logging.info("Setting units to: %s", units)
        except:
            logging.info("Warning: No units found. Setting units to 'None'")
            cube.units = cf_units.Unit(None)
    if standard_name:
        try:
            cube.standard_name = standard_name
            logging.info("Setting standard_name to correct value: %s", standard_name)
        except ValueError:
            logging.info(
                "Warning: Standard Name is not valid. Set long name instead to %s",
                standard_name,
            )
            cube.long_name = standard_name

    target_projection = ccrs.PlateCarree()
    # try:
    projected_cube = iris.analysis.cartography.project(
        cube,
        target_projection,
        nx=da_filepath.shape[index_of_x],
        ny=da_filepath.shape[index_of_y],
    )
    # except ValueError as e:
    #     print("Error during projection:", e)
    #     return
    data_da = xr.DataArray.from_iris(projected_cube[0])
    data_da = data_da.sortby("projection_x_coordinate")
    data_da = data_da.sortby("projection_y_coordinate", ascending=False)
    data_da = data_da.rename(
        {"projection_y_coordinate": "y", "projection_x_coordinate": "x"}
    )
    # data_da = data_da.where(data_da != 0.0, np.nan)
    # combined_ds = da_filepath.copy()
    combined_ds = xr.Dataset({var: da_filepath})
    combined_ds[f"projected_{var}"] = (data_da.dims, data_da.values)
    combined_ds = combined_ds.assign_coords(
        {"projected_x": (data_da.x.dims, data_da.x.values)}
    )
    combined_ds = combined_ds.assign_coords(
        {"projected_y": (data_da.y.dims, data_da.y.values)}
    )
    # combined_ds = combined_ds.fillna(0)

    return combined_ds

def rollback_object(
    obj_store: ObjectStoreS3,
    append_dim_values: np.ndarray,
    bucket: str,
    object_prefix: str,
    var: str,
    append_dim: str
) -> None:
    """
    Rolls back the Zarr object stored in the object store by removing the
    last appended dimension.

    Parameters
    ----------
    obj_store
        Object store instance.
    ds_filepath
        Dataset to be rolled back.
    bucket
        Name of the bucket.
    object_prefix
        Prefix of the object.
    var
        Variable name.
    append_dim
        Name of the append dimension.
    """
    dest = f"{bucket}/{object_prefix}/{var}.zarr"
    mapper = obj_store.get_mapper(dest)
    zarr_group = zarr.open(mapper, mode="a")
    for group in zarr_group:
        zarr_array = zarr_group[group]
        original_shape = zarr_array.shape
        if append_dim in zarr_array.attrs["_ARRAY_DIMENSIONS"]:
            append_dim_index = zarr_array.attrs["_ARRAY_DIMENSIONS"].index(append_dim)
            new_shape = list(original_shape)
            new_shape[append_dim_index] -= len(append_dim_values)
            zarr_array.attrs["_ARRAY_DIMENSIONS"] = zarr_array.attrs[
                "_ARRAY_DIMENSIONS"
            ]
            zarr_array.resize(tuple(new_shape))
    zarr.consolidate_metadata(mapper)
    zarr_group.store.close()

    logging.info("Object store object %s rolled back successfully.", dest)


def _send_data_to_store(
    obj_store: ObjectStoreS3,
    bucket: str,
    ds_filepath: xr.Dataset,
    object_prefix: str,
    variables: List[str],
    append_dim: str,
    send_vars_indep: bool,
    client: Client,
    rechunk: dict,
    reproject: bool,
    skip_integrity_check: bool,
    to_zarr_kwargs: dict,
) -> None:
    """
    Send data to the object store.

    Parameters
    ----------
    obj_store
        Object store to be used.
    bucket
        Name of the bucket in the object store. Bucket names can consist only of
        lowercase letters, numbers, dots (.), and hyphens (-).
    ds_filepath
        Dataset to be sent.
    object_prefix
        Prefix to be added to the object names in the object store.
    variables
        List of variables to send. If None, all variables will be sent.
    append_dim
        Name of the append dimension.
    send_vars_indep
        Whether to send variables as separate objects.
    client
        Dask client.
    rechunk
        Rechunk strategy dictionary.
    reproject
        Whether to reproject the dataset.
    skip_integrity_check
        Whether to skip the data integrity check.
    to_zarr_kwargs
        Additional keyword arguments passed to xr.Dataset.to_zarr(), by default None.
    """
    # See https://stackoverflow.com/questions/66769922/concurrently-write-xarray-datasets-to-zarr-how-to-efficiently-scale-with-dask
    if send_vars_indep:
        variables = _get_update_variables(ds_filepath, variables)
        if client:
            futures = []
            for var in variables:
                futures.append(
                    client.submit(
                        _send_variable,
                        ds_filepath,
                        obj_store,
                        var,
                        bucket,
                        object_prefix,
                        append_dim,
                        rechunk,
                        reproject,
                        skip_integrity_check
                    )
                )
            client.gather(futures)
        else:
            for var in variables:
                _send_variable(
                    ds_filepath,
                    obj_store,
                    var,
                    bucket,
                    object_prefix,
                    append_dim,
                    rechunk,
                    reproject,
                    skip_integrity_check
                )

    else:
        dest = f"{bucket}/{object_prefix}.zarr"
        mapper = obj_store.get_mapper(dest)

        try:
            check_destination_exists(obj_store, dest)
            logging.info("Appending to %s along the %s dimension", dest, append_dim)

            try:
                ds_obj_store = xr.open_zarr(mapper)
                ds_filepath = check_duplicates(ds_filepath, ds_obj_store, append_dim)
                ds_filepath.to_zarr(mapper, mode="a", append_dim=append_dim)
            except DuplicatedAppendDimValue:
                logging.info(
                    "Skipping %s due to duplicate values in the append dimension", dest
                )
            except KeyError:
                logging.info(
                    "Skipping %s due to no %s on data dimensions", dest, append_dim
                )

        except FileNotFoundError:
            logging.info("Creating %s", dest)
            ds_filepath.to_zarr(mapper, mode="w")


def get_files(
    bucket: str,
    store_credentials_json: str,
) -> List[str]:
    """
    Get the list of files in the bucket.

    Parameters
    ----------
    bucket
        Bucket name.
    store_credentials_json
        Path to the JSON file containing the credentials for the Object Store.#

    Returns
    -------
    List[str]
        List of files in the bucket.
    """
    obj_store = ObjectStoreS3(anon=False, store_credentials_json=store_credentials_json)
    logging.info("Getting list of files in bucket '%s'", bucket)
    for file in obj_store.ls(f"{bucket}"):
        logging.info(file)
    return obj_store.ls(f"{bucket}")
