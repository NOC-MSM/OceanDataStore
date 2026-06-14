"""
utils.py

Description: Utility functions for processing gridded ocean data.

Contact: Ollie Tooth (oliver.tooth@noc.ac.uk)
"""
# == Import Python packages == #
import json

import icechunk
import numpy as np
import xarray as xr
import zarr


# == Utility Functions == #
def compute_gc_distance(
        lat1: xr.DataArray,
        lon1: xr.DataArray,
        lat2: xr.DataArray,
        lon2: xr.DataArray
) -> xr.DataArray:
    """
    Calculate the Great-Circle distance between two sets of
    geographical points on the Earth's surface.

    Parameters:
    -----------
    lat1 : xr.DataArray
        Latitude of the first set of points (degrees).
    lon1 : xr.DataArray
        Longitude of the first set of points (degrees).
    lat2 : xr.DataArray
        Latitude of the second set of points (degrees).
    lon2 : xr.DataArray
        Longitude of the second set of points (degrees).
    
    Returns:
    --------
    dist : xr.DataArray
        Great-circle distance between the two sets
        of points (meters).
    
    """
    # Define the radius of the Earth in meters:
    re = 6371000

    # Convert latitudes and longitudes from degrees to radians:
    lon1, lat1, lon2, lat2 = map(np.deg2rad, [lon1, lat1, lon2, lat2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Calculate the great-circle distance between points:
    dist = (2*re*np.arcsin(np.sqrt(
            np.sin(dlat/2)**2 +
            (np.cos(lat1) *
            np.cos(lat2) *
            np.sin(dlon/2)**2)
            )))

    return dist


def compute_dx(
        ds: xr.Dataset,
        ) -> xr.DataArray:
    """
    Calculate zonal length of each grid cell in meters.
    
    The length is calculated using the latitude and longitude coordinates
    of the input dataset assuming a uniform regular grid.

    Parameters:
    -----------
    ds : xr.Dataset
        Input dataset containing 'latitude' and 'longitude' coordinates.

    Returns:
    --------
    xr.DataArray
        DataArray representing the zonal length of each grid cell.
    """
    # -- Validate Input -- #
    if not isinstance(ds, xr.Dataset):
        raise TypeError("Input must be an xarray Dataset.")
    if 'latitude' not in ds.coords or 'longitude' not in ds.coords:
        raise ValueError("Input dataset must contain 'latitude' and 'longitude' coordinates.")

    # -- Calculate Grid Cell Length -- #
    # Infer horizontal resolution for uniform grid:
    dlon = ds['longitude'].diff(dim="longitude").mean().values

    if (ds['longitude'].ndim == 1) and (ds['latitude'].ndim == 1):
        # Define 2-dimensional longitude and latitude arrays for grid cell centers:
        lon = np.repeat(ds['longitude'].values[np.newaxis, :], len(ds['latitude']), axis=0)
        lat = np.repeat(ds['latitude'].values[:, np.newaxis], len(ds['longitude']), axis=1)
    else:
        # Use existing 2-dimensional longitude and latitude arrays:
        lon = ds['longitude'].values
        lat = ds['latitude'].values

    # Calculate zonal and meridional grid cell dimensions:
    dx = compute_gc_distance(lon1=lon - dlon / 2, lat1=lat, lon2=lon + dlon / 2, lat2=lat)

    # Define dx DataArray with CF-compliant metadata:
    dx = xr.DataArray(
        data=dx,
        dims=('latitude', 'longitude'),
        coords={'latitude': ds['latitude'], 'longitude': ds['longitude']},
        name='dx',
        attrs={
            'long_name': 'Grid-Cell Zonal Length',
            'standard_name': 'cell_x_length',
            'units': 'm',
        },
    )

    return dx


def compute_dy(
        ds: xr.Dataset,
        ) -> xr.DataArray:
    """
    Calculate meridional length of each grid cell in meters.
    
    The length is calculated using the latitude and longitude coordinates
    of the input dataset assuming a uniform regular grid.

    Parameters:
    -----------
    ds : xr.Dataset
        Input dataset containing 'latitude' and 'longitude' coordinates.

    Returns:
    --------
    xr.DataArray
        DataArray representing the meridional length of each grid cell.
    """
    # -- Validate Input -- #
    if not isinstance(ds, xr.Dataset):
        raise TypeError("Input must be an xarray Dataset.")
    if 'latitude' not in ds.coords or 'longitude' not in ds.coords:
        raise ValueError("Input dataset must contain 'latitude' and 'longitude' coordinates.")

    # -- Calculate Grid Cell Length -- #
    # Infer horizontal resolution for uniform grid:
    dlat = ds['latitude'].diff(dim="latitude").mean().values

    if (ds['longitude'].ndim == 1) and (ds['latitude'].ndim == 1):
        # Define 2-dimensional longitude and latitude arrays for grid cell centers:
        lon = np.repeat(ds['longitude'].values[np.newaxis, :], len(ds['latitude']), axis=0)
        lat = np.repeat(ds['latitude'].values[:, np.newaxis], len(ds['longitude']), axis=1)
    else:
        # Use existing 2-dimensional longitude and latitude arrays:
        lon = ds['longitude'].values
        lat = ds['latitude'].values

    # Calculate zonal and meridional grid cell dimensions:
    dy = compute_gc_distance(lon1=lon, lat1=lat - dlat / 2, lon2=lon, lat2=lat + dlat / 2)

    # Define dy DataArray with CF-compliant metadata:
    dy = xr.DataArray(
        data=dy,
        dims=('latitude', 'longitude'),
        coords={'latitude': ds['latitude'], 'longitude': ds['longitude']},
        name='dy',
        attrs={
            'long_name': 'Grid-Cell Meridional Length',
            'standard_name': 'cell_y_length',
            'units': 'm',
        },
    )

    return dy


def compute_cell_area(
        ds: xr.Dataset,
        ) -> xr.DataArray:
    """
    Calculate horizontal area of each grid cell in square meters.
    
    The area is calculated using the latitude and longitude coordinates
    of the input dataset assuming a uniform regular grid.

    Parameters:
    -----------
    ds : xr.Dataset
        Input dataset containing 'latitude' and 'longitude' coordinates.

    Returns:
    --------
    xr.DataArray
        DataArray representing the horizontal area of each grid cell.
    """
    # -- Validate Input -- #
    if not isinstance(ds, xr.Dataset):
        raise TypeError("Input must be an xarray Dataset.")
    if 'latitude' not in ds.coords or 'longitude' not in ds.coords:
        raise ValueError("Input dataset must contain 'latitude' and 'longitude' coordinates.")

    # -- Calculate Grid Cell Area -- #
    # Infer horizontal resolution for uniform grid:
    dlon = ds['longitude'].diff(dim="longitude").mean().values
    dlat = ds['latitude'].diff(dim="latitude").mean().values

    if (ds['longitude'].ndim == 1) and (ds['latitude'].ndim == 1):
        # Define 2-dimensional longitude and latitude arrays for grid cell centers:
        lon = np.repeat(ds['longitude'].values[np.newaxis, :], len(ds['latitude']), axis=0)
        lat = np.repeat(ds['latitude'].values[:, np.newaxis], len(ds['longitude']), axis=1)
    else:
        # Use existing 2-dimensional longitude and latitude arrays:
        lon = ds['longitude'].values
        lat = ds['latitude'].values

    # Calculate zonal and meridional grid cell dimensions:
    dx = compute_gc_distance(lon1=lon - dlon / 2, lat1=lat, lon2=lon + dlon / 2, lat2=lat)
    dy = compute_gc_distance(lon1=lon, lat1=lat - dlat / 2, lon2=lon, lat2=lat + dlat / 2)

    # Define cell_area DataArray with CF-compliant metadata:
    cell_area = xr.DataArray(
        data=dx*dy,
        dims=('latitude', 'longitude'),
        coords={'latitude': ds['latitude'], 'longitude': ds['longitude']},
        name='cell_area',
        attrs={
            'long_name': 'Grid-Cell Area',
            'standard_name': 'cell_area',
            'units': 'm2',
        },
    )

    return cell_area


def compute_cell_thickness(
        ds: xr.Dataset,
    ) -> xr.DataArray:
    """
    Calculate vertical thickness of each grid cell in meters.

    Cell thickness is calculated using the depth coordinates of the input dataset assuming a regular grid in the vertical dimension.

    Parameters:
    -----------
    ds : xr.Dataset
        Input dataset containing 'depth' coordinates.

    Returns:
    --------
    xr.DataArray
        Vertical thickness of each grid cell.
    """
    # -- Validate Input -- #
    if not isinstance(ds, xr.Dataset):
        raise TypeError("Input must be an xarray Dataset.")
    if 'depth' not in ds.coords:
        raise ValueError("Input dataset must contain 'depth' coordinates.")
    depth = ds['depth'].data

    # Check that depth is 1-dimensional:
    if depth.ndim != 1:
        raise ValueError("Input depth DataArray must be 1-dimensional.")

    # Find interfaces between vertical levels:
    interfaces = 0.5 * (depth[:-1] + depth[1:])
    # Use sea surface as top boundary:
    top = 0.0
    # Extrapolate bottom boundary:
    bottom = depth[-1] + (depth[-1] - interfaces[-1])
    edges = np.concatenate([[top], interfaces, [bottom]])

    # Define cell_thickness DataArray with CF-compliant metadata:
    cell_thickness = xr.DataArray(
        data=np.diff(edges),
        dims=('depth',),
        coords={'depth': depth},
        name='cell_thickness',
        attrs={
            'long_name': 'Grid-Cell Thickness',
            'standard_name': 'cell_thickness',
            'units': 'm',
        },
    )

    return cell_thickness

def compute_land_sea_mask(
        da: xr.DataArray,
        ) -> xr.DataArray:
    """
    Calculate land-sea mask from a variable DataArray.
    
    The resulting mask is defined as follows:
    * 1 -> ocean grid point
    * 0 -> land grid point

    Parameters:
    -----------
    da : xr.DataArray
        Input variable DataArray containing NaN values on land points.

    Returns:
    --------
    xr.DataArray
        Land-sea mask.
    """
    # -- Validate Input -- #
    if not isinstance(da, xr.DataArray):
        raise TypeError("Input must be an xarray DataArray.")
    if da.ndim != 2:
        raise ValueError("Input DataArray must be 2-dimensional.")
    
    # -- Calculate Land-Sea Mask -- #
    # Define land-sea mask:
    mask = xr.where(np.isnan(da), 0, 1)

    # Add CF-compliant metadata to the mask:
    mask.attrs['long_name'] = "Land-Sea Binary Mask"
    mask.attrs['standard_name'] = "sea_binary_mask"
    mask.attrs['comment'] = " 1 = sea, 0 = land"

    return mask


def update_icechunk_global_attrs(
        credentials_filepath: str,
        bucket: str,
        prefix: str,
        attrs: dict,
        commit_message: str,
        branch: str='main',
        region: str='us-east-1',
        force_path_style: bool=True,
) -> str:
    """
    Update global attributes of existing Icechunk store via a new
    commit.

    Expects Icechunk S3 storage at a custom endpoint (e.g., JASMIN OS).

    Parameters:
    -----------
    credentials_filepath : str
        Filepath to JSON file containing Icechunk S3 storage credentials.
    bucket : str
        Name of the S3 bucket where the Icechunk store is located.
    prefix : str
        Prefix (path) within the S3 bucket where the Icechunk store is located.
    attrs : dict
        Dictionary of global attributes to update in the root group of the Icechunk store.
    commit_message : str
        Commit message describing the update to the Icechunk store.
    branch : str, optional
        Branch of the Icechunk repository to update (default: 'main').
    region : str, optional
        AWS region where the S3 bucket is located (default: 'us-east-1').
    force_path_style : bool, optional
        Whether to force path-style access for S3 (default: True).

    Returns:
    --------
    str
        Snapshot ID of new commit.
    """
    # -- Validate Input -- #
    if not isinstance(credentials_filepath, str):
        raise TypeError("credentials_filepath must be a string.")
    if not isinstance(bucket, str):
        raise TypeError("bucket must be a string.")
    if not isinstance(prefix, str):
        raise TypeError("prefix must be a string.")
    if not isinstance(attrs, dict):
        raise TypeError("attributes must be a dictionary.")
    if not isinstance(commit_message, str):
        raise TypeError("commit_message must be a string.")
    if not isinstance(branch, str):
        raise TypeError("branch must be a string.")
    if not isinstance(region, str):
        raise TypeError("region must be a string.")
    if not isinstance(force_path_style, bool):
        raise TypeError("force_path_style must be a boolean.")

    # -- Update Icechunk Global Attributes -- #
    # Load Icechunk S3 storage credentials from JSON file:
    store_credentials = json.load(open(credentials_filepath, 'r'))

    # Define Icechunk storage:
    storage = icechunk.s3_storage(
    bucket=bucket,
    prefix=prefix,
    region=region,
    access_key_id=store_credentials['token'],
    secret_access_key=store_credentials['secret'],
    endpoint_url=store_credentials['endpoint_url'],
    force_path_style=force_path_style,
    )

    # Open Icechunk repository & start read-only session on main branch:
    repo = icechunk.Repository.open(storage=storage)
    print(f"Opened Icechunk repository at s3://{bucket}/{prefix} on branch '{branch}'")

    # Open a writable session on root group:
    session = repo.writable_session(branch=branch)
    root = zarr.open_group(session.store)
    # Update global attributes & commit changes to repo:
    root.attrs.update(attrs)
    print(f"Updated global attributes via new commit on branch '{branch}' with commit message -> '{commit_message}'")
    
    return session.commit(message=commit_message)


def update_icechunk_variable_attrs(
        credentials_filepath: str,
        bucket: str,
        prefix: str,
        vars: list[str],
        attrs: list[dict],
        commit_message: str,
        branch: str='main',
        region: str='us-east-1',
        force_path_style: bool=True,
) -> str:
    """
    Update variable attributes of existing Icechunk store via a new
    commit.

    Expects Icechunk S3 storage at a custom endpoint (e.g., JASMIN OS).

    Parameters:
    -----------
    credentials_filepath : str
        Filepath to JSON file containing Icechunk S3 storage credentials.
    bucket : str
        Name of the S3 bucket where the Icechunk store is located.
    prefix : str
        Prefix (path) within the S3 bucket where the Icechunk store is located.
    vars : list[str]
        List of variable names whose attributes are to be updated.
    attrs : list[dict]
        List of dictionaries containing attributes to update for each variable.
    commit_message : str
        Commit message describing the update to the Icechunk store.
    branch : str, optional
        Branch of the Icechunk repository to update (default: 'main').
    region : str, optional
        AWS region where the S3 bucket is located (default: 'us-east-1').
    force_path_style : bool, optional
        Whether to force path-style access for S3 (default: True).

    Returns:
    --------
    str
        Snapshot ID of new commit.
    """
    # -- Validate Input -- #
    if not isinstance(credentials_filepath, str):
        raise TypeError("credentials_filepath must be a string.")
    if not isinstance(bucket, str):
        raise TypeError("bucket must be a string.")
    if not isinstance(prefix, str):
        raise TypeError("prefix must be a string.")
    if not isinstance(vars, list):
        raise TypeError("vars must be a list.")
    if not isinstance(attrs, list):
        raise TypeError("attributes must be a list.")
    if not isinstance(commit_message, str):
        raise TypeError("commit_message must be a string.")
    if not isinstance(branch, str):
        raise TypeError("branch must be a string.")
    if not isinstance(region, str):
        raise TypeError("region must be a string.")
    if not isinstance(force_path_style, bool):
        raise TypeError("force_path_style must be a boolean.")

    # -- Update Icechunk Global Attributes -- #
    # Load Icechunk S3 storage credentials from JSON file:
    store_credentials = json.load(open(credentials_filepath, 'r'))

    # Define Icechunk storage:
    storage = icechunk.s3_storage(
    bucket=bucket,
    prefix=prefix,
    region=region,
    access_key_id=store_credentials['token'],
    secret_access_key=store_credentials['secret'],
    endpoint_url=store_credentials['endpoint_url'],
    force_path_style=force_path_style,
    )

    # Open Icechunk repository & start read-only session on main branch:
    repo = icechunk.Repository.open(storage=storage)
    print(f"Opened Icechunk repository at s3://{bucket}/{prefix} on branch '{branch}'")

    # Open a writable session on root group:
    session = repo.writable_session(branch=branch)
    root = zarr.open_group(session.store)
    # Update variable attributes & commit changes to repo:
    for var, attr in zip(vars, attrs):
        root[var].attrs.update(attr)

    print(f"Updated variable attributes via new commit on branch '{branch}' with commit message -> '{commit_message}'")
    
    return session.commit(message=commit_message)
