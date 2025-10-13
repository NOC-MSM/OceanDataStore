"""
npd_collections.py

Description:
Function to create the National Oceanography Centre (NOC) 
Near-Present Day Spatio-Temporal Access Catalog Collection.

Authors:
    - Ollie Tooth
"""
# -- Import Python Modules -- #
import logging
import pystac
import datetime
import xarray as xr
from tqdm import tqdm
from OceanDataStore.object_store import ObjectStoreS3

from utils import open_icechunk_store
from utils import create_item_with_icechunk_asset, create_item_with_zarr_asset

def create_npd_jra55_collection(
    credentials_json: str = "/dssgfs01/working/otooth/AtlantiS/jasmin_os/credentials/jasmin_os_credentials.json"
    ) -> pystac.Collection:
    """
    Create the NOC Near-Present Day JRA55-do STAC Collection.

    Parameters:
    ----------
    credentials_json : str
        Path to the JSON file containing the credentials for the S3 object store.
    
    Returns:
    -------
    npd_collection : pystac.Collection
        NOC Near-Present Day STAC Collection.
    """
    # -- Initialise Object Store -- #
    obj_store = ObjectStoreS3(anon=False,
                              asynchronous=False,
                              store_credentials_json=credentials_json
                              )

    # Define list of variable Zarr stores to exclude from the STAC item creation:
    exclude_vars = ['depthu_bounds', 'depthv_bounds', 'depthw_bounds', 'deptht_bounds', 'time_counter_bounds', 'time_centered_bounds']

    # -- Define NOC Near-Present Day Collection -- #
    # Define the spatial extent for the collection:
    spatial_extent = pystac.SpatialExtent(bboxes=[[-180.0, -90.0, 0, 180.0, 90.0, 6000]])

    # Define the current temporal extent for the collection:
    collection_interval = sorted([datetime.datetime(year=1976, month=1, day=1), datetime.datetime(year=2024, month=2, day=1)])
    temporal_extent = pystac.TemporalExtent(intervals=[collection_interval])

    # Define the Near-Present Day Collection:
    npd_collection = pystac.Collection(
        id="noc-npd-jra55",
        title="NOC Near-Present Day JRA55-do Collection",
        description="Collection of multi-decadal Near-Present Day ocean model simulations produced by the National Oceanography Centre (NOC) as part of the Atlantic Climate and Environment Strategic Science (AtlantiS) programme.",
        extent=pystac.Extent(spatial=spatial_extent, temporal=temporal_extent),
        # Open Government License (OGL) - UK version 3.0 - http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
        license="OGL-UK-3.0",
        extra_fields=dict(contact="Ollie Tooth (oliver.tooth@noc.ac.uk)", project="AtlantiS", status="completed", last_data_update="2025-05-30"),
        keywords=["NOC", "JRA55-do", "Near-Present Day", "AtlantiS", "hindcast", "global", "model", "ocean", "sea-ice"],
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

    logging.info(f"Completed: Created NOC STAC Collection with ID: {npd_collection.id}")

    # -- Define NOC Near-Present Day Model Configuration Catalogs -- #
    npd_eorca1_jra55v1 = pystac.Catalog(
        id="npd-eorca1-jra55v1",
        title="eORCA1 JRA55v1 NPD Catalog",
        description="Catalog of outputs from the eORCA1 JRA55-do version 1 Near-Present Day ocean physics simulation performed by the National Oceanography Centre."
        )

    logging.info(f"Completed: Created NOC STAC Catalog with ID: {npd_eorca1_jra55v1.id}")

    npd_eorca025_jra55v1 = pystac.Catalog(
        id="npd-eorca025-jra55v1",
        title="eORCA025 JRA55v1 NPD Catalog",
        description="Catalog of outputs from the eORCA025 JRA55-do version 1 Near-Present Day ocean physics simulation performed by the National Oceanography Centre.",
        )

    logging.info(f"Completed: Created NOC STAC Catalog with ID: {npd_eorca025_jra55v1.id}")

    # Define NOC Near-Present Day Platform Sub-Catalogs -- #
    # Note: Options for platforms are: "gn", "gr", "tn", "tr".
    # where gn = native model grids, gr = regridded grids, tn = transects on native model grids, tr = transects on regridded grids.

    gn_eorca1_jra55v1 = pystac.Catalog(
        id="gn",
        title="eORCA1 JRA55v1 NPD global native model grid Catalog",
        description="Catalog of global ocean physics outputs stored on the native eORCA1 curvilinear model grid."
        )
    
    logging.info(f"Completed: Created NOC STAC Nested Catalog with ID: {gn_eorca1_jra55v1.id}")

    gn_eorca025_jra55v1 = pystac.Catalog(
        id="gn",
        title="eORCA025 JRA55v1 NPD global native model grid Catalog",
        description="Catalog of global ocean physics outputs stored on the native eORCA025 curvilinear model grid."
        )
    
    logging.info(f"Completed: Created NOC STAC Nested Catalog with ID: {gn_eorca025_jra55v1.id}")

    tn_eorca1_jra55v1 = pystac.Catalog(
        id="tn",
        title="eORCA1 JRA55v1 NPD transect Catalog",
        description="Catalog of ocean physics transect outputs defined on the native eORCA1 curvilinear model grid."
    )

    logging.info(f"Completed: Created NOC STAC Nested Catalog with ID: {tn_eorca1_jra55v1.id}")

    tn_eorca025_jra55v1 = pystac.Catalog(
        id="tn",
        title="eORCA025 JRA55v1 NPD transect Catalog",
        description="Catalog of ocean physics transect outputs defined on the native eORCA025 curvilinear model grid."
    )

    logging.info(f"Completed: Created NOC STAC Nested Catalog with ID: {tn_eorca025_jra55v1.id}")

    # -- Add Items to NOC Near-Present Day eORCA1 JRA55v1 Sub-Catalog -- #
    # Define url for eORCA1 JRA55v1 NPD data:
    bucket="npd-eorca1-jra55v1"
    endpoint_url="https://noc-msm-o.s3-ext.jc.rl.ac.uk"

    for prefix in ["T1y", "U1y", "V1y", "W1y", "I1y", "S1y", "T1m", "U1m", "V1m", "W1m", "S1m", "domain"]:
        # Create item with asset for each eORCA1 JRA55v1 NPD prefix:
        if 'domain' in prefix:
            operation = "None None"
            zarr_format=3
        elif '1y' in prefix:
            operation = "annual mean"
            zarr_format=2
        elif '1m' in prefix:
            operation = "monthly mean"
            zarr_format=2

        # Get variable Zarr stores from JASMIN object store:
        var_stores = [path.split("/")[-1] for path in obj_store.ls(f"{bucket}/{prefix}") if path.split("/")[-1] not in exclude_vars]

        # Create STAC Item for each variable Zarr store:
        logging.info(f"In Progress: Adding {prefix} Items...")
        for var in tqdm(var_stores):
            # Open dataset from Zarr store:
            ds = xr.open_zarr(f"{endpoint_url}/{bucket}/{prefix}/{var}", consolidated=True)
            item = create_item_with_zarr_asset(
                id=f"noc-npd-jra55/{bucket}/gn/{prefix}/{var}",
                ds=ds,
                bucket=bucket,
                platform="gn",
                prefix=f"{prefix}/{var}",
                config="eORCA1 JRA55v1 NPD",
                operation=operation,
                zarr_format=zarr_format
            )
            # Add item to the eORCA1 JRA55v1 NPD global native model grid catalog:
            gn_eorca1_jra55v1.add_item(item)

    logging.info(f"Completed: Added Items to NOC STAC Catalog with ID: {gn_eorca1_jra55v1.id}")

    # -- Add Items to NOC Near-Present Day eORCA1 JRA55v1 {tn} Sub-Catalog -- #
    # Define the store credentials for the eORCA1 JRA55v1 NPD data:
    for prefix in ["M1m/move_16N", "M1m/samba_34_5S", "M1m/rapid_26N"]:
        # Open dataset from Zarr store:
        ds = xr.open_zarr(f"{endpoint_url}/{bucket}/{prefix}", consolidated=True)
        item = create_item_with_zarr_asset(
            id=f"noc-npd-jra55/{bucket}/tn/{prefix}",
            ds=ds,
            bucket=bucket,
            platform="tn",
            prefix=prefix,
            config="eORCA1 JRA55v1 NPD",
            operation=operation,
        )

        # Add item to the eORCA1 JRA55v1 NPD transect native model grid catalog:
        tn_eorca1_jra55v1.add_item(item)

    logging.info(f"Completed: Added Items to NOC STAC Catalog with ID: {tn_eorca1_jra55v1.id}")

    # -- Add Items to NOC Near-Present Day eORCA025 JRA55v1 Sub-Catalog -- #
    # Define the store credentials for the eORCA025 JRA55v1 NPD data:
    for prefix in ["T1y", "U1y", "V1y", "W1y", "I1y", "S1y", "T1m", "U1m", "V1m", "W1m", "I1m", "S1m", "domain"]:
        # Define url for eORCA025 JRA55v1 NPD data:
        bucket="npd-eorca025-jra55v1"
        endpoint_url="https://noc-msm-o.s3-ext.jc.rl.ac.uk"

        # Create item with asset for each eORCA025 JRA55v1 NPD prefix:
        if 'domain' in prefix:
            operation = "None None"
            zarr_format=3
        elif '1y' in prefix:
            operation = "annual mean"
            zarr_format=2
        elif '1m' in prefix:
            operation = "monthly mean"
            zarr_format=2

        # Get variable Zarr stores from JASMIN object store:
        var_stores = [path.split("/")[-1] for path in obj_store.ls(f"{bucket}/{prefix}") if path.split("/")[-1] not in exclude_vars]

        # Create STAC Item for each variable Zarr store:
        logging.info(f"In Progress: Adding {prefix} Items...")
        for var in tqdm(var_stores):
            # Open dataset from Zarr store:
            ds = xr.open_zarr(f"{endpoint_url}/{bucket}/{prefix}/{var}", consolidated=True)
            item = create_item_with_zarr_asset(
                id=f"noc-npd-jra55/{bucket}/gn/{prefix}/{var}",
                ds=ds,
                bucket=bucket,
                platform="gn",
                prefix=f"{prefix}/{var}",
                config="eORCA025 JRA55v1 NPD",
                operation=operation,
                zarr_format=zarr_format
            )
            # Add item to the eORCA025 JRA55v1 NPD global native model grid catalog:
            gn_eorca025_jra55v1.add_item(item)

    logging.info(f"Completed: Added Items to NOC STAC Catalog with ID: {gn_eorca025_jra55v1.id}")

    # -- Add Items to NOC Near-Present Day eORCA025 JRA55v1 {tn} Sub-Catalog -- #
    # Define the store credentials for the eORCA025 JRA55v1 NPD data:
    for prefix in ["M1m/move_16N", "M1m/samba_34_5S", "M1m/rapid_26N"]:
        # Open dataset from Zarr store:
        ds = xr.open_zarr(f"{endpoint_url}/{bucket}/{prefix}", consolidated=True)
        item = create_item_with_zarr_asset(
            id=f"noc-npd-jra55/{bucket}/tn/{prefix}",
            ds=ds,
            bucket=bucket,
            platform="tn",
            prefix=prefix,
            config="eORCA025 JRA55v1 NPD",
            operation=operation,
        )

        # Add item to the eORCA025 JRA55v1 NPD transect native model grid catalog:
        tn_eorca025_jra55v1.add_item(item)
    
    logging.info(f"Completed: Added Items to NOC STAC Catalog with ID: {tn_eorca025_jra55v1.id}")

    # -- Add Nested Catalogs to NOC Near-Present Day Collection -- #
    npd_eorca1_jra55v1.add_child(gn_eorca1_jra55v1)
    npd_eorca025_jra55v1.add_child(gn_eorca025_jra55v1)

    npd_eorca1_jra55v1.add_child(tn_eorca1_jra55v1)
    npd_eorca025_jra55v1.add_child(tn_eorca025_jra55v1)

    npd_collection.add_child(npd_eorca1_jra55v1)
    npd_collection.add_child(npd_eorca025_jra55v1)

    return npd_collection


def create_npd_era5_collection() -> pystac.Collection:
    """
    Create the NOC Near-Present Day ERA-5 STAC Collection.
    
    Returns:
    -------
    npd_collection : pystac.Collection
        NOC Near-Present Day STAC Collection.
    """
    # -- Define NOC Near-Present Day Collection -- #
    # Define the spatial extent for the collection:
    spatial_extent = pystac.SpatialExtent(bboxes=[[-180.0, -90.0, 0, 180.0, 90.0, 6000]])

    # Define the current temporal extent for the collection:
    collection_interval = sorted([datetime.datetime(year=1976, month=1, day=1), datetime.datetime(year=2024, month=12, day=31)])
    temporal_extent = pystac.TemporalExtent(intervals=[collection_interval])

    # Define the Near-Present Day Collection:
    npd_collection = pystac.Collection(
        id="noc-npd-era5",
        title="NOC Near-Present Day ERA-5 Collection",
        description="Collection of multi-decadal Near-Present Day ocean model simulations produced by the National Oceanography Centre (NOC) as part of the Atlantic Climate and Environment Strategic Science (AtlantiS) programme.",
        extent=pystac.Extent(spatial=spatial_extent, temporal=temporal_extent),
        # Open Government License (OGL) - UK version 3.0 - http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
        license="OGL-UK-3.0",
        extra_fields=dict(contact="Ollie Tooth (oliver.tooth@noc.ac.uk)", project="AtlantiS", status="ongoing", update_frequency="quarterly", last_data_update="2025-05-30"),
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

    logging.info(f"Completed: Created NOC STAC Collection with ID: {npd_collection.id}")

    # -- Define NOC Near-Present Day Model Configuration Catalogs -- #
    npd_eorca1_era5v1 = pystac.Catalog(
        id="npd-eorca1-era5v1",
        title="eORCA1 ERA5v1 NPD Catalog",
        description="Catalog of outputs from the eORCA1 ERA-5 version 1 Near-Present Day ocean physics simulation performed by the National Oceanography Centre."
        )

    logging.info(f"Completed: Created NOC STAC Catalog with ID: {npd_eorca1_era5v1.id}")

    npd_eorca025_era5v1 = pystac.Catalog(
        id="npd-eorca025-era5v1",
        title="eORCA025 ERA5v1 NPD Catalog",
        description="Catalog of outputs from the eORCA025 ERA-5 version 1 Near-Present Day ocean physics simulation performed by the National Oceanography Centre.",
        )

    logging.info(f"Completed: Created NOC STAC Catalog with ID: {npd_eorca025_era5v1.id}")

    npd_eorca12_era5v1 = pystac.Catalog(
        id="npd-eorca12-era5v1",
        title="eORCA12 ERA5v1 NPD Catalog",
        description="Catalog of outputs from the eORCA12 ERA-5 version 1 Near-Present Day ocean physics simulation performed by the National Oceanography Centre.",
        )

    logging.info(f"Completed: Created NOC STAC Catalog with ID: {npd_eorca12_era5v1.id}")

    # Define NOC Near-Present Day Platform Sub-Catalogs -- #
    # Note: Options for platforms are: "gn", "gr", "tn", "tr".
    # where gn = native model grids, gr = regridded grids, tn = transects on native model grids, tr = transects on regridded grids.

    gn_eorca1_era5v1 = pystac.Catalog(
        id="gn",
        title="eORCA1 ERA5v1 NPD global native model grid Catalog",
        description="Catalog of global ocean physics outputs stored on the native eORCA1 curvilinear model grid."
        )

    logging.info(f"Completed: Created NOC STAC Nested Catalog with ID: {gn_eorca1_era5v1.id}")

    gn_eorca025_era5v1 = pystac.Catalog(
        id="gn",
        title="eORCA025 ERA5v1 NPD global native model grid Catalog",
        description="Catalog of global ocean physics outputs stored on the native eORCA025 curvilinear model grid."
        )

    logging.info(f"Completed: Created NOC STAC Nested Catalog with ID: {gn_eorca025_era5v1.id}")

    gn_eorca12_era5v1 = pystac.Catalog(
        id="gn",
        title="eORCA12 ERA5v1 NPD global native model grid Catalog",
        description="Catalog of global ocean physics outputs stored on the native eORCA12 curvilinear model grid."
        )

    logging.info(f"Completed: Created NOC STAC Nested Catalog with ID: {gn_eorca12_era5v1.id}")

    tn_eorca1_era5v1 = pystac.Catalog(
        id="tn",
        title="eORCA1 ERA5v1 NPD transect Catalog",
        description="Catalog of ocean physics transect outputs defined on the native eORCA1 curvilinear model grid."
    )

    logging.info(f"Completed: Created NOC STAC Nested Catalog with ID: {tn_eorca1_era5v1.id}")

    tn_eorca025_era5v1 = pystac.Catalog(
        id="tn",
        title="eORCA025 ERA5v1 NPD transect Catalog",
        description="Catalog of ocean physics transect outputs defined on the native eORCA025 curvilinear model grid."
    )

    logging.info(f"Completed: Created NOC STAC Nested Catalog with ID: {tn_eorca025_era5v1.id}")

    tn_eorca12_era5v1 = pystac.Catalog(
        id="tn",
        title="eORCA12 ERA5v1 NPD transect Catalog",
        description="Catalog of ocean physics transect outputs defined on the native eORCA12 curvilinear model grid."
    )

    logging.info(f"Completed: Created NOC STAC Nested Catalog with ID: {tn_eorca12_era5v1.id}")

    # -- Add Items to NOC Near-Present Day eORCA1 ERA5v1 {gn} Sub-Catalog -- #
    # Define the store credentials for the eORCA1 ERA5v1 NPD data:
    bucket = "npd-eorca1-era5v1"
    for prefix in ["T1y", "U1y", "V1y", "W1y", "I1y", "S1y", "T1m", "U1m", "V1m", "W1m", "I1m", "S1m",
                   "domain/domain_cfg", "domain/mesh_mask", "domain/subbasins"
                   ]:
        # Open dataset from Icechunk repository:
        ds = open_icechunk_store(bucket=bucket, prefix=prefix, branch="main")

        # Create item with asset for each eORCA1 ERA5v1 NPD prefix:
        if 'domain' in prefix:
            operation = "None None"
        elif '1y' in prefix:
            operation = "annual mean"
        elif '1m' in prefix:
            operation = "monthly mean"
        elif '5d' in prefix:
            operation = "5-day mean"

        item = create_item_with_icechunk_asset(
            id=f"noc-npd-era5/{bucket}/gn/{prefix}",
            ds=ds,
            bucket=bucket,
            platform="gn",
            prefix=prefix,
            config="eORCA1 ERA5v1 NPD",
            operation=operation,
        )
        # Add item to the eORCA1 ERA5v1 NPD global native model grid catalog:
        gn_eorca1_era5v1.add_item(item)

    logging.info(f"Completed: Added Items to NOC STAC Catalog with ID: {gn_eorca1_era5v1.id}")

    # -- Add Items to NOC Near-Present Day eORCA1 ERA5v1 {tn} Sub-Catalog -- #
    # Define the store credentials for the eORCA1 ERA5v1 NPD data:
    for prefix in ["M1m/MOVE_16N", "M1m/SAMBA_34_5S", "M1m/RAPID_26N", "M1m/OSNAP"]:
        # Open dataset from Icechunk repository:
        ds = open_icechunk_store(bucket=bucket, prefix=prefix, branch="main")

        # Create item with asset for each eORCA1 ERA5v1 NPD prefix:
        operation = "monthly mean"
        item = create_item_with_icechunk_asset(
            id=f"noc-npd-era5/{bucket}/tn/{prefix}",
            ds=ds,
            bucket=bucket,
            platform="tn",
            prefix=prefix,
            config="eORCA1 ERA5v1 NPD",
            operation=operation,
        )
        # Add item to the eORCA1 ERA5v1 NPD global native model grid catalog:
        tn_eorca1_era5v1.add_item(item)

    logging.info(f"Completed: Added Items to NOC STAC Catalog with ID: {tn_eorca1_era5v1.id}")

    # -- Add Items to NOC Near-Present Day eORCA025 ERA5v1 {gn} Sub-Catalog -- #
    # Define the store credentials for the eORCA025 ERA5v1 NPD data:
    bucket = "npd-eorca025-era5v1"
    for prefix in ["T1y_3d", "T1y_4d", "U1y_3d", "U1y_4d", "V1y_3d", "V1y_4d", "W1y_4d", "I1y_3d", "S1y_1d",
                   "T1m_3d", "T1m_4d", "U1m_3d", "U1m_4d", "V1m_3d", "V1m_4d", "W1m_4d", "I1m_3d", "S1m_1d",
                   "T5d_3d", "T5d_4d", "U5d_3d", "U5d_4d", "V5d_3d", "V5d_4d", "I5d_3d", "S5d_1d",
                   "domain/domain_cfg", "domain/mesh_mask", "domain/subbasins"
                   ]:
        # Open dataset from Icechunk repository:
        ds = open_icechunk_store(bucket=bucket, prefix=prefix, branch="main")

        # Create item with asset for each eORCA025 ERA5v1 NPD prefix:
        if 'domain' in prefix:
            operation = "None None"
        elif '1y' in prefix:
            operation = "annual mean"
        elif '1m' in prefix:
            operation = "monthly mean"
        elif '5d' in prefix:
            operation = "5-day mean"

        item = create_item_with_icechunk_asset(
            id=f"noc-npd-era5/{bucket}/gn/{prefix}",
            ds=ds,
            bucket=bucket,
            platform="gn",
            prefix=prefix,
            config="eORCA025 ERA5v1 NPD",
            operation=operation,
        )
        # Add item to the eORCA025 ERA5v1 NPD global native model grid catalog:
        gn_eorca025_era5v1.add_item(item)

    logging.info(f"Completed: Added Items to NOC STAC Catalog with ID: {gn_eorca025_era5v1.id}")

    # -- Add Items to NOC Near-Present Day eORCA025 ERA5v1 {tn} Sub-Catalog -- #
    # Define the store credentials for the eORCA025 ERA5v1 NPD data:
    for prefix in ["M1m/MOVE_16N", "M1m/SAMBA_34_5S", "M1m/RAPID_26N", "M1m/OSNAP"]:
        # Open dataset from Icechunk repository:
        ds = open_icechunk_store(bucket=bucket, prefix=prefix, branch="main")

        # Create item with asset for each eORCA025 ERA5v1 NPD prefix:
        operation = "monthly mean"
        item = create_item_with_icechunk_asset(
            id=f"noc-npd-era5/{bucket}/tn/{prefix}",
            ds=ds,
            bucket=bucket,
            platform="tn",
            prefix=prefix,
            config="eORCA025 ERA5v1 NPD",
            operation=operation,
        )
        # Add item to the eORCA025 ERA5v1 NPD global native model grid catalog:
        tn_eorca025_era5v1.add_item(item)

    logging.info(f"Completed: Added Items to NOC STAC Catalog with ID: {tn_eorca025_era5v1.id}")

    # -- Add Items to NOC Near-Present Day eORCA12 ERA5v1 Sub-Catalog -- #
    # Define the store credentials for the eORCA12 ERA5v1 NPD data:
    bucket = "npd-eorca12-era5v1"
    for prefix in ["T1y_3d", "T1y_4d", "U1y_3d", "U1y_4d", "V1y_3d", "V1y_4d", "W1y_4d", "I1y_3d", "S1y_1d",
                   "T1m_3d", "T1m_4d", "U1m_3d", "U1m_4d", "V1m_3d", "V1m_4d", "W1m_4d", "I1m_3d", "S1m_1d",
                   "domain/domain_cfg",
                   ]:
        # Open dataset from Icechunk repository:
        ds = open_icechunk_store(bucket=bucket, prefix=prefix, branch="main")

        # Create item with asset for each eORCA12 ERA5v1 NPD prefix:
        if 'domain' in prefix:
            operation = "None None"
        elif '1y' in prefix:
            operation = "annual mean"
        elif '1m' in prefix:
            operation = "monthly mean"
        elif '5d' in prefix:
            operation = "5-day mean"

        item = create_item_with_icechunk_asset(
            id=f"noc-npd-era5/{bucket}/gn/{prefix}",
            ds=ds,
            bucket=bucket,
            platform="gn",
            prefix=prefix,
            config="eORCA12 ERA5v1 NPD",
            operation=operation,
        )
        # Add item to the eORCA12 ERA5v1 NPD global native model grid catalog:
        gn_eorca12_era5v1.add_item(item)

    logging.info(f"Completed: Added Items to NOC STAC Catalog with ID: {gn_eorca12_era5v1.id}")

    # -- Add Items to NOC Near-Present Day eORCA12 ERA5v1 {tn} Sub-Catalog -- #
    # Define the store credentials for the eORCA12 ERA5v1 NPD data:
    for prefix in ["M1m/MOVE_16N", "M1m/SAMBA_34_5S", "M1m/RAPID_26N", "M1m/OSNAP"]:
        # Open dataset from Icechunk repository:
        ds = open_icechunk_store(bucket=bucket, prefix=prefix, branch="main")

        # Create item with asset for each eORCA12 ERA5v1 NPD prefix:
        operation = "monthly mean"
        item = create_item_with_icechunk_asset(
            id=f"noc-npd-era5/{bucket}/tn/{prefix}",
            ds=ds,
            bucket=bucket,
            platform="tn",
            prefix=prefix,
            config="eORCA12 ERA5v1 NPD",
            operation=operation,
        )
        # Add item to the eORCA12 ERA5v1 NPD global native model grid catalog:
        tn_eorca12_era5v1.add_item(item)

    logging.info(f"Completed: Added Items to NOC STAC Catalog with ID: {tn_eorca12_era5v1.id}")

    # -- Add Nested Catalogs to NOC Near-Present Day Collection -- #
    npd_eorca1_era5v1.add_child(gn_eorca1_era5v1)
    npd_eorca025_era5v1.add_child(gn_eorca025_era5v1)
    npd_eorca12_era5v1.add_child(gn_eorca12_era5v1)

    npd_eorca1_era5v1.add_child(tn_eorca1_era5v1)
    npd_eorca025_era5v1.add_child(tn_eorca025_era5v1)
    npd_eorca12_era5v1.add_child(tn_eorca12_era5v1)

    npd_collection.add_child(npd_eorca1_era5v1)
    npd_collection.add_child(npd_eorca025_era5v1)
    npd_collection.add_child(npd_eorca12_era5v1)

    return npd_collection