"""
utils.py

Description:
Utility functions to create the National Oceanography Centre
(NOC) Spatio-Temporal Access Catalog and write to JSON files.

Authors:
    - Ollie Tooth (oliver.tooth@noc.ac.uk)
"""
# -- Import Python Modules -- #
import pystac
import datetime
import icechunk
import xarray as xr
from shapely.geometry import Polygon, mapping

# -- I/O Functions -- #
def open_icechunk_store(
    bucket: str,
    prefix: str,
    branch: str = "main",
    group: str | None = None,
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
    group : str, optional
        Group within the Icechunk repository to open (default is None).
    endpoint_url : str, optional
        The S3 endpoint URL (default is "https://noc-msm-o.s3-ext.jc.rl.ac.uk").
    """
    # Define S3 storage:
    storage = icechunk.s3_storage(
    bucket=bucket,
    prefix=prefix,
    region="us-east-1",
    anonymous=True,
    endpoint_url=endpoint_url,
    force_path_style=True,
    )

    # Open Icechunk Repository:
    repo = icechunk.Repository.open(storage=storage)

    # Open Dataset from Icechunk Store:
    return xr.open_zarr(repo.readonly_session(branch=branch).store, group=group, consolidated=False)


# -- STAC Functions -- #
def create_item_with_zarr_asset(
    id : str,
    ds: xr.Dataset,
    bucket: str,
    prefix: str,
    title: str,
    dataset_type: str = "model",
    product_type: str = "timeseries",
    product_version: str = "1.0",
    institution: str = "National Oceanography Centre, UK",
    platform: str = "gn",
    horizontal_grid_type: str = "curvilinear",
    horizontal_grid_resolution: str = "1 degree",
    vertical_grid_type: str = "zps",
    vertical_grid_coordinate: str = "depth with partial steps",
    vertical_grid_levels: int = 75,
    operation: str ="annual-mean",
    status: str = "completed",
    update_frequency: str = "None",
    variant: str = "r1i1c1f1",
    ocean_component: str = "NEMO v4.2.2",
    sea_ice_component: str = "SI3 v4.0",
    biogeochemistry_component: str = "None",
    atmosphere_component: str = "None",
    atmospheric_forcing: str = "JRA55-do",
    start_date: str = "1976-01-01",
    end_date: str = "2024-02-01",
    bbox: tuple = (-180.0, -90.0, 180.0, 90.0),
    collection : str = "noc-npd-jra55",
    variable_stores: bool = True,
    endpoint_url: str = "https://noc-msm-o.s3-ext.jc.rl.ac.uk",
    zarr_format: int = 2,
    ) -> pystac.Item:
    """
    Create a STAC Item from a Zarr Store asset.

    Parameters
    ----------
    id : str
        Unique identifier for the STAC Item.
    ds : xr.Dataset
        Dataset containing the data to be included in the STAC Item.
    bucket : str
        S3 bucket name where the data is stored.
    prefix : str
        Prefix for the data in the S3 bucket (e.g., "U1y", "U1m", etc.).
    title : str
        Title of the dataset.
    dataset_type : str
        Type of dataset (e.g., "model", "observation", etc.).
    product_type : str
        Type of product (e.g., "climatology", "timeseries", etc.).
    product_version : str
        Version of the product.
    institution : str
        Institution responsible for producing the dataset.
    platform : str
        Platform name (e.g., "gn_global", "gr_global", etc.).
    horizontal_grid_type : str
        Type of horizontal grid used in the dataset (e.g., "regular rectilinear", "irregular rectilinear", "curvilinear", etc.).
    horizontal_grid_resolution : str
        Horizontal grid resolution of the dataset (e.g., "1 degreee", "0.25 degree", etc.).
    vertical_grid_type : str
        Type of vertical grid used in the dataset (e.g., "z", "sigma", "hybrid", etc.).
    vertical_grid_coordinate : str
        Type of vertical coordinate used in the dataset (e.g., "depth", "sigma", etc.).
    vertical_grid_levels : int
        Number of vertical levels in the dataset.
    operation : str, optional
        Operation string indicating the type of operation performed on the dataset (default is "annual-mean").
    status : str, optional
        Status of the dataset (e.g., "ongoing", "completed", etc.) (default is "completed").
    update_frequency : str, optional
        Frequency at which the dataset is updated (e.g., "monthly", "biannually", etc.) (default is "None").
    variant : str, optional
        Simulation variant string for the dataset (default is "r1i1c1f1").
    ocean_component : str, optional
        Ocean model component used to produce the dataset (e.g., "NEMO v4.2.2", etc.) (default is "NEMO v4.2.2").
    sea_ice_component : str, optional
        Sea ice model component used to produce the dataset (e.g., "CICE v6.1", etc.) (default is "SI3 v4.0").
    biogeochemistry_component : str, optional
        Biogeochemistry model component used to produce the dataset (e.g., "PISCES v2", etc.) (default is "None").
    atmosphere_component : str, optional
        Atmospheric model component used to produce the dataset (e.g., "UKMO UM Global Atmosphere 7.1", etc.) (default is "None").
    atmospheric_forcing : str, optional
        Atmospheric forcing used to produce the dataset (e.g., "ERA5", "JRA55-do", etc.) (default is "JRA55-do").
    start_date : str, optional
        Start date of the dataset in "YYYY-MM-DD" format (default is "1976-01-01").
    end_date : str, optional
        End date of the dataset in "YYYY-MM-DD" format (default is "2024-12-31").
    bbox : tuple, optional
        Bounding box for the dataset in the format (min_lon, min_lat, max_lon, max_lat).
        (default is global coverage).
    collection : str, optional
        STAC Collection to which this Item belongs (default is "noc-npd-jra55").
    variable_stores : bool, optional
        Whether each variable is stored in a separate Zarr store (default is True).
    endpoint_url : str, optional
        S3 endpoint URL (default is "https://noc-msm-o.s3-ext.jc.rl.ac.uk").
    zarr_format: int, optional
        Zarr format version (default is 2).

    Returns
    -------
    pystac.Item
        A STAC Item containing the dataset information and an asset pointing to the data.
    """
    # Define the item description based on the prefix:
    var = f"{prefix.split('/')[-1]} output" if variable_stores else "outputs"

    if 'domain' in prefix:
        description = "**Global ocean model domain and mesh mask variables.**"
    elif 'I' in prefix:
        description = f"**{operation.capitalize()} global sea-ice {var} defined at NEMO model T-points.**"
    elif 'S' in prefix:
        description = f"**{operation.capitalize()} global ocean scalar {var}.**"
    elif 'M' in prefix:
        description = f"**{operation.capitalize()} ocean physics transect {var} defined at {prefix.split('/')[-1]}.**"
    else:
        description = f"**{operation.capitalize()} global ocean physics {var} defined at {prefix[0]}-points.**"

    # Add OceanDataCatalog Access Information to the description:
    description += f"\n\n**OceanDataCatalog Access:**\n`catalog.open_dataset(id='{id}')`"

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
        id=id,
        geometry=geometry,
        bbox=list(polygon.bounds),  # [min_lon, min_lat, max_lon, max_lat]
        datetime=datetime.datetime(year=(int(start_date.split("-")[0]) + int(end_date.split("-")[0])) // 2, month=1, day=1),
        start_datetime=datetime.datetime(year=int(start_date.split("-")[0]), month=int(start_date.split("-")[1]), day=int(start_date.split("-")[2])),
        end_datetime=datetime.datetime(year=int(end_date.split("-")[0]), month=int(end_date.split("-")[1]), day=int(end_date.split("-")[2])),
        properties={
            "title": title,
            "description": description,
            "dataset_type": dataset_type,
            "product_type": product_type,
            "product_version": product_version,
            "institution": institution,
            "platform": platform,
            "horizontal_grid_type": horizontal_grid_type,
            "horizontal_grid_resolution": horizontal_grid_resolution,
            "vertical_grid_type": vertical_grid_type,
            "vertical_grid_coordinate": vertical_grid_coordinate,
            "vertical_grid_levels": vertical_grid_levels,
            "dimensions": list(ds.dims),
            "variables": list(ds.data_vars),
            "variable_standard_names": [ds[var].attrs.get('standard_name', var) for var in ds.data_vars],
            "aggregation": operation.split()[1].lower(),
            "aggregation_frequency": operation.split()[0].lower(),
            "status": status,
            "update_frequency": update_frequency,
            "latest_data_update": datetime.datetime.now().isoformat(),
            "variant": variant,
            "ocean_component": ocean_component,
            "sea_ice_component": sea_ice_component,
            "biogeochemistry_component": biogeochemistry_component,
            "atmosphere_component": atmosphere_component,
            "atmospheric_forcing": atmospheric_forcing,
        },
        collection=collection,
    )

    item.add_asset(key=prefix.split('/')[-1], asset=pystac.Asset(
        href=f"https://noc-msm-o.s3-ext.jc.rl.ac.uk/{bucket}/{prefix}",
        title=title,
        description=description,
        media_type="application/vnd.zarr",
        extra_fields=dict(
            endpoint_url=endpoint_url,
            bucket=bucket,
            prefix=prefix,
            zarr_format=zarr_format,
            anonymous=True
        )
    ))

    return item


def create_item_with_icechunk_asset(
    ds: xr.Dataset,
    id: str,
    bucket: str,
    prefix: str,
    title: str | None = None,
    description: str | None = None,
    dataset_type: str | None = None,
    product_type: str | None = None,
    product_version: str | None = None,
    institution: str | None = None,
    citation: str | None = None,
    acknowledgement: str | None = None,
    license: str | None = None,
    doi: str | None = None,
    platform: str | None = None,
    horizontal_grid_type: str | None = None,
    horizontal_grid_resolution: str | None = None,
    vertical_grid_type: str | None = None,
    vertical_grid_coordinate: str | None = None,
    vertical_grid_levels: int | None = None,
    aggregation: str | None = None,
    aggregation_frequency: str | None = None,
    status: str | None = None,
    update_frequency: str | None = None,
    ocean_component: str | None = None,
    sea_ice_component: str | None = None,
    biogeochemistry_component: str | None = None,
    atmosphere_component: str | None = None,
    atmospheric_forcing: str | None = None,
    variant: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    bbox: tuple | None = None,
    collection: str = "noc-npd-era5",
    endpoint_url: str = "https://noc-msm-o.s3-ext.jc.rl.ac.uk",
    group: str | None = None,
    anonymous: bool = True,
    ) -> pystac.Item:
    """
    Create a STAC Item from an Icechunk Store.

    Parameters
    ----------
    ds : xr.Dataset
        Dataset to be included in the STAC Item.
    id : str
        Unique identifier for the STAC Item.
    bucket : str
        S3 bucket name where the dataset is stored.
    prefix : str
        Prefix for the dataset in the S3 bucket (e.g., "U1y", "U1m", etc.).
    title : str, optional
        Title of the dataset (default is None, which will use the "title" attribute from the dataset if available).
    description : str, optional
        Description of the dataset (default is None, which will use the "description" attribute from the dataset if available).
    dataset_type : str, optional
        Type of dataset (e.g., "model", "observation", etc.) (default is None, which will use the "dataset_type" attribute from the dataset if available).
    product_type : str, optional
        Type of product (e.g., "climatology", "timeseries", etc.) (default is None, which will use the "product_type" attribute from the dataset if available).
    product_version : str, optional
        Version of the product (default is None, which will use the "product_version" attribute from the dataset if available).
    institution : str, optional
        Institution responsible for producing the dataset (default is None, which will use the "institution" attribute from the dataset if available).
    citation : str, optional
        Citation for the dataset (default is None, which will use the "citation" attribute from the dataset if available).
    acknowledgement : str, optional
        Acknowledgement for the dataset (default is None, which will use the "acknowledgement" attribute from the dataset if available).
    license : str, optional
        License for the dataset (default is None, which will use the "license" attribute from the dataset if available).
    doi : str, optional
        Digital Object Identifier (DOI) for the dataset (default is None, which will use the "doi" attribute from the dataset if available).
    platform : str, optional
        Platform string (e.g., "gn", "gr", "tn", etc.) (default is None, which will use the "platform" attribute from the dataset if available).
    horizontal_grid_type : str, optional
        Type of horizontal grid used in the dataset (e.g., "regular rectilinear", "irregular rectilinear", "curvilinear", etc.) (default is None, which will use the "horizontal_grid_type" attribute from the dataset if available).
    horizontal_grid_resolution : str, optional
        Horizontal resolution of the dataset (e.g., "1 degree", "0.25 degree", etc.) (default is None, which will use the "horizontal_grid_resolution" attribute from the dataset if available).
    vertical_grid_type : str, optional
        Type of vertical grid used in the dataset (e.g., "z", "sigma", "hybrid", etc.) (default is None, which will use the "vertical_grid_type" attribute from the dataset if available).
    vertical_grid_coordinate : str, optional
        Type of vertical coordinate used in the dataset (e.g., "depth", "sigma", etc.) (default is None, which will use the "vertical_grid_coordinate" attribute from the dataset if available).
    vertical_grid_levels : int, optional
        Number of vertical levels in the dataset (default is None, which will use the "vertical_grid_levels" attribute from the dataset if available).
    aggregation : str, optional
        Type of aggregation used to produce the dataset (e.g., "mean", "max", etc.) (default is None, which will use the "aggregation" attribute from the dataset if available).
    aggregation_frequency : str, optional
        Frequency at which the aggregation is applied (e.g., "monthly", "biannually", etc.) (default is None, which will use the "aggregation_frequency" attribute from the dataset if available).
    status : str, optional
        Status of the dataset (e.g., "ongoing", "completed", etc.) (default is None, which will use the "status" attribute from the dataset if available).
    update_frequency : str, optional
        Frequency at which the dataset is updated (e.g., "monthly", "biannually", etc.) (default is None, which will use the "update_frequency" attribute from the dataset if available).
    ocean_component : str, optional
        Ocean model component used to produce the dataset (e.g., "NEMO v4.2.2", etc.) (default is None, which will use the "ocean_component" attribute from the dataset if available).
    sea_ice_component : str, optional
        Sea ice model component used to produce the dataset (e.g., "CICE v6.1", etc.) (default is None, which will use the "sea_ice_component" attribute from the dataset if available).
    biogeochemistry_component : str, optional
        Biogeochemistry model component used to produce the dataset (e.g., "PISCES v2", etc.) (default is None, which will use the "biogeochemistry_component" attribute from the dataset if available).
    atmosphere_component : str, optional
        Atmospheric model component used to produce the dataset (e.g., "UKMO UM Global Atmosphere 7.1", etc.) (default is None, which will use the "atmosphere_component" attribute from the dataset if available).
    atmospheric_forcing : str, optional
        Atmospheric forcing used to produce the dataset (e.g., "ERA5", "JRA-55", etc.) (default is None, which will use the "atmospheric_forcing" attribute from the dataset if available).
    variant : str, optional
        Configuration variant string for the dataset (default is "r1i1c1f1").
    start_date : str, optional
        Start date of the dataset in "YYYY-MM-DD" format (default is "1976-01-01").
    end_date : str, optional
        End date of the dataset in "YYYY-MM-DD" format (default is "2024-12-31").
    bbox : tuple, optional
        Bounding box for the dataset in the format (min_lon, min_lat, max_lon, max_lat).
        (default is global coverage).
    collection : str, optional
        Collection to which this Item belongs (default is "noc-npd-era5").
    endpoint_url : str, optional
        The S3 endpoint URL (default is "https://noc-msm-o.s3-ext.jc.rl.ac.uk").
    group : str, optional
        Group within the Icechunk repository to open (default is None).
    anonymous : bool, optional
        Whether anonymous access is supported for the S3 asset (default is True).

    Returns
    -------
    pystac.Item
        STAC Item containing the dataset metadata and associated dataset asset.
    """
    # === Geometry === #
    # Collect bounding box from dataset attributes if not provided:
    bbox = ds.attrs.get("bbox", "[-180.0, -90.0, 180.0, 90.0]") if bbox is None else bbox
    bbox = [float(bound) for bound in bbox.replace("[", "").replace("]", "").split(",")]

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

    # === Properties === #
    # Add OceanDataCatalog Access Information to description:
    if description is None:
        description = ds.attrs.get("description", "")
    description += f"\n\n**OceanDataCatalog Access:**\n`catalog.open_dataset(id='{id}')`"

    # Define start and end datetimes for the Item:
    if start_date is None:
        start_date = ds.attrs.get("start_date", None)
        if start_date is None:
            raise ValueError("'start_date' must be provided either as a parameter or as a global dataset attribute.")
    if end_date is None:
        end_date = ds.attrs.get("end_date", None)
        if end_date is None:
            raise ValueError("'end_date' must be provided either as a parameter or as a global dataset attribute.")

    # Define standard properties dictionary:
    properties={
                "title": ds.attrs.get("title", None) if title is None else title,
                "description": description,
                "dataset_type": ds.attrs.get("dataset_type", None) if dataset_type is None else dataset_type,
                "product_type": ds.attrs.get("product_type", None) if product_type is None else product_type,
                "product_version": ds.attrs.get("product_version", None) if product_version is None else product_version,
                "institution": ds.attrs.get("institution", None) if institution is None else institution,
                "citation": ds.attrs.get("citation", None) if citation is None else citation,
                "acknowledgement": ds.attrs.get("acknowledgement", None) if acknowledgement is None else acknowledgement,
                "license": ds.attrs.get("license", None) if license is None else license,
                "doi": ds.attrs.get("doi", None) if doi is None else doi,
                "platform": ds.attrs.get("platform", None) if platform is None else platform,
                "horizontal_grid_type": ds.attrs.get("horizontal_grid_type", None) if horizontal_grid_type is None else horizontal_grid_type,
                "horizontal_grid_resolution": ds.attrs.get("horizontal_grid_resolution", None) if horizontal_grid_resolution is None else horizontal_grid_resolution,
                "vertical_grid_type": ds.attrs.get("vertical_grid_type", None) if vertical_grid_type is None else vertical_grid_type,
                "vertical_grid_coordinate": ds.attrs.get("vertical_grid_coordinate", None) if vertical_grid_coordinate is None else vertical_grid_coordinate,
                "vertical_grid_levels": ds.attrs.get("vertical_grid_levels", None) if vertical_grid_levels is None else vertical_grid_levels,
                "dimensions": list(ds.dims),
                "variables": list(ds.data_vars),
                "variable_standard_names": [ds[var].attrs.get('standard_name', var) for var in ds.data_vars],
                "aggregation": ds.attrs.get("aggregation", None) if aggregation is None else aggregation,
                "aggregation_frequency": ds.attrs.get("aggregation_frequency", None) if aggregation_frequency is None else aggregation_frequency,
                "status": ds.attrs.get("status", None) if status is None else status,
                "update_frequency": ds.attrs.get("update_frequency", None) if update_frequency is None else update_frequency,
                "latest_data_update": datetime.datetime.now().isoformat(),
                }
    
    if properties["dataset_type"] == "model":
        # Append numerical model specific properties:
        properties.update({
            "variant": ds.attrs.get("variant", None) if variant is None else variant,
            "ocean_component": ds.attrs.get("ocean_component", None) if ocean_component is None else ocean_component,
            "sea_ice_component": ds.attrs.get("sea_ice_component", None) if sea_ice_component is None else sea_ice_component,
            "biogeochemistry_component": ds.attrs.get("biogeochemistry_component", None) if biogeochemistry_component is None else biogeochemistry_component,
            "atmosphere_component": ds.attrs.get("atmosphere_component", None) if atmosphere_component is None else atmosphere_component,
            "atmospheric_forcing": ds.attrs.get("atmospheric_forcing", None) if atmospheric_forcing is None else atmospheric_forcing,
        })

    # === Create a STAC Item with Asset === #
    item = pystac.Item(
        id=id,
        geometry=geometry,
        bbox=list(polygon.bounds),
        datetime=datetime.datetime(year=(int(start_date.split("-")[0]) + int(end_date.split("-")[0])) // 2, month=1, day=1),
        start_datetime=datetime.datetime(year=int(start_date.split("-")[0]), month=int(start_date.split("-")[1]), day=int(start_date.split("-")[2])),
        end_datetime=datetime.datetime(year=int(end_date.split("-")[0]), month=int(end_date.split("-")[1]), day=int(end_date.split("-")[2])),
        properties=properties,
        collection=collection,
    )

    item.add_asset(key=prefix.split('/')[-1], asset=pystac.Asset(
        href=f"{endpoint_url}/{bucket}/{prefix}",
        title=ds.attrs.get("title", None) if title is None else title,
        description=description,
        media_type="application/vnd.zarr+icechunk",
        extra_fields=dict(
            endpoint_url=endpoint_url,
            bucket=bucket,
            prefix=prefix,
            variant=ds.attrs.get("variant", None) if variant is None else variant,
            group=group,
            anonymous=anonymous
        )
    ))

    return item
