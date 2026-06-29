"""
obs_collections.py

Description:
Function to create Spatio-Temporal Access Catalog Collections
for ocean observation datasets.

Authors:
    - Ollie Tooth (oliver.tooth@noc.ac.uk)
"""
# -- Import Python Modules -- #
import logging
import pystac
import datetime

from OceanDataStore.catalog.stac.utils import open_icechunk_store, create_item_with_icechunk_asset


def create_nsidc_collection() -> pystac.Collection:
    """
    Create the NSIDC Sea Ice Index, Version 4 STAC Collection.
    
    Returns:
    -------
    nsidc_collection : pystac.Collection
        NSIDC Sea Ice Index, Version 4 STAC Collection.
    """
    # ==== Define NSIDC Sea Ice Index, Version 4 Collection ==== #
    # Define the spatial extent for the collection:
    spatial_extent = pystac.SpatialExtent(bboxes=[[-180.0, -90.0, 180.0, 90.0]])

    # Define the current temporal extent for the collection:
    collection_interval = sorted([datetime.datetime(year=1978, month=11, day=15), datetime.datetime(year=2025, month=12, day=15)])
    temporal_extent = pystac.TemporalExtent(intervals=[collection_interval])

    # Define the NSIDC Sea Ice Index, Version 4 Collection:
    nsidc_collection = pystac.Collection(
        id="nsidc",
        title="NSIDC Sea Ice Index, Version 4 Collection",
        description="**About:**\n\nCollection of National Snow and Ice Data Center (NSIDC) Sea Ice Index, Version 4 datasets.\n\n**More Information:**\n - [NSIDC](https://nsidc.org/home)",
        extent=pystac.Extent(spatial=spatial_extent, temporal=temporal_extent),
        license="U.S. Government Works License",
        extra_fields=dict(contact="Ollie Tooth (oliver.tooth@noc.ac.uk)", project="OceanDataStore", status="ongoing", update_frequency="quarterly", last_data_update="2025-12-15"),
        keywords=["NSIDC", "arctic", "antarctic", "observation", "sea-ice"],
        providers=[
            pystac.Provider(
                name="National Snow and Ice Data Center (NSIDC)",
                description="National Snow and Ice Data Center (NSIDC), Cooperative Institute for Research in Environmental Sciences, University of Colorado, United States.",
                roles=[pystac.ProviderRole.PRODUCER, pystac.ProviderRole.LICENSOR],
                url="https://nsidc.org/data/g02135/versions/4"
            ),
            pystac.Provider(
                name="JASMIN",
                description="JASMIN Environmental Data Analysis Facility (United Kingdom).",
                roles=[pystac.ProviderRole.HOST],
                url="https://jasmin.ac.uk"
            )
        ],
    )

    logging.info(f"Completed: Created STAC Collection: {nsidc_collection}")

    # -- Add Items to NSIDC Sea Ice Index Collection -- #
    bucket = "nsidc"
    for prefix in ["nsidc_sea_ice_index_v4_antarctic_monthly", "nsidc_sea_ice_index_v4_arctic_monthly"]:
        # Open dataset from Icechunk repository:
        ds = open_icechunk_store(bucket=bucket, prefix=prefix, branch="main")

        item = create_item_with_icechunk_asset(
            ds=ds,
            id=f"{bucket}/{prefix}",
            bucket=bucket,
            prefix=prefix,
            start_date="1978-11-15",
            end_date="2025-12-15",
            collection=bucket
            )
        # Add Item to the NSIDC Sea Ice Index Collection:
        nsidc_collection.add_item(item)

    logging.info(f"Completed: Added Items to STAC Collection with ID: {nsidc_collection.id}")

    return nsidc_collection


def create_woa23_collection() -> pystac.Collection:
    """
    Create the World Ocean Atlas 2023 STAC Collection.
    
    Returns:
    -------
    woa23_collection : pystac.Collection
        World Ocean Atlas 2023 STAC Collection.
    """
    # ==== Define World Ocean Atlas 2023 Collection ==== #
    # Define the spatial extent for the collection:
    spatial_extent = pystac.SpatialExtent(bboxes=[[-180.0, -90.0, 180.0, 90.0]])

    # Define the current temporal extent for the collection:
    collection_interval = sorted([datetime.datetime(year=1971, month=1, day=1), datetime.datetime(year=2020, month=12, day=31)])
    temporal_extent = pystac.TemporalExtent(intervals=[collection_interval])

    # Define the World Ocean Atlas 2023 Collection:
    woa23_collection = pystac.Collection(
        id="woa23",
        title="World Ocean Atlas 2023 Collection",
        description="**About:**\n\nCollection of World Ocean Atlas 2023 climatology datasets.\n\n**More Information:**\n - [World Ocean Atlas](https://www.ncei.noaa.gov/access/world-ocean-atlas-2023/)",
        extent=pystac.Extent(spatial=spatial_extent, temporal=temporal_extent),
        license="Creative Commons CC0 1.0 Universal License",
        extra_fields=dict(contact="Ollie Tooth (oliver.tooth@noc.ac.uk)", project="OceanDataStore", status="ongoing", update_frequency="None", last_data_update="2024-02-01"),
        keywords=["WOA23", "global", "observation", "temperature", "salinity"],
        providers=[
            pystac.Provider(
                name="NOAA National Centers for Environmental Information (NCEI)",
                description="National Oceanic and Atmospheric Administration (NOAA) National Centers for Environmental Information (NCEI), United States.",
                roles=[pystac.ProviderRole.PRODUCER, pystac.ProviderRole.LICENSOR],
                url="https://www.ncei.noaa.gov",
            ),
            pystac.Provider(
                name="JASMIN",
                description="JASMIN Environmental Data Analysis Facility (United Kingdom).",
                roles=[pystac.ProviderRole.HOST],
                url="https://jasmin.ac.uk"
            )
        ],
    )

    logging.info(f"Completed: Created STAC Collection: {woa23_collection}")

    # -- Add Items to World Ocean Atlas 2023 Collection -- #
    bucket = "woa23"
    for prefix in ["woa23_1971_2000_annual_climatology",
                   "woa23_1971_2000_monthly_climatology",
                   "woa23_1981_2010_annual_climatology",
                   "woa23_1981_2010_monthly_climatology",
                   "woa23_1991_2020_annual_climatology",
                   "woa23_1991_2020_monthly_climatology"
                   ]:
        # Open dataset from Icechunk repository:
        ds = open_icechunk_store(bucket=bucket, prefix=prefix, branch="main")

        item = create_item_with_icechunk_asset(
            ds=ds,
            id=f"{bucket}/{prefix}",
            bucket=bucket,
            prefix=prefix,
            start_date=f"{prefix.split('_')[1]}-01-01",
            end_date=f"{prefix.split('_')[2]}-12-31",
            collection=bucket
            )
        # Add item to the World Ocean Atlas 2023 Collection:
        woa23_collection.add_item(item)

    logging.info(f"Completed: Added Items to STAC Collection with ID: {woa23_collection.id}")

    return woa23_collection


def create_oisst_collection() -> pystac.Collection:
    """
    Create the OISST Version 2.1 STAC Collection.
    
    Returns:
    -------
    oisst_collection : pystac.Collection
        OISST Version 2.1 STAC Collection.
    """
    # ==== Define OISST Version 2.1 Collection ==== #
    # Define the spatial extent for the collection:
    spatial_extent = pystac.SpatialExtent(bboxes=[[-180.0, -90.0, 180.0, 90.0]])

    # Define the current temporal extent for the collection:
    collection_interval = sorted([datetime.datetime(year=1981, month=9, day=1), datetime.datetime(year=2026, month=5, day=1)])
    temporal_extent = pystac.TemporalExtent(intervals=[collection_interval])

    # Define the OISST Version 2.1 Collection:
    oisst_collection = pystac.Collection(
        id="oisst",
        title="OISST Version 2.1 Collection",
        description="**About:**\n\nCollection of OISST Version 2.1 datasets.\n\n**More Information:**\n - [OISST Version 2.1](https://psl.noaa.gov/data/gridded/data.noaa.oisst.v2.highres.html)",
        extent=pystac.Extent(spatial=spatial_extent, temporal=temporal_extent),
        license="Creative Commons CC0 1.0 Universal License",
        extra_fields=dict(contact="Ollie Tooth (oliver.tooth@noc.ac.uk)", project="OceanDataStore", status="ongoing", update_frequency="quarterly", last_data_update="2026-05-01"),
        keywords=["OISSTv2.1", "global", "observation", "sea surface temperature", "sea ice concentration"],
        providers=[
            pystac.Provider(
                name="NOAA National Centers for Environmental Information (NCEI)",
                description="National Oceanic and Atmospheric Administration (NOAA) National Centers for Environmental Information (NCEI), United States.",
                roles=[pystac.ProviderRole.PRODUCER, pystac.ProviderRole.LICENSOR],
                url="https://www.ncei.noaa.gov",
            ),
            pystac.Provider(
                name="JASMIN",
                description="JASMIN Environmental Data Analysis Facility (United Kingdom).",
                roles=[pystac.ProviderRole.HOST],
                url="https://jasmin.ac.uk"
            )
        ],
    )

    logging.info(f"Completed: Created STAC Collection: {oisst_collection}")

    # -- Add Items to OISST Version 2.1 Collection -- #
    bucket = "oisst"
    for prefix in ["oisst_v2.1_monthly",
                   "oisst_v2.1_1991_2020_daily_climatology",
                   "oisst_v2.1_1991_2020_monthly_climatology",
                   ]:
        # Open dataset from Icechunk repository:
        ds = open_icechunk_store(bucket=bucket, prefix=prefix, branch="main")

        if "1991_2020" in prefix:
            start_date = "1991-01-01"
            end_date = "2020-12-31"
        else:
            start_date = "1981-09-01"
            end_date = "2026-05-01"

        item = create_item_with_icechunk_asset(
            ds=ds,
            id=f"{bucket}/{prefix}",
            bucket=bucket,
            prefix=prefix,
            start_date=start_date,
            end_date=end_date,
            collection=bucket
            )
        # Add item to the OISST Version 2.1 Collection:
        oisst_collection.add_item(item)

    logging.info(f"Completed: Added Items to STAC Collection with ID: {oisst_collection.id}")

    return oisst_collection


def create_en4_collection() -> pystac.Collection:
    """
    Create the EN4.2.2 STAC Collection.
    
    Returns:
    -------
    en4_collection : pystac.Collection
        EN4.2.2 STAC Collection.
    """
    # ==== Define EN4.2.2 Collection ==== #
    # Define the spatial extent for the collection:
    spatial_extent = pystac.SpatialExtent(bboxes=[[-180.0, -90.0, 180.0, 90.0]])

    # Define the current temporal extent for the collection:
    collection_interval = sorted([datetime.datetime(year=1950, month=1, day=1), datetime.datetime(year=2026, month=3, day=1)])
    temporal_extent = pystac.TemporalExtent(intervals=[collection_interval])

    # Define the EN4.2.2 Collection:
    en4_collection = pystac.Collection(
        id="en4.2.2",
        title="EN4.2.2 Collection",
        description="**About:**\n\nCollection of EN4.2.2 quality Controlled Ocean datasets.\n\n**More Information:**\n - [EN4.2.2](https://www.metoffice.gov.uk/hadobs/en4/)",
        extent=pystac.Extent(spatial=spatial_extent, temporal=temporal_extent),
        license="Non-Commercial Government Licence",
        extra_fields=dict(contact="Ollie Tooth (oliver.tooth@noc.ac.uk)", project="OceanDataStore", status="ongoing", update_frequency="quarterly", last_data_update="2026-05-01"),
        keywords=["EN4.2.2", "global", "observation", "temperature", "salinity"],
        providers=[
            pystac.Provider(
                name="Met Office",
                description="Met Office, United Kingdom.",
                roles=[pystac.ProviderRole.PRODUCER, pystac.ProviderRole.LICENSOR],
                url="https://www.metoffice.gov.uk",
            ),
            pystac.Provider(
                name="JASMIN",
                description="JASMIN Environmental Data Analysis Facility (United Kingdom).",
                roles=[pystac.ProviderRole.HOST],
                url="https://jasmin.ac.uk"
            )
        ],
    )

    logging.info(f"Completed: Created STAC Collection: {en4_collection}")

    # -- Add Items to EN4.2.2 Collection -- #
    bucket = "en4.2.2"
    for prefix in ["en4.2.2_analysis_g10_monthly",
                   "en4.2.2_analysis_g10_1971_2000_monthly_climatology",
                   "en4.2.2_analysis_g10_1981_2010_monthly_climatology",
                   "en4.2.2_analysis_g10_1991_2020_monthly_climatology",
                   ]:
        # Open dataset from Icechunk repository:
        ds = open_icechunk_store(bucket=bucket, prefix=prefix, branch="main")

        if "19" in prefix:
            start_date = f"{prefix.split('_')[3]}-01-01"
            end_date = f"{prefix.split('_')[4]}-12-31"
        else:
            start_date = "1950-01-01"
            end_date = "2026-03-12"

        item = create_item_with_icechunk_asset(
            ds=ds,
            id=f"{bucket}/{prefix}",
            bucket=bucket,
            prefix=prefix,
            start_date=start_date,
            end_date=end_date,
            collection=bucket
            )
        # Add item to the EN4.2.2 Collection:
        en4_collection.add_item(item)

    logging.info(f"Completed: Added Items to STAC Collection with ID: {en4_collection.id}")

    return en4_collection


def create_armor3d_collection() -> pystac.Collection:
    """
    Create the ARMOR3D STAC Collection.
    
    Returns:
    -------
    armor3d_collection : pystac.Collection
        ARMOR3D STAC Collection.
    """
    # ==== Define ARMOR3D Collection ==== #
    # Define the spatial extent for the collection:
    spatial_extent = pystac.SpatialExtent(bboxes=[[-180.0, -90.0, 180.0, 90.0]])

    # Define the current temporal extent for the collection:
    collection_interval = sorted([datetime.datetime(year=1993, month=1, day=1), datetime.datetime(year=2024, month=12, day=31)])
    temporal_extent = pystac.TemporalExtent(intervals=[collection_interval])

    # Define the ARMOR3D Collection:
    armor3d_collection = pystac.Collection(
        id="armor3d",
        title="ARMOR3D Collection",
        description="**About:**\n\nCollection of Multi Observation Global Ocean ARMOR3D Temperature Salinity Height Geostrophic Current and MLD.\n\n**More Information:**\n - [ARMOR3D](https://data.marine.copernicus.eu/product/MULTIOBS_GLO_PHY_TSUV_3D_MYNRT_015_012/description)",
        extent=pystac.Extent(spatial=spatial_extent, temporal=temporal_extent),
        license="Copernicus Marine Environment Monitoring Service Service Level Agreement (SLA)",
        extra_fields=dict(contact="Ollie Tooth (oliver.tooth@noc.ac.uk)", project="OceanDataStore", status="ongoing", update_frequency="quarterly", last_data_update="2025-11-01"),
        keywords=["ARMOR3D", "global", "observation", "temperature", "salinity", "dynamic height", "geostrophic current", "mixed layer depth"],
        providers=[
            pystac.Provider(
                name="Copernicus Marine Service",
                description="Copernicus Marine Service, Mercator Ocean International, France.",
                roles=[pystac.ProviderRole.PRODUCER, pystac.ProviderRole.LICENSOR],
                url="https://marine.copernicus.eu",
            ),
            pystac.Provider(
                name="JASMIN",
                description="JASMIN Environmental Data Analysis Facility (United Kingdom).",
                roles=[pystac.ProviderRole.HOST],
                url="https://jasmin.ac.uk"
            )
        ],
    )

    logging.info(f"Completed: Created STAC Collection: {armor3d_collection}")

    # -- Add Items to ARMOR3D Collection -- #
    bucket = "armor3d"
    for prefix in ["armor3d_global_my_monthly",
                   "armor3d_global_my_1971_2000_monthly_climatology",
                   "armor3d_global_my_1981_2010_monthly_climatology",
                   "armor3d_global_my_1991_2020_monthly_climatology",
                   ]:
        # Open dataset from Icechunk repository:
        ds = open_icechunk_store(bucket=bucket, prefix=prefix, branch="main")

        if "19" in prefix:
            start_date = f"{prefix.split('_')[3]}-01-01"
            end_date = f"{prefix.split('_')[4]}-12-31"
        else:
            start_date = "1993-01-01"
            end_date = "2024-12-31"

        item = create_item_with_icechunk_asset(
            ds=ds,
            id=f"{bucket}/{prefix}",
            bucket=bucket,
            prefix=prefix,
            start_date=start_date,
            end_date=end_date,
            collection=bucket
            )
        # Add item to the ARMOR3D Collection:
        armor3d_collection.add_item(item)

    logging.info(f"Completed: Added Items to STAC Collection with ID: {armor3d_collection.id}")

    return armor3d_collection


def create_hadisst_collection() -> pystac.Collection:
    """
    Create the HadISST Version 1.1 STAC Collection.
    
    Returns:
    -------
    hadisst_collection : pystac.Collection
        HadISST Version 1.1 STAC Collection.
    """
    # ==== Define HadISST Version 1.1 Collection ==== #
    # Define the spatial extent for the collection:
    spatial_extent = pystac.SpatialExtent(bboxes=[[-180.0, -90.0, 180.0, 90.0]])

    # Define the current temporal extent for the collection:
    collection_interval = sorted([datetime.datetime(year=1870, month=1, day=16), datetime.datetime(year=2026, month=4, day=16)])
    temporal_extent = pystac.TemporalExtent(intervals=[collection_interval])

    # Define the HadISST Version 1.1 Collection:
    hadisst_collection = pystac.Collection(
        id="hadisst",
        title="HadISST Version 1.1 Collection",
        description="**About:**\n\nCollection of HadISST Version 1.1 datasets.\n\n**More Information:**\n - [HadISST Version 1.1](https://www.metoffice.gov.uk/hadobs/hadisst/)",
        extent=pystac.Extent(spatial=spatial_extent, temporal=temporal_extent),
        license="Non-Commercial Government Licence",
        extra_fields=dict(contact="Ollie Tooth (oliver.tooth@noc.ac.uk)", project="OceanDataStore", status="ongoing", update_frequency="quarterly", last_data_update="2026-05-01"),
        keywords=["HadISSTv1.1", "global", "observation", "sea surface temperature", "sea ice concentration"],
        providers=[
            pystac.Provider(
                name="Met Office",
                description="Met Office, United Kingdom.",
                roles=[pystac.ProviderRole.PRODUCER, pystac.ProviderRole.LICENSOR],
                url="https://www.metoffice.gov.uk",
            ),
            pystac.Provider(
                name="JASMIN",
                description="JASMIN Environmental Data Analysis Facility (United Kingdom).",
                roles=[pystac.ProviderRole.HOST],
                url="https://jasmin.ac.uk"
            )
        ],
    )

    logging.info(f"Completed: Created STAC Collection: {hadisst_collection}")

    # -- Add Items to HadISST Version 1.1 Collection -- #
    bucket = "hadisst"
    for prefix in ["hadisst_v1.1_monthly"]:
        # Open dataset from Icechunk repository:
        ds = open_icechunk_store(bucket=bucket, prefix=prefix, branch="main")

        item = create_item_with_icechunk_asset(
            ds=ds,
            id=f"{bucket}/{prefix}",
            bucket=bucket,
            prefix=prefix,
            start_date="1870-01-16",
            end_date="2026-05-01",
            collection=bucket
            )
        # Add item to the HadISST Version 1.1 Collection:
        hadisst_collection.add_item(item)

    logging.info(f"Completed: Added Items to STAC Collection with ID: {hadisst_collection.id}")

    return hadisst_collection


def create_era5_collection() -> pystac.Collection:
    """
    Create the ERA5 STAC Collection.
    
    Returns:
    -------
    era5_collection : pystac.Collection
        ERA5 STAC Collection.
    """
    # ==== Define ERA5 Collection ==== #
    # Define the spatial extent for the collection:
    spatial_extent = pystac.SpatialExtent(bboxes=[[-180.0, -90.0, 180.0, 90.0]])

    # Define the current temporal extent for the collection:
    collection_interval = sorted([datetime.datetime(year=1980, month=1, day=1), datetime.datetime(year=2026, month=6, day=20)])
    temporal_extent = pystac.TemporalExtent(intervals=[collection_interval])

    # Define the ERA5 Collection:
    era5_collection = pystac.Collection(
        id="era5",
        title="ERA5 Collection",
        description="**About:**\n\nCollection of ERA5 datasets.\n\n**More Information:**\n - [ERA5](https://www.ecmwf.int/en/forecasts/datasets/reanalysis-datasets/era5)",
        extent=pystac.Extent(spatial=spatial_extent, temporal=temporal_extent),
        license="Creative Commons CC-BY-4.0 License",
        extra_fields=dict(contact="Ollie Tooth (oliver.tooth@noc.ac.uk)", project="OceanDataStore", status="ongoing", update_frequency="quarterly", last_data_update="2026-06-20"),
        keywords=["ERA5", "global", "reanalysis", "sea surface temperature", "sea ice concentration"],
        providers=[
            pystac.Provider(
                name="ECMWF",
                description="European Centre for Medium-Range Weather Forecasts (ECMWF), EU.",
                roles=[pystac.ProviderRole.PRODUCER, pystac.ProviderRole.LICENSOR],
                url="https://www.ecmwf.int",
            ),
            pystac.Provider(
                name="JASMIN",
                description="JASMIN Environmental Data Analysis Facility (United Kingdom).",
                roles=[pystac.ProviderRole.HOST],
                url="https://jasmin.ac.uk"
            )
        ],
    )

    logging.info(f"Completed: Created STAC Collection: {era5_collection.id}")

    # -- Add Items to ERA5 Collection -- #
    bucket = "era5"
    prefixes = ["era5_1991_2020_daily_climatology",
                "era5_1996_2025_daily_climatology",
                "era5_daily_timeseries",
                "era5_monthly_timeseries"
                ]
    dates = [("1991-01-01", "2020-12-31"),
             ("1996-01-01", "2025-12-31"),
             ("1980-01-01", "2026-06-20"),
             ("1980-01-01", "2026-06-20")
             ]

    for prefix, date in zip(prefixes, dates):
        # Open dataset from Icechunk repository:
        ds = open_icechunk_store(bucket=bucket, prefix=prefix, branch="main")

        item = create_item_with_icechunk_asset(
            ds=ds,
            id=f"{bucket}/{prefix}",
            bucket=bucket,
            prefix=prefix,
            start_date=date[0],
            end_date=date[1],
            collection=bucket
            )
        # Add item to the ERA5 Collection:
        era5_collection.add_item(item)

    logging.info(f"Completed: Added Items to STAC Collection with ID: {era5_collection.id}")

    return era5_collection


def create_ostia_collection() -> pystac.Collection:
    """
    Create the OSTIA STAC Collection.
    
    Returns:
    -------
    ostia_collection : pystac.Collection
        OSTIA STAC Collection.
    """
    # ==== Define OSTIA Collection ==== #
    # Define the spatial extent for the collection:
    spatial_extent = pystac.SpatialExtent(bboxes=[[-44.975, 13.975, 31.025, 84.975]])

    # Define the current temporal extent for the collection:
    collection_interval = sorted([datetime.datetime(year=1993, month=1, day=1), datetime.datetime(year=2024, month=12, day=31)])
    temporal_extent = pystac.TemporalExtent(intervals=[collection_interval])

    # Define the OSTIA Collection:
    ostia_collection = pystac.Collection(
        id="ostia",
        title="OSTIA Collection",
        description="**About:**\n\nCollection of OSTIA Sea Surface Datasets.\n\n**More Information:**\n - [OSTIA](https://doi.org/10.48670/moi-00165)",
        extent=pystac.Extent(spatial=spatial_extent, temporal=temporal_extent),
        license="Copernicus Marine Environment Monitoring Service Service Level Agreement (SLA)",
        extra_fields=dict(contact="Ollie Tooth (oliver.tooth@noc.ac.uk)", project="OceanDataStore", status="ongoing", update_frequency="quarterly", last_data_update="2025-11-01"),
        keywords=["OSTIA", "North Atlantic", "observation", "sea surface temperature", "sea ice concentration"],
        providers=[
            pystac.Provider(
                name="Met Office",
                description="Met Office, United Kingdom.",
                roles=[pystac.ProviderRole.PRODUCER],
                url="https://www.metoffice.gov.uk",
            ),
            pystac.Provider(
                name="Copernicus Marine Service",
                description="Copernicus Marine Service, Mercator Ocean International, France.",
                roles=[pystac.ProviderRole.LICENSOR],
                url="https://marine.copernicus.eu",
            ),
            pystac.Provider(
                name="JASMIN",
                description="JASMIN Environmental Data Analysis Facility (United Kingdom).",
                roles=[pystac.ProviderRole.HOST],
                url="https://jasmin.ac.uk"
            )
        ],
    )

    logging.info(f"Completed: Created STAC Collection: {ostia_collection}")

    # -- Add Items to OSTIA Collection -- #
    bucket = "ostia"
    for prefix in ["ostia_rep_na_1991_2020_daily_climatology",
                   "ostia_rep_na_1996_2025_daily_climatology",
                   "ostia_rep_na_daily_timeseries",
                   "ostia_nrt_na_daily_timeseries",
                   "ostia_rep_na_daily_spatial",
                   "ostia_nrt_na_daily_spatial"
                   ]:
        # Open dataset from Icechunk repository:
        ds = open_icechunk_store(bucket=bucket, prefix=prefix, branch="main")

        if "19" in prefix:
            start_date = f"{prefix.split('_')[3]}-01-01"
            end_date = f"{prefix.split('_')[4]}-12-31"
        elif "rep" in prefix:
            start_date = "1981-10-01"
            end_date = "2025-12-18"
        else:
            start_date = "2025-01-01"
            end_date = "2026-06-28"

        item = create_item_with_icechunk_asset(
            ds=ds,
            id=f"{bucket}/{prefix}",
            bucket=bucket,
            prefix=prefix,
            start_date=start_date,
            end_date=end_date,
            collection=bucket
            )
        # Add item to the OSTIA Collection:
        ostia_collection.add_item(item)

    logging.info(f"Completed: Added Items to STAC Collection with ID: {ostia_collection.id}")

    return ostia_collection