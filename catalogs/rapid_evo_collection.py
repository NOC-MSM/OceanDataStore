"""
rapid_evolution_collection.py

Description:
Function to create the National Oceanography Centre (NOC) 
Rapid Evolution Spatio-Temporal Access Catalog Collection.

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

from utils import  create_item_with_zarr_asset

def create_rapid_evo_collection(
    credentials_json: str = "/dssgfs01/working/otooth/AtlantiS/jasmin_os/credentials/rapid_evo_credentials.json"
    ) -> pystac.Collection:
    """
    Create the NOC Rapid Evolution STAC Collection.

    Parameters:
    ----------
    credentials_json : str
        Path to the JSON file containing the credentials for the S3 object store.
    
    Returns:
    -------
    rapid_evo_collection : pystac.Collection
        NOC Rapid Evolution STAC Collection.
    """
    # -- Initialise Object Store -- #
    obj_store = ObjectStoreS3(anon=False,
                              asynchronous=False,
                              store_credentials_json=credentials_json
                              )

    # Define list of variable Zarr stores to exclude from the STAC item creation:
    exclude_vars = ['depthu_bounds', 'depthv_bounds', 'depthw_bounds', 'deptht_bounds', 'time_counter_bounds', 'time_centered_bounds']

    # -- Define NOC Rapid Evolution Collection -- #
    # Define the spatial extent for the collection:
    spatial_extent = pystac.SpatialExtent(bboxes=[[-180.0, -90.0, 0, 180.0, 90.0, 6000]])

    # Define the current temporal extent for the collection:
    collection_interval = sorted([datetime.datetime(year=1976, month=1, day=1), datetime.datetime(year=2024, month=12, day=31)])
    temporal_extent = pystac.TemporalExtent(intervals=[collection_interval])

    # Define the RAPID-Evolution Collection:
    rapid_evo_collection = pystac.Collection(
        id="noc-rapid-evolution",
        title="NOC RAPID-Evolution Collection",
        description="Collection of nested ocean model simulations produced by the National Oceanography Centre (NOC) as part of the CCROC RAPID-Evolution project delivered through a partnership between UK (National Oceanography Centre, Met Office) and US (University of Miami and NOAA's AOML).",
        extent=pystac.Extent(spatial=spatial_extent, temporal=temporal_extent),
        # Open Government License (OGL) - UK version 3.0 - http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
        license="OGL-UK-3.0",
        extra_fields=dict(contact="Adam Blaker (atb299@noc.ac.uk)", project="RAPID-Evolution", status="complete", last_data_update="2025-05-30"),
        keywords=["NOC", "Rapid Evolution", "hindcast", "global", "nested", "model", "ocean", "sea-ice"],
        providers=[
            pystac.Provider(
                name="National Oceanography Centre",
                description="National Oceanography Centre (United Kindom) - Marine Systems Modelling group.",
                roles=[pystac.ProviderRole.PRODUCER, pystac.ProviderRole.LICENSOR],
                url="https://rapid.ac.uk/rapid-evolution"
            ),
            pystac.Provider(
                name="JASMIN",
                description="JASMIN environmental data analysis facility (United Kindgom).",
                roles=[pystac.ProviderRole.HOST],
                url="https://jasmin.ac.uk"
            )
        ],
    )

    logging.info(f"Completed: Created NOC STAC Collection with ID: {rapid_evo_collection.id}")

    # -- Define NOC RAPID-Evolution Model Configuration Catalogs -- #
    r_evo_eorca025 = pystac.Catalog(
        id="noc-rapid-evolution/r_evo_eorca025",
        title="eORCA025 RAPID-Evolution global parent domain Catalog",
        description="Catalog of eORCA025 JRA55-do global parent domain outputs from the RAPID-Evolution ocean physics simulation performed by the National Oceanography Centre."
    )

    logging.info(f"Completed: Created NOC STAC Catalog with ID: {r_evo_eorca025.id}")

    r_evo_rapid12 = pystac.Catalog(
        id="noc-rapid-evolution/r_evo_rapid12",
        title="RAPID12 RAPID-Evolution nested child domain Catalog",
        description="Catalog of RAPID12 JRA55-do nested child domain outputs from the RAPID-Evolution ocean physics simulation performed by the National Oceanography Centre.",
    )

    logging.info(f"Completed: Created NOC STAC Catalog with ID: {r_evo_rapid12.id}")

    r_evo_rapid36 = pystac.Catalog(
        id="noc-rapid-evolution/r_evo_rapid36",
        title="RAPID36 RAPID-Evolution nested grandchild domain Catalog",
        description="Catalog of RAPID36 JRA55-do nested grandchild domain outputs from the RAPID-Evolution ocean physics simulation performed by the National Oceanography Centre.",
    )

    logging.info(f"Completed: Created NOC STAC Catalog with ID: {r_evo_rapid36.id}")

    # Define NOC RAPID-Evolution Platform Sub-Catalogs -- #
    # Note: Options for platforms are: "gn_global", "gr_global", "gn_regional{1...4}", "gr_regional{1...4}", "tn", "tr".
    # where gn = global native model grids, gr = global regridded grids, tn = transects on native model grids, tr = transects on regridded grids.

    gn_eorca025 = pystac.Catalog(
        id="noc-rapid-evolution/r_evo_eorca025/gn_global",
        title="RAPID12 JRA55-do global parent domain native model grid Catalog",
        description="Catalog of global ocean physics outputs stored on the native global eORCA025 curvilinear model grid."
        )

    logging.info(f"Completed: Created NOC STAC Nested Catalog with ID: {gn_eorca025.id}")

    gn_rapid12 = pystac.Catalog(
        id="noc-rapid-evolution/r_evo_rapid12/gn_nest",
        title="RAPID12 JRA55-do nested child domain native model grid Catalog",
        description="Catalog of ocean physics outputs stored on the native nested RAPID12 curvilinear model grid."
        )

    logging.info(f"Completed: Created NOC STAC Nested Catalog with ID: {gn_rapid12.id}")

    gn_rapid36 = pystac.Catalog(
        id="noc-rapid-evolution/r_evo_rapid36/gn_nest",
        title="RAPID36 JRA55-do nested grandchild domain native model grid Catalog",
        description="Catalog of ocean physics outputs stored on the native nested RAPID36 curvilinear model grid."
        )

    logging.info(f"Completed: Created NOC STAC Nested Catalog with ID: {gn_rapid36.id}")

    # -- Add Items to NOC RAPID-Evolution eORCA025 global parent Sub-Catalog -- #
    # Define url for eORCA025 RAPID-Evolution data:
    endpoint_url="https://rapidevolution-o.s3-ext.jc.rl.ac.uk"

    for prefix in ["T1m", "U1m", "V1m", "W1m", "S1m", "eORCA025_domain_cfg"]:
        # Create item with asset for each eORCA025 global parent RAPID-Evolution prefix:
        if 'domain' in prefix:
            operation = "None None"
            bucket="rapid-evolution-ancillaries"

            # Open domain_cfg dataset from Zarr store:
            ds = xr.open_zarr(f"{endpoint_url}/{bucket}/{prefix}", consolidated=True)
            item = create_item_with_zarr_asset(
                ds=ds,
                bucket=bucket,
                platform="gn_global",
                prefix=prefix,
                start_date="1976-01-16",
                end_date="2023-12-16",
                collection="noc-rapid-evolution",
                config="eORCA025 RAPID-Evolution global parent",
                operation=operation,
                endpoint_url=endpoint_url,
                zarr_format=3,
            )
            # Add item to the eORCA025 RAPID-Evolution global parent domain native model grid catalog:
            gn_eorca025.add_item(item)
        
        else:
            bucket="r-evo1-eorca025-rapid12-rapid36"
            prefix = f"eORCA025/{prefix}"

            if '1y' in prefix:
                operation = "annual mean"
            elif '1m' in prefix:
                operation = "monthly mean"

            # Get variable Zarr stores from JASMIN object store:
            var_stores = [path.split("/")[-1] for path in obj_store.ls(f"{bucket}/{prefix}") if path.split("/")[-1] not in exclude_vars]

            # Create STAC Item for each variable Zarr store:
            logging.info(f"In Progress: Adding {prefix} Items...")
            for var in tqdm(var_stores):
                # Open dataset from Zarr store:
                ds = xr.open_zarr(f"{endpoint_url}/{bucket}/{prefix}/{var}", consolidated=True)
                item = create_item_with_zarr_asset(
                    ds=ds,
                    bucket=bucket,
                    platform="gn_global",
                    prefix=f"{prefix}/{var}",
                    start_date="1976-01-16",
                    end_date="2023-12-16",
                    collection="noc-rapid-evolution",
                    config="eORCA025 RAPID-Evolution global parent",
                    operation=operation,
                    endpoint_url=endpoint_url,
                    zarr_format=3,
                )
                # Add item to the eORCA025 RAPID-Evolution global parent domain native model grid catalog:
                gn_eorca025.add_item(item)

    logging.info(f"Completed: Added Items to NOC STAC Catalog with ID: {gn_eorca025.id}")

    # -- Add Items to NOC RAPID-Evolution RAPID12 nested child domain Sub-Catalog -- #
    for prefix in ["T1m", "U1m", "V1m", "W1m", "S1m", "eORCA025_RAPID12_domain_cfg"]:
        # Create item with asset for each RAPID12 nested child domain prefix:
        if 'domain' in prefix:
            operation = "None None"
            bucket="rapid-evolution-ancillaries"

            # Open domain_cfg dataset from Zarr store:
            ds = xr.open_zarr(f"{endpoint_url}/{bucket}/{prefix}", consolidated=True)
            item = create_item_with_zarr_asset(
                ds=ds,
                bucket=bucket,
                platform="gn_nest",
                prefix=prefix,
                start_date="1976-01-16",
                end_date="2023-12-16",
                bbox=(-100.143814, 6.0719233, -1.8753614, 42.41955),
                collection="noc-rapid-evolution",
                config="RAPID12 RAPID-Evolution child nest",
                operation=operation,
                endpoint_url=endpoint_url,
                zarr_format=3,
            )
            # Add item to the RAPID12 RAPID-Evolution nested child domain native model grid catalog:
            gn_eorca025.add_item(item)
        
        else:
            bucket="r-evo1-eorca025-rapid12-rapid36"
            prefix = f"RAPID12/{prefix}"
            if '1y' in prefix:
                operation = "annual mean"
            elif '1m' in prefix:
                operation = "monthly mean"

            # Get variable Zarr stores from JASMIN object store:
            var_stores = [path.split("/")[-1] for path in obj_store.ls(f"{bucket}/{prefix}") if path.split("/")[-1] not in exclude_vars]

            # Create STAC Item for each variable Zarr store:
            logging.info(f"In Progress: Adding {prefix} Items...")
            for var in tqdm(var_stores):
                # Open dataset from Zarr store:
                ds = xr.open_zarr(f"{endpoint_url}/{bucket}/{prefix}/{var}", consolidated=True)
                item = create_item_with_zarr_asset(
                    ds=ds,
                    bucket=bucket,
                    platform="gn_nest",
                    prefix=f"{prefix}/{var}",
                    start_date="1976-01-16",
                    end_date="2023-12-16",
                    bbox=(-100.143814, 6.0719233, -1.8753614, 42.41955),
                    collection="noc-rapid-evolution",
                    config="RAPID12 RAPID-Evolution child nest",
                    operation=operation,
                    endpoint_url=endpoint_url,
                    zarr_format=3,
                )
                # Add item to the RAPID12 RAPID-Evolution nested child domain native model grid catalog:
                gn_rapid12.add_item(item)

    logging.info(f"Completed: Added Items to NOC STAC Catalog with ID: {gn_rapid12.id}")

    # -- Add Items to NOC RAPID-Evolution RAPID36 nested grandchild domain Sub-Catalog -- #
    for prefix in ["T1m", "U1m", "V1m", "W1m", "S1m", "eORCA025_RAPID36_domain_cfg"]:
        # Create item with asset for each RAPID36 nested grandchild domain prefix:
        if 'domain' in prefix:
            operation = "None None"
            bucket="rapid-evolution-ancillaries"

            # Open domain_cfg dataset from Zarr store:
            ds = xr.open_zarr(f"{endpoint_url}/{bucket}/{prefix}", consolidated=True)
            item = create_item_with_zarr_asset(
                ds=ds,
                bucket=bucket,
                platform="gn_nest",
                prefix=prefix,
                start_date="1976-01-16",
                end_date="2023-12-16",
                bbox=(-98.530975, 17.34014, -8.879465, 30.447763),
                collection="noc-rapid-evolution",
                config="RAPID36 RAPID-Evolution grandchild nest",
                operation=operation,
                endpoint_url=endpoint_url,
                zarr_format=3,
            )
            # Add item to the RAPID36 RAPID-Evolution nested grandchild domain native model grid catalog:
            gn_eorca025.add_item(item)
        
        else:
            bucket="r-evo1-eorca025-rapid12-rapid36"
            prefix = f"RAPID36/{prefix}"
            if '1y' in prefix:
                operation = "annual mean"
            elif '1m' in prefix:
                operation = "monthly mean"

            # Get variable Zarr stores from JASMIN object store:
            var_stores = [path.split("/")[-1] for path in obj_store.ls(f"{bucket}/{prefix}") if path.split("/")[-1] not in exclude_vars]

            # Create STAC Item for each variable Zarr store:
            logging.info(f"In Progress: Adding {prefix} Items...")
            for var in tqdm(var_stores):
                # Open dataset from Zarr store:
                ds = xr.open_zarr(f"{endpoint_url}/{bucket}/{prefix}/{var}", consolidated=True)
                item = create_item_with_zarr_asset(
                    ds=ds,
                    bucket=bucket,
                    platform="gn_nest",
                    start_date="1976-01-16",
                    end_date="2023-12-16",
                    prefix=f"{prefix}/{var}",
                    bbox=(-98.530975, 17.34014, -8.879465, 30.447763),
                    collection="noc-rapid-evolution",
                    config="RAPID36 RAPID-Evolution grandchild nest",
                    operation=operation,
                    endpoint_url=endpoint_url,
                    zarr_format=3,
                )
                # Add item to the RAPID36 RAPID-Evolution nested grandchild domain native model grid catalog:
                gn_rapid36.add_item(item)

    logging.info(f"Completed: Added Items to NOC STAC Catalog with ID: {gn_rapid36.id}")

    # -- Add Nested Catalogs to NOC RAPID-Evolution Collection -- #
    r_evo_eorca025.add_child(gn_eorca025)
    r_evo_rapid12.add_child(gn_rapid12)
    r_evo_rapid36.add_child(gn_rapid36)

    rapid_evo_collection.add_child(r_evo_eorca025)
    rapid_evo_collection.add_child(r_evo_rapid12)
    rapid_evo_collection.add_child(r_evo_rapid36)

    return rapid_evo_collection