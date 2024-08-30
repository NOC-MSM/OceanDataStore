"""Module with sanity checks."""

from typing import List
import numpy as np
import xarray as xr
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
) -> None:
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
    """
    filepath_append_dim = ds_filepath[append_dim]

    # Number of duplicates in the append dimension
    n_dupl = np.sum(np.isin(ds_obj_store[append_dim], filepath_append_dim))

    if n_dupl == 0:
        return n_dupl
    elif n_dupl == filepath_append_dim.size:
        raise DuplicatedAppendDimValue(
            n_dupl,
            append_dim,
            filepath_append_dim.values[0],
            filepath_append_dim.values[-1],
        )
    elif n_dupl > 0:
        raise ValueError(
            f"Only found {n_dupl} duplicates in the append dimension when "
            f"there are {filepath_append_dim.size} values in the dataset."
        )
    else:
        raise NotImplementedError(
            "Found error in check_duplicates which is not implemented."
        )


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


def check_data_integrity(
    mapper: FSMap,
    var: str,
    append_dim: str,
    ds: xr.Dataset,
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
            validate_checksum(ds_obj_store, var, append_dim, ds)


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
    ds_obj_store: xr.Dataset, var: str, append_dim: str, ds: xr.Dataset
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
    """

    #     if append_dim in list(ds_filepath[var].sizes):
    #     ds_filepath.attrs[
    #         f'expected_checksum_{ds_filepath[var].time_counter.values[0]}'] = expected_checksum
    # else:
    #     ds_filepath.attrs[
    #         f'expected_checksum_{var}'] = expected_checksum

    expected_checksum = None
    if append_dim not in list(ds[var].sizes):
        specific_chunk = ds_obj_store
        expected_checksum = ds_obj_store.attrs.get("expected_checksum", None)
    else:
        try:
            specific_chunk = ds_obj_store.sel({append_dim: ds[append_dim].values})
        except KeyError:
            specific_chunk = None
        if specific_chunk is not None:
            expected_checksum = specific_chunk.attrs.get(
                "expected_checksum", None
            )

    if expected_checksum:
        data_bytes = specific_chunk[var].values.tobytes()
        actual_checksum = np.frombuffer(data_bytes, dtype=np.uint32).sum()
        if f"projected_{var}" in specific_chunk:
            data_bytes_reprojected = specific_chunk[f"projected_{var}"].values.tobytes()
            actual_checksum += np.frombuffer(data_bytes_reprojected, dtype=np.uint32).sum()

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
