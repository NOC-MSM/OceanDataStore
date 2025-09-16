"""
utils.py

Description:
Utility functions to create the National Oceanography Centre
(NOC) Spatio-Temporal Access Catalog and write to JSON files.

Authors:
    - Ollie Tooth
"""
# -- Import Python Modules -- #
import sys
import pystac
import logging
import datetime
import icechunk
import xarray as xr
from shapely.geometry import Polygon, mapping


# -- Logging Functions -- #
def create_logging_banner(logger: logging.Logger) -> None:
    """Add OceanDataStore banner to logger."""
    logger.info(r"""
         .~~~.
       .(     ).~~~~~~.
     ~(               ).~~~.
   .(    OceanDataStore     ).  
  (___________________________).

      STAC Catalog Creator
    """,
    extra={"simple": True},
    )


def initialise_logging(logger: logging.Logger) -> None:
    """Initialise logging configuration."""
    logging.basicConfig(
        stream=sys.stdout,
        format="🌐   OceanDataStore  🌐   | %(levelname)10s | %(asctime)s | %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# -- I/O Functions -- #
def open_icechunk_store(
    bucket: str,
    prefix: str,
    branch: str = "main",
    endpoint_url: str = "https://noc-msm-o.s3-ext.jc.rl.ac.uk",
    ) -> xr.Dataset:
    """
    Open an Icechunk Store as an xarray.Dataset.

    Parameters
    ----------
    bucket : str
        S3 bucket name where the Icechunk repository is stored.
    prefix : str
        Prefix for the Icechunk repository in the S3 bucket.
    branch : str, optional
        Branch of the Icechunk repository to open (default is "main").
    endpoint_url : str, optional
        The S3 endpoint URL (default is "https://noc-msm-o.s3-ext.jc.rl.ac.uk").
    """
    # Define S3 storage:
    storage = icechunk.s3_storage(
    bucket=bucket,
    prefix=prefix,
    anonymous=True,
    endpoint_url=endpoint_url,
    force_path_style=True,
    )

    # Open Icechunk Repository:
    repo = icechunk.Repository.open(storage=storage)

    # Open Dataset from Icechunk Store:
    return xr.open_zarr(repo.readonly_session(branch=branch).store, consolidated=False)


# -- STAC Functions -- #
def create_item_with_icechunk_asset(
    ds: xr.Dataset,
    bucket: str,
    platform: str,
    prefix: str,
    start_date: str = "1976-01-01",
    end_date: str = "2024-12-31",
    bbox: tuple = (-180.0, -90.0, 180.0, 90.0),
    collection: str = "noc-npd-era5",
    config: str = "eORCA1 ERA5v1 NPD",
    operation: str ="annual-mean",
    endpoint_url: str = "https://noc-msm-o.s3-ext.jc.rl.ac.uk",
    ) -> pystac.Item:
    """
    Create a STAC Item from an Icechunk Store asset.

    Parameters
    ----------
    ds : xr.Dataset
        The xarray Dataset containing the data to be included in the STAC Item.
    bucket : str
        The S3 bucket name where the data is stored.
    platform : str
        The platform name (e.g., "gn_global", "gr_global", etc.).
    prefix : str
        The prefix for the data in the S3 bucket (e.g., "U1y", "U1m", etc.).
    start_date : str, optional
        The start date of the dataset in "YYYY-MM-DD" format (default is "1976-01-01").
    end_date : str, optional
        The end date of the dataset in "YYYY-MM-DD" format (default is "2024-12-31").
    bbox : tuple, optional
        Bounding box for the dataset in the format (min_lon, min_lat, max_lon, max_lat).
        (default is global coverage).
    collection : str, optional
        The name of the STAC Collection to which this Item belongs (default is "noc-npd-era5").
    config : str, optional
        The configuration string for the dataset (default is "eORCA1 ERA5v1 NPD").
    operation : str, optional
        The operation string indicating the type of operation performed on the dataset (default is "annual-mean").
    endpoint_url : str, optional
        The S3 endpoint URL (default is "https://noc-msm-o.s3-ext.jc.rl.ac.uk").

    Returns
    -------
    pystac.Item
        A STAC Item containing the dataset information and an asset pointing to the data.
    """
    # Define the item description based on the prefix:
    if 'domain' in prefix:
        description = f"Icechunk repository containing {config} global ocean model {prefix.split('/')[-1]} variables."
    elif 'I' in prefix:
        description = f"Icechunk repository containing {config} global sea-ice {operation} outputs defined at T-points."
    elif 'S' in prefix:
        description = f"Icechunk repository containing {config} global ocean scalar {operation} outputs."
    elif 'M' in prefix:
        description = f"Icechunk repository containing {config} ocean physics transect {operation} outputs defined at {prefix.split('/')[-1]}."
    else:
        description = f"Icechunk repository containing {config} global ocean physics {operation} outputs defined at {prefix[0]}-points."

    # Define Polygon geometry for the item:
    polygon = Polygon([
        (bbox[0], bbox[1]),   # SW corner
        (bbox[2], bbox[1]),   # SE corner
        (bbox[2], bbox[3]),   # NE corner
        (bbox[0], bbox[3]),   # NW corner
        (bbox[0], bbox[1])    # Closing the polygon back to SW corner
    ])

    # Convert the Polygon to GeoJSON format:
    geometry = mapping(polygon)

    # Create a STAC Item with Asset:
    item = pystac.Item(
        id=f"{collection}/{bucket}/{platform}/{prefix}",
        geometry=geometry,
        bbox=list(polygon.bounds),  # [min_lon, min_lat, max_lon, max_lat]
        datetime=None,
        start_datetime=datetime.datetime(year=int(start_date.split("-")[0]), month=int(start_date.split("-")[1]), day=int(start_date.split("-")[2])),
        end_datetime=datetime.datetime(year=int(end_date.split("-")[0]), month=int(end_date.split("-")[1]), day=int(end_date.split("-")[2])),
        properties={
            "title": f"{config} {prefix} Icechunk repository",
            "description": description,
            "platform": platform,
            "variables": list(ds.data_vars),
            "variable_standard_names": [ds[var].attrs.get('standard_name', var) for var in ds.data_vars],
            "dimensions": list(ds.dims),
            "operation": operation.split(" ")[1],
            "operation_frequency": operation.split(" ")[0],
            "ocean_component": "NEMO v4.2.2",
            "si_component": "SI3 v4.0",
            "status": "ongoing",
            "update_frequency": "quarterly",
            "latest_data_update": datetime.datetime.now().isoformat(),
        },
        collection=collection,
    )

    item.add_asset(key=prefix.split('/')[-1], asset=pystac.Asset(
        href=f"https://noc-msm-o.s3-ext.jc.rl.ac.uk/{bucket}/{prefix}",
        title=f"{config} {prefix} Icechunk repository",
        description=description,
        media_type="application/icechunk",
        extra_fields=dict(
            bucket=bucket,
            prefix=prefix,
            endpoint_url=endpoint_url,
            anonymous=True
        )
    ))

    return item


def create_item_with_zarr_asset(
    ds: xr.Dataset,
    bucket: str,
    platform: str,
    prefix: str,
    start_date: str = "1976-01-01",
    end_date: str = "2024-02-01",
    bbox: tuple = (-180.0, -90.0, 180.0, 90.0),
    collection : str = "noc-npd-jra55",
    config: str = "eORCA1 JRA55v1 NPD",
    operation: str ="annual-mean",
    variable_stores: bool = True,
    endpoint_url: str = "https://noc-msm-o.s3-ext.jc.rl.ac.uk",
    zarr_format: int = 2,
    ) -> pystac.Item:
    """
    Create a STAC Item from a Zarr Store asset.

    Parameters
    ----------
    ds : xr.Dataset
        The xarray Dataset containing the data to be included in the STAC Item.
    bucket : str
        The S3 bucket name where the data is stored.
    platform : str
        The platform name (e.g., "gn_global", "gr_global", etc.).
    prefix : str
        The prefix for the data in the S3 bucket (e.g., "U1y", "U1m", etc.).
    start_date : str, optional
        The start date of the dataset in "YYYY-MM-DD" format (default is "1976-01-01").
    end_date : str, optional
        The end date of the dataset in "YYYY-MM-DD" format (default is "2024-12-31").
    bbox : tuple, optional
        Bounding box for the dataset in the format (min_lon, min_lat, max_lon, max_lat).
        (default is global coverage).
    collection : str, optional
        The name of the STAC Collection to which this Item belongs (default is "noc-npd-jra55").
    config : str, optional
        The configuration string for the dataset (default is "eORCA1 JRA55v1 NPD").
    operation : str, optional
        The operation string indicating the type of operation performed on the dataset (default is "annual-mean").
    variable_stores : bool, optional
        Whether each variable is stored in a separate Zarr store (default is True).
    endpoint_url : str, optional
        The S3 endpoint URL (default is "https://noc-msm-o.s3-ext.jc.rl.ac.uk").
    zarr_format: int, optional
        The Zarr format version (default is 2).

    Returns
    -------
    pystac.Item
        A STAC Item containing the dataset information and an asset pointing to the data.
    """
    # Define the item description based on the prefix:
    var = f"{prefix.split('/')[-1]} output" if variable_stores else "outputs"

    if 'domain' in prefix:
        description = f"Zarr store containing {config} global ocean model {prefix.split('/')[-1]} variables."
    elif 'I' in prefix:
        description = f"Zarr store containing {config} global sea-ice {operation} {var} defined at T-points."
    elif 'S' in prefix:
        description = f"Zarr store containing {config} global ocean scalar {operation} {var}."
    elif 'M' in prefix:
        description = f"Zarr store containing {config} ocean physics transect {operation} {var} defined at {prefix.split('/')[-1]}."
    else:
        description = f"Zarr store containing {config} global ocean physics {operation} {var} defined at {prefix[0]}-points."

    # Define Polygon geometry for the item:
    polygon = Polygon([
        (bbox[0], bbox[1]),   # SW corner
        (bbox[2], bbox[1]),   # SE corner
        (bbox[2], bbox[3]),   # NE corner
        (bbox[0], bbox[3]),   # NW corner
        (bbox[0], bbox[1])    # Closing the polygon back to SW corner
    ])

    # Convert the Polygon to GeoJSON format:
    geometry = mapping(polygon)

    # Create a STAC Item with Asset:
    item = pystac.Item(
        id=f"{collection}/{bucket}/{platform}/{prefix}",
        geometry=geometry,
        bbox=list(polygon.bounds),  # [min_lon, min_lat, max_lon, max_lat]
        datetime=None,
        start_datetime=datetime.datetime(year=int(start_date.split("-")[0]), month=int(start_date.split("-")[1]), day=int(start_date.split("-")[2])),
        end_datetime=datetime.datetime(year=int(end_date.split("-")[0]), month=int(end_date.split("-")[1]), day=int(end_date.split("-")[2])),
        properties={
            "title": f"{config} {prefix} Zarr store",
            "description": description,
            "platform": platform,
            "variables": list(ds.data_vars),
            "variable_standard_names": [ds[var].attrs.get('standard_name', var) for var in ds.data_vars],
            "dimensions": list(ds.dims),
            "operation": operation.split(" ")[1],
            "operation_frequency": operation.split(" ")[0],
            "ocean_component": "NEMO v4.2.2",
            "si_component": "SI3 v4.0",
            "status": "completed",
            "latest_data_update": datetime.datetime.now().isoformat(),
        },
        collection=collection,
    )

    item.add_asset(key=prefix.split('/')[-1], asset=pystac.Asset(
        href=f"https://noc-msm-o.s3-ext.jc.rl.ac.uk/{bucket}/{prefix}",
        title=f"{config} {prefix} Zarr store.",
        description=description,
        media_type="application/vnd+zarr",
        extra_fields=dict(
            bucket=bucket,
            prefix=prefix,
            endpoint_url=endpoint_url,
            zarr_format=zarr_format,
            anonymous=True
        )
    ))

    return item