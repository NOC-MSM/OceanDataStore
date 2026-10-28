"""
rapid_evolution_collection.py

Description:
Function to create the National Oceanography Centre (NOC) 
Rapid Evolution Spatio-Temporal Access Catalog Collection.

Authors:
    - Ollie Tooth (oliver.tooth@noc.ac.uk)
"""
# -- Import Python Modules -- #
import datetime
import logging

import pystac
import xarray as xr

from OceanDataStore.catalog.stac.utils import (
    create_item_with_icechunk_asset,
    create_item_with_zarr_asset,
    open_icechunk_store,
)

logger = logging.getLogger(__name__)


def create_rapid_evo_collection(
    ) -> pystac.Collection:
    """
    Create the NOC Rapid Evolution STAC Collection.
    
    Returns:
    -------
    rapid_evo_collection : pystac.Collection
        NOC Rapid Evolution STAC Collection.
    """
    # -- Define NOC Rapid Evolution Collection -- #
    # Define the spatial extent for the collection:
    spatial_extent = pystac.SpatialExtent(bboxes=[[-180.0, -90.0, 0, 180.0, 90.0, 6000]])

    # Define the current temporal extent for the collection:
    start_datetime = datetime.datetime(year=1976, month=1, day=1, tzinfo=datetime.timezone.utc)
    end_datetime = datetime.datetime(year=2023, month=12, day=31, tzinfo=datetime.timezone.utc)
    start_date_str = start_datetime.strftime("%Y-%m-%d")
    end_date_str = end_datetime.strftime("%Y-%m-%d")
    collection_interval = sorted([start_datetime, end_datetime])
    temporal_extent = pystac.TemporalExtent(intervals=[collection_interval])

    # Define the RAPID-Evolution Collection:
    rapid_evo_collection = pystac.Collection(
        id="noc-rapid-evolution",
        title="NOC RAPID-Evolution Collection",
        description="**About:**\n\nCollection of nested ocean model simulations produced by the National Oceanography Centre (NOC) as part of the CCROC RAPID-Evolution project delivered through a partnership between UK (National Oceanography Centre, Met Office) and US (University of Miami and NOAA's AOML).\n\n**More Information:**\n - [RAPID-Evolution](https://rapid.ac.uk/rapid-evolution)",
        extent=pystac.Extent(spatial=spatial_extent, temporal=temporal_extent),
        # Open Government License (OGL) - UK version 3.0 - http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
        license="OGL-UK-3.0",
        extra_fields={"contact": "Adam Blaker (atb299@noc.ac.uk)",
                      "project": "RAPID-Evolution",
                      "status": "complete",
                      "last_data_update": end_date_str
                      },
        keywords=["NOC", "Rapid Evolution", "hindcast", "global", "nested", "model", "ocean", "sea-ice"],
        providers=[
            pystac.Provider(
                name="National Oceanography Centre (NOC)",
                description="National Oceanography Centre (United Kingdom) - Ocean Modelling Group.",
                roles=[pystac.ProviderRole.PRODUCER, pystac.ProviderRole.LICENSOR],
                url="https://rapid.ac.uk/rapid-evolution"
            ),
            pystac.Provider(
                name="JASMIN",
                description="JASMIN Environmental Data Analysis Facility (United Kingdom).",
                roles=[pystac.ProviderRole.HOST],
                url="https://jasmin.ac.uk"
            )
        ],
    )

    logger.info(f"Completed: Created STAC Collection: {rapid_evo_collection}")

    # ==== Define NOC RAPID Evolution Model Simulations Catalogs ==== #
    r_evo_eorca025_jra55 = pystac.Catalog(
        id="r-evo-eorca025-jra55",
        title="eORCA025 JRA55-do RAPID-Evolution Catalog",
        description="Catalog of eORCA025 JRA55-do RAPID-Evolution nested ocean sea-ice simulations performed by the National Oceanography Centre."
        )
    logger.info(f"-> Completed: Created STAC Catalog with ID: {r_evo_eorca025_jra55.id}")

    # ==== Define NOC RAPID Evolution Variant Catalogs ==== #
    r1i1c1f1_rapid_evo = pystac.Catalog(
        id="r1i1c1f1",
        title="NOC RAPID-Evolution: r1i1c1f1 Catalog",
        description="Catalog of RAPID-Evolution nested ocean physics & sea-ice outputs for model variant: r1i1c1f1.\n\n**Variant Label:**\n\nRealisation=1, Initialisation=1, Configuration=1, Forcing=1."
        )

    logger.info(f"-> Completed: Created STAC Catalog with ID: {r1i1c1f1_rapid_evo.id}")

    # -- NOC RAPID Evolution Nested NEMODataTree Icechunk Repository -- #
    # Define endpoint url for RAPID-Evolution data:
    endpoint_url="https://rapidevolution-o.s3-ext.jc.rl.ac.uk"

    # Add root group for hierarchical Icechunk repository:
    bucket = "rapid-evolution"
    ds = open_icechunk_store(bucket=bucket, prefix="rapid-evo1-1m", branch="main", endpoint_url=endpoint_url)
    item = create_item_with_icechunk_asset(
        ds=ds,
        id=f"noc-rapid-evolution/r-evo-eorca025-jra55/{ds.attrs.get('variant', 'r1i1c1f1')}/rapid-evo1-1m",
        bucket=bucket,
        prefix="rapid-evo1-1m",
        title="RAPID-Evolution eORCA025 JRA55-do Nested NEMODataTree",
        description="**Monthly-mean ocean outputs from the eORCA025 global parent domain, RAPID12 regional nested child domain, and RAPID36 regional nested grandchild domain.**",
        start_date=start_date_str,
        end_date=end_date_str,
        collection="noc-rapid-evolution",
        endpoint_url=endpoint_url,
        )
    # Add item to the RAPID-Evolution monthly-mean nested NEMODataTree:
    r1i1c1f1_rapid_evo.add_item(item)

    # Add individual parent domain groups in hierarchical Icechunk repository:
    for prefix in ["T1m_parent", "U1m_parent", "V1m_parent", "W1m_parent", "F1m_parent"]:
        # Open dataset from Icechunk repository:
        group = f"grid{prefix[0]}"
        ds = open_icechunk_store(bucket=bucket, prefix="rapid-evo1-1m", branch="main", group=group, endpoint_url=endpoint_url)

        if "time_counter" in ds:
            item = create_item_with_icechunk_asset(
                ds=ds,
                id=f"noc-rapid-evolution/r-evo-eorca025-jra55/{ds.attrs.get('variant', 'r1i1c1f1')}/{prefix}",
                bucket=bucket,
                prefix="rapid-evo1-1m",
                title=f"RAPID-Evolution eORCA025 NEMODataTree {prefix[0]}-grid parent node",
                description=f"**Monthly-mean eORCA025 global parent domain ocean {'scalar' if prefix[0] == 'T' else 'vector'} outputs defined at {prefix[0]}-points.**",
                collection="noc-rapid-evolution",
                group=group,
                endpoint_url=endpoint_url,
                )
            # Add item to the RAPID-Evolution monthly-mean nested NEMODataTree:
            r1i1c1f1_rapid_evo.add_item(item)

    # Add individual child domain groups in hierarchical Icechunk repository:
    for prefix in ["T1m_child", "U1m_child", "V1m_child", "W1m_child", "F1m_child"]:
        # Open dataset from Icechunk repository:
        group = f"grid{prefix[0]}/1_grid{prefix[0]}"
        ds = open_icechunk_store(bucket=bucket, prefix="rapid-evo1-1m", branch="main", group=group, endpoint_url=endpoint_url)

        if "time_counter" in ds:
            item = create_item_with_icechunk_asset(
                ds=ds,
                id=f"noc-rapid-evolution/r-evo-eorca025-jra55/{ds.attrs.get('variant', 'r1i1c1f1')}/{prefix}",
                bucket=bucket,
                prefix="rapid-evo1-1m",
                title=f"RAPID-Evolution RAPID12 NEMODataTree {prefix[0]}-grid child node",
                description=f"**Monthly-mean RAPID12 regional nested child domain ocean {'scalar' if prefix[0] == 'T' else 'vector'} outputs defined at {prefix[0]}-points.**",
                collection="noc-rapid-evolution",
                group=group,
                endpoint_url=endpoint_url,
                )
            # Add item to the RAPID-Evolution monthly-mean nested NEMODataTree:
            r1i1c1f1_rapid_evo.add_item(item)

    # Add individual grandchild domain groups in hierarchical Icechunk repository:
    for prefix in ["T1m_grandchild", "U1m_grandchild", "V1m_grandchild", "W1m_grandchild", "F1m_grandchild"]:
        # Open dataset from Icechunk repository:
        group = f"grid{prefix[0]}/1_grid{prefix[0]}/2_grid{prefix[0]}"
        ds = open_icechunk_store(bucket=bucket, prefix="rapid-evo1-1m", branch="main", group=group, endpoint_url=endpoint_url)

        if "time_counter" in ds:
            item = create_item_with_icechunk_asset(
                ds=ds,
                id=f"noc-rapid-evolution/r-evo-eorca025-jra55/{ds.attrs.get('variant', 'r1i1c1f1')}/{prefix}",
                bucket=bucket,
                prefix="rapid-evo1-1m",
                title=f"RAPID-Evolution RAPID36 NEMODataTree {prefix[0]}-grid grandchild node",
                description=f"**Monthly-mean RAPID36 regional nested grandchild domain ocean {'scalar' if prefix[0] == 'T' else 'vector'} outputs defined at {prefix[0]}-points.**",
                collection="noc-rapid-evolution",
                group=group,
                endpoint_url=endpoint_url
                )
            # Add item to the RAPID-Evolution monthly-mean nested NEMODataTree:
            r1i1c1f1_rapid_evo.add_item(item)

    logger.info(f"-> Completed: Added Items to STAC Catalog with ID: {rapid_evo_collection.id}/{r_evo_eorca025_jra55.id}/{r1i1c1f1_rapid_evo.id}")

    # -- NOC RAPID-Evolution domain_cfg Zarr Stores -- #
    # Define bucket for RAPID-Evolution ancillary data:
    bucket="rapid-evolution-ancillaries"
    operation = "None None"

    # Open eORCA025 parent domain_cfg dataset from Zarr store:
    ds = xr.open_zarr(f"{endpoint_url}/{bucket}/eORCA025_domain_cfg", consolidated=True)
    item = create_item_with_zarr_asset(
        id="noc-rapid-evolution/r-evo-eorca025-jra55/eorca025_domain_cfg",
        ds=ds,
        bucket=bucket,
        platform="gn",
        prefix="eORCA025_domain_cfg",
        title="RAPID-Evolution eORCA025 domain_cfg",
        horizontal_grid_resolution="1/4 degree",
        start_date=start_date_str,
        end_date=end_date_str,
        collection="noc-rapid-evolution",
        operation=operation,
        endpoint_url=endpoint_url,
        zarr_format=3,
    )
    # Add Item to RAPID Evolution Collection:
    r1i1c1f1_rapid_evo.add_item(item)

    # Open RAPID12 child domain_cfg dataset from Zarr store:
    ds = xr.open_zarr(f"{endpoint_url}/{bucket}/eORCA025_RAPID12_domain_cfg", consolidated=True)
    item = create_item_with_zarr_asset(
        id="noc-rapid-evolution/r-evo-eorca025-jra55/rapid12_domain_cfg",
        ds=ds,
        bucket=bucket,
        platform="gn",
        prefix="eORCA025_RAPID12_domain_cfg",
        title="RAPID-Evolution RAPID12 domain_cfg",
        horizontal_grid_resolution="1/12 degree",
        start_date=start_date_str,
        end_date=end_date_str,
        bbox=(-100.143814, 6.0719233, -1.8753614, 42.41955),
        collection="noc-rapid-evolution",
        operation=operation,
        endpoint_url=endpoint_url,
        zarr_format=3,
    )
    # Add Item to RAPID Evolution Collection:
    r1i1c1f1_rapid_evo.add_item(item)

    # Open RAPID36 grandchild domain_cfg dataset from Zarr store:
    ds = xr.open_zarr(f"{endpoint_url}/{bucket}/eORCA025_RAPID36_domain_cfg", consolidated=True)
    item = create_item_with_zarr_asset(
        id="noc-rapid-evolution/r-evo-eorca025-jra55/rapid36_domain_cfg",
        ds=ds,
        bucket=bucket,
        platform="gn",
        prefix="eORCA025_RAPID36_domain_cfg",
        title="RAPID-Evolution RAPID36 domain_cfg",
        horizontal_grid_resolution="1/36 degree",
        start_date=start_date_str,
        end_date=end_date_str,
        bbox=(-98.530975, 17.34014, -8.879465, 30.447763),
        collection="noc-rapid-evolution",
        operation=operation,
        endpoint_url=endpoint_url,
        zarr_format=3,
    )
    # Add Item to RAPID Evolution Collection:
    r1i1c1f1_rapid_evo.add_item(item)

    logger.info(f"Completed: Added RAPID Evolution domain_cfg Items to STAC Catalog: {rapid_evo_collection.id}/{r_evo_eorca025_jra55.id}/{r1i1c1f1_rapid_evo.id}")

    # ==== Add Nested Catalogs to NOC RAPID Evolution Collection ==== #

    # Model Simulation Variant Catalogs -> Model Simulation Catalogs:
    r_evo_eorca025_jra55.add_child(r1i1c1f1_rapid_evo)

    # Model Simulation Catalogs -> RAPID Evolution Collection:
    rapid_evo_collection.add_child(r_evo_eorca025_jra55)\

    return rapid_evo_collection