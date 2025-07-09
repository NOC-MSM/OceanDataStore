"""
create_noc_stac.py

Description:
This script defines the National Oceanography Centre (NOC)
Spatio-Temporal Access Catalog and writes to JASMIN cloud
object storage.

Authors:
    - Ollie Tooth
"""
# -- Import Python Modules -- #
import os
import pystac
import datetime
import icechunk
import xarray as xr
from shapely.geometry import Polygon, mapping

# -- Define Utility Functions -- #
def create_item_with_asset(ds: xr.Dataset,
                           bucket: str,
                           platform: str,
                           prefix: str,
                           config: str ="eORCA1 ERA5v1 NPD",
                           operation: str ="annual-mean",
                           ) -> pystac.Item:
    """
    Create a STAC Item with an asset from an xarray Dataset.

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
    config : str, optional
        The configuration string for the dataset (default is "eORCA1 ERA5v1 NPD").
    operation : str, optional
        The operation string indicating the type of operation performed on the dataset (default is "annual-mean").

    Returns
    -------
    pystac.Item
        A STAC Item containing the dataset information and an asset pointing to the data.
    """
    # Define the item description based on the prefix:
    if 'I' in prefix:
        description = f"Icechunk repository containing {config} global sea-ice {operation} outputs defined at T-points."
    elif 'S' in prefix:
        description = f"Icechunk repository containing {config} global ocean scalar {operation} outputs."
    else:
        description = f"Icechunk repository containing {config} global ocean physics {operation} outputs defined at {prefix[0]}-points."

    # Define Polygon geometry for the item:
    polygon = Polygon([
        (-180.0, -90.0),  # SW corner
        (180.0, -90.0),   # SE corner
        (180.0, 90.0),    # NE corner
        (-180.0, 90.0),   # NW corner
        (-180.0, -90.0)   # Closing the polygon back to SW corner
    ])

    # Convert the Polygon to GeoJSON format:
    geometry = mapping(polygon)

    # Create a STAC Item with Asset:
    item = pystac.Item(
        id=f"noc-npd/{bucket}/{platform}/{prefix}",
        geometry=geometry,
        bbox=list(polygon.bounds),  # [min_lon, min_lat, max_lon, max_lat]
        datetime=None,
        start_datetime=datetime.datetime(year=1976, month=1, day=1),
        end_datetime=datetime.datetime(year=2024, month=12, day=31),
        properties={
            "title": f"{config} {prefix} Icechunk repository",
            "description": description,
            "platform": platform,
            "variables": list(ds.data_vars),
            "dimensions": list(ds.dims),
            "operation": operation.split(" ")[1],
            "operation_frequency": operation.split(" ")[0],
            "ocean_component": "NEMO v4.2.2",
            "si_component": "SI3 v4.0",
            "status": "ongoing",
            "update_frequency": "quarterly",
            "latest_data_update": datetime.datetime.now().isoformat(),
        },
        collection="noc-npd",
    )

    item.add_asset(key=prefix, asset=pystac.Asset(
        href=f"https://noc-msm-o.s3-ext.jc.rl.ac.uk/{bucket}/{platform}/{prefix}",
        title=f"{config} {prefix} Icechunk repository",
        description=description,
        media_type=pystac.MediaType.ZARR,
        extra_fields=dict(
            bucket=bucket,
            prefix=prefix,
            endpoint_url="https://noc-msm-o.s3-ext.jc.rl.ac.uk",
            anonymous=True
        )
    ))

    return item


# -- Define NOC Model STAC Base Catalog -- #
noc_stac = pystac.Catalog(id="noc-model-stac",
                         title="NOC Model STAC Catalog",
                         description='National Oceanography Centre Spatio-Temporal Asset Catalog for Ocean Model Data',
                         stac_extensions=None,
                         extra_fields={
                             "created": datetime.datetime.now().isoformat(),
                             "last_update": datetime.datetime.now().isoformat(),
                             "catalog_version": "0.1.0",
                             "contacts": ["Oliver Tooth (oliver.tooth@noc.ac.uk)",
                                          "Adam Blaker (atb299@noc.ac.uk)",
                                          "Andrew Coward (acc@noc.ac.uk)",
                                          ],
                             },
                         )

# -- Define NOC Near-Present Day Collection -- #
# Define the spatial extent for the collection:
spatial_extent = pystac.SpatialExtent(bboxes=[[-180.0, -90.0, 0, 180.0, 90.0, 6000]])

# Define the current temporal extent for the collection:
collection_interval = sorted([datetime.datetime(year=1976, month=1, day=1), datetime.datetime(year=2024, month=12, day=31)])
temporal_extent = pystac.TemporalExtent(intervals=[collection_interval])

# Define the Near-Present Day Collection:
npd_collection = pystac.Collection(
    id="noc-npd",
    title="NOC Near-Present Day Collection",
    description="Collection of multi-decadal Near-Present Day ocean model simulations produced by the National Oceanography Centre (NOC) as part of the Atlantic Climate and Environment Strategic Science (AtlantiS) programme.",
    extent=pystac.Extent(spatial=spatial_extent, temporal=temporal_extent),
    # Open Government License (OGL) - UK version 3.0 - http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
    license="OGL-UK-3.0",
    extra_fields=dict(project="AtlantiS", status="ongoing", update_frequency="quarterly", last_data_update="2025-05-30"),
    keywords=["NOC", "Near-Present Day", "AtlantiS", "hindcast", "global", "model", "ocean", "sea-ice"],
    providers=[
        pystac.Provider(
            name="National Oceanography Centre",
            description="National Oceanography Centre (United Kindom) - Marine Systems Modelling group.",
            roles=[pystac.ProviderRole.PRODUCER, pystac.ProviderRole.LICENSOR],
            url="https://noc-msm.github.io/NOC_Near_Present_Day/"
        ),
        pystac.Provider(
            name="JASMIN",
            description="JASMIN environmental data analysis facility (United Kindgom).",
            roles=[pystac.ProviderRole.HOST],
            url="https://jasmin.ac.uk"
        )
    ],
)

# -- Define NOC Near-Present Day Model Configuration Catalogs -- #
npd_eorca1_era5v1 = pystac.Catalog(
    id="noc-npd/npd-eorca1-era5v1",
    title="eORCA1 ERA5v1 NPD Catalog",
    description="Catalog of outputs from the eORCA1 ERA-5 version 1 Near-Present Day ocean physics simulation performed by the National Oceanography Centre."
    )

npd_eorca025_era5v1 = pystac.Catalog(
    id="noc-npd/npd-eorca025-era5v1",
    title="eORCA025 ERA5v1 NPD Catalog",
    description="Catalog of outputs from the eORCA025 ERA-5 version 1 Near-Present Day ocean physics simulation performed by the National Oceanography Centre.",
    )

npd_eorca12_era5v1 = pystac.Catalog(
    id="noc-npd/npd-eorca12-era5v1",
    title="eORCA12 ERA5v1 NPD Catalog",
    description="Catalog of outputs from the eORCA12 ERA-5 version 1 Near-Present Day ocean physics simulation performed by the National Oceanography Centre.",
    )

# Define NOC Near-Present Day Platform Sub-Catalogs -- #
# Note: Options for platforms are: "gn_global", "gr_global", "gn_regional{1...4}", "gr_regional{1...4}", "tn", "tr".
# where gn = global native model grids, gr = global regridded grids, tn = transects on native model grids, tr = transects on regridded grids.

gn_eorca1_era5v1 = pystac.Catalog(
    id="noc-npd/npd-eorca1-era5v1/gn_global",
    title="eORCA1 ERA5v1 NPD global native model grid Catalog",
    description="Catalog of global ocean physics outputs stored on the native eORCA1 curvilinear model grid."
    )

gn_eorca025_era5v1 = pystac.Catalog(
    id="noc-npd/npd-eorca025-era5v1/gn_global",
    title="eORCA025 ERA5v1 NPD global native model grid Catalog",
    description="Catalog of global ocean physics outputs stored on the native eORCA025 curvilinear model grid."
    )

gn_eorca12_era5v1 = pystac.Catalog(
    id="noc-npd/npd-eorca12-era5v1/gn_global",
    title="eORCA12 ERA5v1 NPD global native model grid Catalog",
    description="Catalog of global ocean physics outputs stored on the native eORCA12 curvilinear model grid."
    )

# -- Add Items to NOC Near-Present Day eORCA1 ERA5v1 Sub-Catalog -- #
# Define the store credentials for the eORCA1 ERA5v1 NPD data:
for prefix in ["T1y", "U1y", "V1y", "W1y", "I1y", "S1y", "T1m", "U1m", "V1m", "W1m", "I1m", "S1m"]:
    # Define S3 storage to read eORCA1 ERA5v1 NPD data:
    storage = icechunk.s3_storage(
    bucket="npd-eorca1-era5v1",
    prefix=prefix,
    anonymous=True,
    endpoint_url="https://noc-msm-o.s3-ext.jc.rl.ac.uk",
    force_path_style=True,
    )
    # Open Icechunk repository:
    repo = icechunk.Repository.open(storage=storage)
    # Open dataset from Icechunk repository:
    ds = xr.open_zarr(repo.readonly_session(branch="main").store, consolidated=False)

    # Create item with asset for each eORCA1 ERA5v1 NPD prefix:
    if '1y' in prefix:
        operation = "annual mean"
    elif '1m' in prefix:
        operation = "monthly mean"
    elif '5d' in prefix:
        operation = "5-day mean"

    item = create_item_with_asset(
        ds=ds,
        bucket="npd-eorca1-era5v1",
        platform="gn_global",
        prefix=prefix,
        config="eORCA1 ERA5v1 NPD",
        operation=operation
    )
    # Add item to the eORCA1 ERA5v1 NPD global native model grid catalog:
    gn_eorca1_era5v1.add_item(item)

# -- Add Items to NOC Near-Present Day eORCA025 ERA5v1 Sub-Catalog -- #
# Define the store credentials for the eORCA025 ERA5v1 NPD data:
for prefix in ["T1y_3d", "T1y_4d", "U1y_3d", "U1y_4d", "V1y_3d", "V1y_4d", "W1y_4d", "I1y_3d", "S1y_1d",
               "T1m_3d", "T1m_4d", "U1m_3d", "U1m_4d", "V1m_3d", "V1m_4d", "W1m_4d", "I1m_3d", "S1m_1d",
               "T5d_3d", "T5d_4d", "U5d_3d", "U5d_4d", "V5d_3d", "V5d_4d", "I5d_3d", "S5d_1d",
               ]:
    # Define S3 storage to read eORCA025 ERA5v1 NPD data:
    storage = icechunk.s3_storage(
    bucket="npd-eorca025-era5v1",
    prefix=prefix,
    anonymous=True,
    endpoint_url="https://noc-msm-o.s3-ext.jc.rl.ac.uk",
    force_path_style=True,
    )
    # Open Icechunk repository:
    repo = icechunk.Repository.open(storage=storage)
    # Open dataset from Icechunk repository:
    ds = xr.open_zarr(repo.readonly_session(branch="main").store, consolidated=False)

    # Create item with asset for each eORCA025 ERA5v1 NPD prefix:
    if '1y' in prefix:
        operation = "annual mean"
    elif '1m' in prefix:
        operation = "monthly mean"
    elif '5d' in prefix:
        operation = "5-day mean"

    item = create_item_with_asset(
        ds=ds,
        bucket="npd-eorca025-era5v1",
        platform="gn_global",
        prefix=prefix,
        config="eORCA025 ERA5v1 NPD",
        operation=operation
    )
    # Add item to the eORCA025 ERA5v1 NPD global native model grid catalog:
    gn_eorca025_era5v1.add_item(item)


# -- Add Catalogs to NOC Near-Present Day Collection -- #
npd_eorca1_era5v1.add_child(gn_eorca1_era5v1)
npd_eorca025_era5v1.add_child(gn_eorca025_era5v1)
npd_eorca12_era5v1.add_child(gn_eorca12_era5v1)

npd_collection.add_child(npd_eorca1_era5v1)
npd_collection.add_child(npd_eorca025_era5v1)
npd_collection.add_child(npd_eorca12_era5v1)

# -- Add NOC Near-Present Day Collection to NOC STAC Catalog -- #
noc_stac.add_child(npd_collection)

# -- Write NOC Model STAC Catalog to local filesystem -- #
print(noc_stac.describe())

noc_stac.normalize_hrefs(root_href="https://noc-msm-o.s3-ext.jc.rl.ac.uk/noc-model-stac/")
noc_stac.save(catalog_type=pystac.CatalogType.SELF_CONTAINED, dest_href=os.path.join(os.getcwd(), "noc-model-stac"))