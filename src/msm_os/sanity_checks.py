"""Module with sanity checks."""

from typing import List, Any
import logging

import numpy as np
import xarray as xr
import dask
from fsspec.mapping import FSMap

from .exceptions import (
    DuplicatedAppendDimValue,
    VariableNotFound,
    ExpectedAttrsNotFound,
    DimensionMismatch,
    CheckSumMismatch,
)


def check_duplicates(
    ds_filepath: xr.Dataset,
    ds_obj_store: xr.Dataset,
    append_dim: str,
) -> xr.Dataset:
    """
    Check if there are duplicates in the append dimension.

    Parameters
    ----------
    ds_filepath
        Local dataset to be sent.
    ds_obj_store
        Dataset in the object store.
    append_dim
        The name of the dimension to check for duplicates.

    Raises
    ------
    DuplicatedAppendDimValue
        If duplicates are found in the append dimension.
    
    Returns
    -------
    xr.Dataset
    """
    filepath_append_dim = ds_filepath[append_dim]

    # Number of duplicates in the append dimension
    n_dupl = np.sum(np.isin(ds_obj_store[append_dim], filepath_append_dim))

    if n_dupl == 0:
        return ds_filepath
    if n_dupl == filepath_append_dim.size:
        raise DuplicatedAppendDimValue(
            n_dupl,
            append_dim,
            filepath_append_dim.values[0],
            filepath_append_dim.values[-1],
        )
    if n_dupl < filepath_append_dim.size:
        ds_filepath = ds_filepath.sel({append_dim: ~np.isin(filepath_append_dim, ds_obj_store[append_dim])})
    else:
        raise NotImplementedError(
            "Found error in check_duplicates which is not implemented."
        )
    return ds_filepath


def check_variable_exists(
    ds: xr.Dataset,
    var: str,
) -> None:
    """
    Check if the variable exists in the dataset.

    Parameters
    ----------
    ds
        Dataset to be checked.
    var : str
        The name of the variable to check.

    Raises
    ------
    VariableNotFound
        If the variable is not found in the dataset.
    """
    if var not in ds:
        raise VariableNotFound(var)


def check_destination_exists(
    obj_store: FSMap,
    dest: str,
) -> None:
    """
    Check if the destination exists in the object store.

    Parameters
    ----------
    obj_store
        Object store to be checked.
    dest
        The name of the destination to check.

    Raises
    ------
    FileNotFoundError
        If the destination is not found in the object store.
    """
    if not obj_store.exists(dest):
        raise FileNotFoundError(f"Destination '{dest}' doesn't exist in object store.")



def data_integrity_evaluation(var: str,
                              append_dim: str,
                              mapper: Any,
                              ds_filepath: xr.Dataset,
                              dest: str,
                              reproject: bool,
                              first_file: bool = False) -> None:
    """ Evaluate the data integrity of the dataset.

    Args:
        obj_store (ObjectStoreS3): object store instance.
        bucket (str): bucket name.
        object_prefix (str): prefix of the object.
        var (str): variable name.
        append_dim (str): name of the append dimension.
        mapper (Any): object store mapper.
        ds_filepath (xr.Dataset): dataset to be evaluated.
        dest (str): destination of the dataset.
        reproject (bool): whether to reproject the dataset.
        first_file (bool, optional): Whether this is the first file being sent.
            Defaults to False.
    """
    # Check data integrity
    try:
        check_data_integrity(mapper,
                             var,
                             append_dim,
                             ds_filepath,
                             reproject,
                             first_file=first_file)
        logging.info("Data integrity check passed for %s", dest)
    except (ExpectedAttrsNotFound, DimensionMismatch, CheckSumMismatch) as error:
        if isinstance(error, ExpectedAttrsNotFound):
            error_msg = "missing expected attributes in the metadata"
        elif isinstance(error, DimensionMismatch):
            error_msg = "dimension mismatch"
        elif isinstance(error, CheckSumMismatch):
            error_msg = "checksum mismatch"

        if append_dim not in list(ds_filepath[var].sizes):
            logging.warning(
                "Error found while trying to update file %s: %s. Error: %s",
                dest,
                error_msg,
                error,
            )
        else:
            logging.warning(
                "Error found while trying to update file %s with time value of %s: %s. Error: %s",
                dest,
                ds_filepath[var].time_counter.values[0],
                error_msg,
                error,
            )

        logging.warning(
            "Object store object %s will be rolled back to previous version", dest
        )
        raise error

def check_data_integrity(
    mapper: FSMap,
    var: str,
    append_dim: str,
    ds: xr.Dataset,
    reproject: bool = False,
    first_file: bool = False,
    test_list: List[str] = None,
) -> None:
    """

    Update/replace the object store with new data.

    Parameters
    ----------
    mapper
        The object store interface.
    var
        The variable to check.
    append_dim
        The name of the dimension to check for duplicates.
    test_list
        List of tests to perform. Default is ["metadata", "checksum"].
    """
    if test_list is None:
        test_list = ["metadata", "checksum"]

    ds_obj_store = xr.open_zarr(mapper)
    check_variable_exists(ds_obj_store, var)

    for test in test_list:
        if test == "metadata":
            validate_dimensions(ds_obj_store)
            validate_variables(ds_obj_store)
        if test == "checksum":
            validate_checksum(ds_obj_store, var, append_dim, ds, reproject, first_file)


def calculate_metadata(
    ds_obj_store: xr.Dataset,
    ds_filepath: xr.Dataset,
    var: str,
    append_dim: str,
    reproject: bool,
    first_file: bool = False,
) -> xr.Dataset:
    """
    Calculate metadata for the dataset.

    Parameters
    ----------
    ds_obj_store : xr.Dataset
        The dataset to which the variable will be appended.
    ds_filepath : xr.Dataset
        The dataset that will be appended.
    var : str
        The name of the variable being appended.
    append_dim : str
        The name of the dimension along which the variable is being appended.
    first_file : bool
        Whether this is the first file being sent.
    Returns
    -------
    xr.Dataset
        The dataset with the calculated metadata.
    """

    # Calculate expected size for the dimension
    expected_size = _calculate_expected_dimension_size(
        ds_obj_store, ds_filepath, append_dim
    )
    if not expected_size:
        expected_size = ["none"]
    ds_filepath.attrs["expected_size"] = expected_size

    # Calculate expected variables and coords for the dataset
    expected_variables = list(set(list(ds_obj_store.keys()) + list(ds_filepath.keys())))
    expected_coords = list(set(list(ds_obj_store.coords) + list(ds_filepath.coords)))
    if not expected_variables:
        expected_variables = ["none"]
    if not expected_coords:
        expected_coords = ["none"]
    ds_filepath.attrs["expected_variables"] = expected_variables
    ds_filepath.attrs["expected_coords"] = expected_coords

    # Calculate checksum for the variable
    expected_checksum = _calculate_expected_checksum(ds_filepath, var, append_dim, reproject, first_file)

    ds_filepath.attrs["expected_checksum"] = expected_checksum

    return ds_filepath

def _calculate_expected_checksum(ds_filepath: xr.Dataset,
                                 var: str,
                                 append_dim: str,
                                 reproject: bool,
                                 first_file: bool) -> int:
    """ Calculate the expected checksum for the variable.

    Args:
        ds_filepath (xr.Dataset): The dataset to be checked.
        var (str): The variable to check.
        append_dim (str): The name of the dimension along which the variable is being appended.
        reproject (bool): Whether to reproject the dataset.
        first_file (bool): Whether this is the first file being sent.

    Returns:
        int: The expected checksum for the variable.
    """
    expected_checksum = 0
    if append_dim not in ds_filepath[var].sizes:
        if first_file:
            expected_checksum += _calculate_checksum(expected_checksum,
                                                                    ds_filepath,
                                                                    var,
                                                                    reproject)
    else:
        append_dim_values = ds_filepath[append_dim].values
        for append_dim_value in append_dim_values:
            expected_checksum += _calculate_checksum(expected_checksum,
                                                     ds_filepath.sel({append_dim: append_dim_value}),
                                                     var,
                                                     reproject)

    return expected_checksum

def _calculate_checksum(expected_checksum: int,
                                       part_of_ds_dataset: xr.Dataset,
                                       var: str,
                                       reproject: bool) -> int:
    """ Calculate checksum

    Args:
        expected_checksum (int): Expected checksum
        part_of_ds_dataset (xr.Dataset): The dataset to be checked.
        var (str): The variable to check.
        reproject (bool): Whether to reproject the dataset.

    Returns:
        int: The expected checksum for the variable.
    """
    def calculate_result(var_part_of_ds_dataset):
        dtype = var_part_of_ds_dataset.data.dtype
        if np.issubdtype(dtype, np.number):
            if isinstance(var_part_of_ds_dataset.data, dask.array.core.Array):
                data_array = var_part_of_ds_dataset.data.astype(np.uint32)
            else:
                values = var_part_of_ds_dataset.values
                values = np.nan_to_num(values, nan=0, posinf=0, neginf=0).astype(np.uint32)
                data_array = dask.array.from_array(values, chunks='auto')
            checksum = data_array.sum().compute()
        else:
            checksum = 0
        return checksum
    expected_checksum += calculate_result(part_of_ds_dataset[var])

    # data_bytes = part_of_ds_dataset[var].values
    # checksum = np.frombuffer(data_bytes, dtype=np.uint32).sum()
    # expected_checksum += checksum
    if "y" in list(part_of_ds_dataset.sizes):
        if reproject:
            expected_checksum += calculate_result(part_of_ds_dataset[f"projected_{var}"])
            # data_bytes_reprojected = part_of_ds_dataset[f"projected_{var}"].values.tobytes()
            # expected_checksum += np.frombuffer(
            #     data_bytes_reprojected, dtype=np.uint32
            # ).sum()
    return expected_checksum

    # else:
    #     for time in ds_filepath[var].time_counter.values:
    #         data_bytes = ds_filepath[var].isel(time_counter=time).values.tobytes()
    #         expected_checksum += np.frombuffer(data_bytes, dtype=np.uint32).sum()
    #         if "y" in list(ds_filepath.sizes):
    #             if reproject:
    #                 data_bytes_reprojected = ds_filepath[f"projected_{var}"].isel(time_counter=time).values.tobytes()
    #                 expected_checksum += np.frombuffer(
    #                     data_bytes_reprojected, dtype=np.uint32
    #                 ).sum()

    # data_bytes = ds_filepath[var].values.tobytes()
    # expected_checksum = np.frombuffer(data_bytes, dtype=np.uint32).sum()
    # if "y" in list(ds_filepath.sizes):
    #     if reproject:
    #         data_bytes_reprojected = ds_filepath[f"projected_{var}"].values.tobytes()
    #         expected_checksum += np.frombuffer(
    #             data_bytes_reprojected, dtype=np.uint32
    #         ).sum()
    # return expected_checksum

def _calculate_expected_dimension_size(
    ds_obj_store: xr.Dataset, ds_filepath: xr.Dataset, append_dim: str
) -> int:
    """
    Calculate the expected size for the specified dimension based on the current
    dataset and variable.

    Parameters
    ----------
    ds_obj_store : xr.Dataset
        The dataset to which the variable will be appended.
    ds_filepath : xr.Dataset
        The dataset that will be appended.
    append_dim : str
        The name of the dimension along which the variable is being appended.

    Returns
    -------
    int
        The expected size for the specified dimension.
    """
    expected_size = {}
    for dim, _ in ds_filepath.sizes.items():
        logging.info("Dim: %s", dim)
        if dim == append_dim:
            if not ds_obj_store.sizes.get(dim):
                current_size = 0
            else:
                current_size = len(ds_obj_store[dim])
            append_size = len(ds_filepath[dim])
            expected_size[dim] = current_size + append_size
        else:
            expected_size[dim] = len(ds_filepath[dim])

    return expected_size


def validate_dimensions(ds_obj_store: xr.Dataset):
    """
    Validates the dimensions of the dataset, ensuring they match expectations based on metadata.

    Parameters
    ----------
    ds_obj_store : xr.Dataset
        The dataset loaded from the object store.
    """
    expected_size = ds_obj_store.attrs.get("expected_size", None)
    if expected_size is None:
        raise ExpectedAttrsNotFound("expected_size")

    for dim, size in ds_obj_store.sizes.items():
        # Compare the expected size with the actual size
        if size != expected_size[dim]:
            raise DimensionMismatch(dim, size, expected_size)


def validate_variables(ds_obj_store: xr.Dataset):
    """
    Audit variables of the dataset.

    Parameters
    ----------
    ds_obj_store : xr.Dataset
        Dataset loaded from the Zarr store.

    """
    expected_variables = ds_obj_store.attrs.get("expected_variables", None)

    if expected_variables is None:
        raise ExpectedAttrsNotFound("expected_variables")

    for var in expected_variables:
        if var not in ds_obj_store.variables:
            raise VariableNotFound(var)


def validate_coords(ds_obj_store: xr.Dataset):
    """
    Audit coords of the dataset.

    Parameters
    ----------
    ds_obj_store : xr.Dataset
        Dataset loaded from the Zarr store.

    """
    expected_coords = ds_obj_store.attrs.get("expected_coords", None)

    if expected_coords is None:
        raise ExpectedAttrsNotFound("expected_coords")

    for var in expected_coords:
        if var not in ds_obj_store.coords:
            raise VariableNotFound(var)


def validate_checksum(
    ds_obj_store: xr.Dataset,
    var: str,
    append_dim: str,
    ds: xr.Dataset,
    reproject: bool = False,
    first_file: bool = False
):
    """
    Validate the checksum of the dataset.

    Parameters
    ----------
    ds_obj_store : xr.Dataset
        Dataset loaded from the Zarr store.
    var
        The variable to check.
    append_dim
        The name of the dimension to check for duplicates.
    ds
        The dataset to be checked.
    reproject
        Whether to reproject the dataset.
    first_file
        Whether this is the first file being sent.
    """

    #     if append_dim in list(ds_filepath[var].sizes):
    #     ds_filepath.attrs[
    #         f'expected_checksum_{ds_filepath[var].time_counter.values[0]}'] = expected_checksum
    # else:
    #     ds_filepath.attrs[
    #         f'expected_checksum_{var}'] = expected_checksum

    expected_checksum = None
    if append_dim not in list(ds[var].sizes):
        if first_file:
            specific_chunk = ds_obj_store
            expected_checksum = ds_obj_store.attrs.get("expected_checksum", None)
        else:
            logging.info("The variable is not chunked along the append dimension.")
            logging.info("Skipping checksum validation.")
            return
    else:
        try:
            specific_chunk = ds_obj_store.sel({append_dim: ds[append_dim].values})
        except KeyError:
            specific_chunk = None
        if specific_chunk is not None:
            expected_checksum = specific_chunk.attrs.get(
                "expected_checksum", None
            )
    actual_checksum = 0
    if expected_checksum is not None:
        if append_dim not in list(specific_chunk[var].sizes):
            actual_checksum += _calculate_checksum(actual_checksum,
                                                   specific_chunk,
                                                   var,
                                                   reproject)
        else:
            append_dim_values = specific_chunk[append_dim].values
            for append_dim_value in append_dim_values:
                actual_checksum += _calculate_checksum(actual_checksum,
                                                       specific_chunk.sel({append_dim: append_dim_value}),
                                                       var,
                                                       reproject)

        logging.info(
            "Expected checksum: %s, Actual checksum: %s",
            expected_checksum,
            actual_checksum,
        )
        if actual_checksum != expected_checksum:
            raise CheckSumMismatch(
                append_dim,
                expected_checksum,
                actual_checksum,
            )
    else:
        raise CheckSumMismatch(
            append_dim, expected_checksum, actual_checksum
        )
