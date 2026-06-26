"""
npd_jra55v1_collection.py

Description:
Function to create the National Oceanography Centre (NOC) 
Near-Present Day JRA55-do version 1 Spatio-Temporal Access
Catalog Collection.

Authors:
    - Ollie Tooth (oliver.tooth@noc.ac.uk)
"""
# -- Import Python Modules -- #
import logging
import pystac
import datetime
import xarray as xr

from OceanDataStore.catalog.stac.utils import create_item_with_zarr_asset


def create_npd_jra55_collection(
    ) -> pystac.Collection:
    """
    Create the NOC Near-Present Day JRA55-do version 1 STAC Collection.
    
    Returns:
    -------
    npd_collection : pystac.Collection
        NOC Near-Present Day JRA55-do version 1 STAC Collection.
    """
    # -- Define NOC Near-Present Day JRA55-do Collection -- #
    # Define the spatial extent for the collection:
    spatial_extent = pystac.SpatialExtent(bboxes=[[-180.0, -90.0, 0, 180.0, 90.0, 6000]])

    # Define the current temporal extent for the collection:
    collection_interval = sorted([datetime.datetime(year=1976, month=1, day=1), datetime.datetime(year=2024, month=2, day=1)])
    temporal_extent = pystac.TemporalExtent(intervals=[collection_interval])

    # Define the Near-Present Day Collection:
    npd_collection = pystac.Collection(
        id="noc-npd-jra55",
        title="NOC Near-Present Day JRA55-do Collection",
        description="**About:**\n\nCollection of multi-decadal Near-Present Day ocean model hindcast simulations produced by the National Oceanography Centre (NOC) using JRA55-do atmospheric forcing as part of the Atlantic Climate and Environment Strategic Science (AtlantiS) programme.\n\n**More Information:**\n - [AtlantiS](https://atlantis.ac.uk)\n - [NOC Near-Present Day](https://noc-msm.github.io/NOC_Near_Present_Day/)",
        extent=pystac.Extent(spatial=spatial_extent, temporal=temporal_extent),
        # Open Government License (OGL) - UK version 3.0 - http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
        license="OGL-UK-3.0",
        extra_fields=dict(contact="Ollie Tooth (oliver.tooth@noc.ac.uk)", project="AtlantiS", status="completed", last_data_update="2025-05-30"),
        keywords=["NOC", "JRA55-do", "Near-Present Day", "AtlantiS", "hindcast", "global", "model", "ocean", "sea-ice"],
        providers=[
            pystac.Provider(
                name="National Oceanography Centre (NOC)",
                description="National Oceanography Centre (United Kingdom) - Ocean Modelling Group.",
                roles=[pystac.ProviderRole.PRODUCER, pystac.ProviderRole.LICENSOR],
                url="https://noc-msm.github.io/NOC_Near_Present_Day/"
            ),
            pystac.Provider(
                name="JASMIN",
                description="JASMIN Environmental Data Analysis Facility (United Kingdom).",
                roles=[pystac.ProviderRole.HOST],
                url="https://jasmin.ac.uk"
            )
        ],
    )

    logging.info(f"Completed: Created NOC STAC Collection with ID: {npd_collection.id}")

    # ==== Define NOC Near-Present Day Model Simulations Catalogs ==== #
    npd_eorca1_jra55v1 = pystac.Catalog(
        id="npd-eorca1-jra55v1",
        title="eORCA1 JRA55v1 NPD Catalog",
        description="Catalog of eORCA1 JRA55-do Near-Present Day ocean sea-ice simulations performed by the National Oceanography Centre."
        )

    logging.info(f"Completed: Created STAC Catalog with ID: {npd_eorca1_jra55v1.id}")

    npd_eorca025_jra55v1 = pystac.Catalog(
        id="npd-eorca025-jra55v1",
        title="eORCA025 JRA55v1 NPD Catalog",
        description="Catalog of eORCA025 JRA55-do Near-Present Day ocean sea-ice simulations performed by the National Oceanography Centre.",
        )

    logging.info(f"Completed: Created STAC Catalog with ID: {npd_eorca025_jra55v1.id}")

    # ==== Define NOC Near-Present Day Model Variant Catalogs ==== #
    r1i1c1f1_eorca1_jra55v1 = pystac.Catalog(
        id="r1i1c1f1",
        title="eORCA1 JRA55v1 NPD: r1i1c1f1 Catalog",
        description="Catalog of eORCA1 JRA55-do Near-Present Day ocean physics & sea-ice outputs for model variant: r1i1c1f1.\n\n**Variant Label:**\n\nRealisation=1, Initialisation=1, Configuration=1, Forcing=1."
        )

    logging.info(f"Completed: Created STAC Catalog with ID: {r1i1c1f1_eorca1_jra55v1.id}")

    r1i1c1f1_eorca025_jra55v1 = pystac.Catalog(
        id="r1i1c1f1",
        title="eORCA025 JRA55v1 NPD: r1i1c1f1 Catalog",
        description="Catalog of eORCA025 JRA55-do Near-Present Day ocean physics & sea-ice outputs for model variant: r1i1c1f1.\n\n**Variant Label:**\n\nRealisation=1, Initialisation=1, Configuration=1, Forcing=1.",
        )

    logging.info(f"Completed: Created STAC Catalog with ID: {r1i1c1f1_eorca025_jra55v1.id}")

    # -- Add Items to NOC Near-Present Day eORCA1 JRA55v1 {gn} Sub-Catalog -- #
    # Define url & bucket for eORCA1 JRA55v1 NPD data:
    endpoint_url="https://noc-msm-o.s3-ext.jc.rl.ac.uk"
    bucket="npd-eorca1-jra55v1"
    variant="r1i1c1f1"

    for prefix in ["T1y", "U1y", "V1y", "W1y", "I1y", "S1y", "T1m", "U1m", "V1m", "W1m", "I1m", "S1m",
                   "domain_cfg"
                   ]:
        # Open dataset from Zarr store:
        ds = xr.open_zarr(f"{endpoint_url}/{bucket}/{prefix}")

        # Create item with asset for each eORCA1 JRA55v1 NPD prefix:
        if 'domain' in prefix:
            operation = "None None"
        elif '1y' in prefix:
            operation = "annual mean"
        elif '1m' in prefix:
            operation = "monthly mean"
        elif '5d' in prefix:
            operation = "5-day mean"

        item = create_item_with_zarr_asset(
            id=f"noc-npd-jra55/{bucket}/{variant}/{prefix}",
            ds=ds,
            bucket=bucket,
            prefix=prefix,
            title=f"NPD eORCA1 JRA55v1 {prefix}",
            platform="gn",
            horizontal_grid_resolution="1 degree",
            variant=variant,
            start_date="1976-01-01",
            end_date="2024-01-31",
            operation=operation,
            zarr_format=3,
            variable_stores=False,
        )
        # Add item to the eORCA1 JRA55v1 NPD global native model grid catalog:
        r1i1c1f1_eorca1_jra55v1.add_item(item)

    logging.info(f"Completed: Added Items to STAC Catalog with ID: {r1i1c1f1_eorca1_jra55v1.id}")

    # -- Add Items to NOC Near-Present Day eORCA025 JRA55v1 {gn} Sub-Catalog -- #
    # Define url & bucket for eORCA025 JRA55v1 NPD data:
    endpoint_url="https://noc-msm-o.s3-ext.jc.rl.ac.uk"
    bucket="npd-eorca025-jra55v1"
    variant="r1i1c1f1"

    for prefix in ["T1y_3d", "T1y_4d", "U1y_3d", "U1y_4d", "V1y_3d", "V1y_4d", "W1y_4d", "I1y_3d", "S1y_1d",
                   "T1m_3d", "T1m_4d", "U1m_3d", "U1m_4d", "V1m_3d", "V1m_4d", "W1m_4d", "I1m_3d", "S1m_1d",
                   "domain_cfg"
                   ]:
        # Open dataset from Zarr store:
        ds = xr.open_zarr(f"{endpoint_url}/{bucket}/{prefix}")

        # Create item with asset for each eORCA025 JRA55v1 NPD prefix:
        if 'domain' in prefix:
            operation = "None None"
        elif '1y' in prefix:
            operation = "annual mean"
        elif '1m' in prefix:
            operation = "monthly mean"
        elif '5d' in prefix:
            operation = "5-day mean"

        item = create_item_with_zarr_asset(
            id=f"noc-npd-jra55/{bucket}/{variant}/{prefix}",
            ds=ds,
            bucket=bucket,
            prefix=prefix,
            title=f"NPD eORCA025 JRA55v1 {prefix}",
            platform="gn",
            horizontal_grid_resolution="1/4 degree",
            variant=variant,
            start_date="1976-01-01",
            end_date="2024-01-31",
            operation=operation,
            zarr_format=3,
            variable_stores=False
        )
        # Add item to the eORCA025 JRA55v1 NPD global native model grid catalog:
        r1i1c1f1_eorca025_jra55v1.add_item(item)

    logging.info(f"Completed: Added Items to STAC Catalog with ID: {r1i1c1f1_eorca025_jra55v1.id}")

    # ==== Add Nested Catalogs to NOC Near-Present Day Collection ==== #

    # Model Simulation Variant Catalogs -> Model Simulation Catalogs:
    npd_eorca1_jra55v1.add_child(r1i1c1f1_eorca1_jra55v1)
    npd_eorca025_jra55v1.add_child(r1i1c1f1_eorca025_jra55v1)

    # Model Simulation Catalogs -> Near-Present Day Collection:
    npd_collection.add_child(npd_eorca1_jra55v1)
    npd_collection.add_child(npd_eorca025_jra55v1)

    return npd_collection
