"""
template_collections.py

Description:
Template Function to create Spatio-Temporal Access Catalog Collections
for ocean observation datasets.

Authors:
    - Ollie Tooth (oliver.tooth@noc.ac.uk)
"""
# -- Import Python Modules -- #
import logging
import pystac
import datetime

from OceanDataStore.catalog.stac.utils import open_icechunk_store, create_item_with_icechunk_asset


def create_example_collection() -> pystac.Collection:
    """
    Create an example STAC Collection from an Icechunk repository
    stored in the JASMIN cloud object store.
    
    Returns:
    -------
    example_collection : pystac.Collection
        Example STAC Collection.

    """
    # ==== Define Example Collection ==== #
    # Define the spatial extent for the collection - this is the maximum extent of all datasets in the collection:
    spatial_extent = pystac.SpatialExtent(bboxes=[[-180.0, -90.0, 180.0, 90.0]])

    # Define the current temporal extent for the collection - this is the maximum temporal extent of all datasets in the collection:
    collection_interval = sorted([datetime.datetime(year=1975, month=1, day=1), datetime.datetime(year=2026, month=6, day=1)])
    temporal_extent = pystac.TemporalExtent(intervals=[collection_interval])

    # Define PySTAC Collection:
    example_collection = pystac.Collection(
        id="example",
        title="Example STAC Collection",
        description="**About:**\n\nExample STAC Collection from an Icechunk repository.\n\n**More Information:**\n - [Source](https://link-to-source.com)",
        extent=pystac.Extent(spatial=spatial_extent, temporal=temporal_extent),
        license="License String", # For example, UK Open Government License v3.0
        extra_fields=dict(contact="Name (email)", project="project_name", status="ongoing / completed", update_frequency="monthly/quarterly/annually", last_data_update="YYYY-MM-DD"),
        keywords=["SOURCE", "global / arctic / antarctic", "model / observation", "temperature / salinity / sea ice concentration"],
        providers=[
            pystac.Provider(
                name="National Oceanography Centre",
                description="National Oceanography Centre (NOC), United Kingdom.",
                roles=[pystac.ProviderRole.PRODUCER, pystac.ProviderRole.LICENSOR],
                url="https://www.noc.ac.uk"
            ),
            pystac.Provider(
                name="JASMIN",
                description="JASMIN Environmental Data Analysis Facility (United Kingdom).",
                roles=[pystac.ProviderRole.HOST],
                url="https://jasmin.ac.uk"
            )
        ],
    )

    logging.info(f"Completed: Created STAC Collection with ID: {example_collection.id}")

    # -- Add Items to Example STAC Collection -- #
    bucket = "bucket_name"
    for prefix in ["example_dataset_1", "example_dataset_2"]:
        # Open dataset from Icechunk repository:
        ds = open_icechunk_store(bucket=bucket, prefix=prefix, branch="branch_name")

        item = create_item_with_icechunk_asset(
            ds=ds,
            id=f"{bucket}/{prefix}",
            bucket=bucket,
            prefix=prefix,
            start_date="YYYY-MM-DD",
            end_date="YYYY-MM-DD",
            collection=bucket,
            )
        # Add Item to the Example STAC Collection:
        example_collection.add_item(item)

    logging.info(f"Completed: Added Items to STAC Collection with ID: {example_collection.id}")

    return example_collection
