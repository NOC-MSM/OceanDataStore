"""
npd_collections.py

Description:
Function to create the National Oceanography Centre (NOC) 
Near-Present Day Spatio-Temporal Access Catalog Collection.

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
        open_icechunk_store,
)

logger = logging.getLogger(__name__)

def description_from_prefix(prefix: str, ds: xr.Dataset) -> str:
        """
        Define Item description based on the prefix and Dataset attributes.
        
        Parameters:
        ----------
        prefix : str
            Prefix of Icechunk repository,
            
        ds : xr.Dataset
            Dataset opened from Icechunk repository, which contains global attributes
            'aggregation_frequency' and 'aggregation' used to define Item description.
            
        Returns:
        -------
        description : str
            Description of NEMO model output Item.
        """
        # --- Validate input arguments --- #
        if not isinstance(prefix, str):
                raise TypeError("'prefix' must be a string.")
        if not isinstance(ds, xr.Dataset):
                raise TypeError("'ds' must be an xarray.Dataset.")
        

        # --- --- Define the item description based on the prefix --- #
        if 'domain' in prefix:
            description = "**Global ocean model domain and mesh mask variables.**"
        elif 'T' in prefix:
            description = f"**{ds.attrs.get('aggregation_frequency', 'monthly').capitalize()} {ds.attrs.get('aggregation', 'mean')} global ocean scalar outputs defined at {prefix[0]}-points.**"
        elif 'U' in prefix:
            description = f"**{ds.attrs.get('aggregation_frequency', 'monthly').capitalize()} {ds.attrs.get('aggregation', 'mean')} global ocean zonal vector outputs defined at {prefix[0]}-points.**"
        elif 'V' in prefix:
            description = f"**{ds.attrs.get('aggregation_frequency', 'monthly').capitalize()} {ds.attrs.get('aggregation', 'mean')} global ocean meridional vector outputs defined at {prefix[0]}-points.**"
        elif 'W' in prefix:
            description = f"**{ds.attrs.get('aggregation_frequency', 'monthly').capitalize()} {ds.attrs.get('aggregation', 'mean')} global ocean vertical vector outputs defined at {prefix[0]}-points.**"
        elif 'F' in prefix:
            description = f"**{ds.attrs.get('aggregation_frequency', 'monthly').capitalize()} {ds.attrs.get('aggregation', 'mean')} global ocean vector outputs defined at {prefix[0]}-points.**"
        elif 'I' in prefix:
            description = f"**{ds.attrs.get('aggregation_frequency', 'monthly').capitalize()} {ds.attrs.get('aggregation', 'mean')} global sea-ice outputs defined at T-points.**"
        elif 'S' in prefix:
            description = f"**{ds.attrs.get('aggregation_frequency', 'monthly').capitalize()} {ds.attrs.get('aggregation', 'mean')} global ocean scalar outputs.**"
        elif 'M' in prefix:
            description = f"**{ds.attrs.get('aggregation_frequency', 'monthly').capitalize()} {ds.attrs.get('aggregation', 'mean')} ocean physics transect outputs defined at {prefix.split('/')[-1]}.**"
        else:
            raise ValueError(f"Unable to determine variable type from prefix: {prefix}")


        return description


def create_npd_era5_collection() -> pystac.Collection:
    """
    Create the NOC Near-Present Day ERA-5 STAC Collection.
    
    Returns:
    -------
    npd_collection : pystac.Collection
        NOC Near-Present Day ERA-5 STAC Collection.
    """
    # ==== Define NOC Near-Present Day Collection ==== #
    # Define the spatial extent for the collection:
    spatial_extent = pystac.SpatialExtent(bboxes=[[-180.0, -90.0, 0, 180.0, 90.0, 6000]])

    # Define the current temporal extent for the collection:
    start_datetime = datetime.datetime(year=1976, month=1, day=1, tzinfo=datetime.timezone.utc)
    end_datetime = datetime.datetime(year=2026, month=5, day=15, tzinfo=datetime.timezone.utc)
    start_date_str = start_datetime.strftime("%Y-%m-%d")
    end_date_str = end_datetime.strftime("%Y-%m-%d")
    collection_interval = sorted([start_datetime, end_datetime])
    temporal_extent = pystac.TemporalExtent(intervals=[collection_interval])

    # Define the Near-Present Day Collection:
    npd_collection = pystac.Collection(
        id="noc-npd-era5",
        title="NOC Near-Present Day ERA-5 Collection",
        description="**About:**\n\nCollection of multi-decadal Near-Present Day ocean model hindcast simulations produced by the National Oceanography Centre (NOC) using bias-corrected ERA-5 atmospheric forcing as part of the Atlantic Climate and Environment Strategic Science (AtlantiS) programme.\n\n**More Information:**\n - [AtlantiS](https://atlantis.ac.uk)\n - [NOC Near-Present Day](https://noc-msm.github.io/NOC_Near_Present_Day/)",
        extent=pystac.Extent(spatial=spatial_extent, temporal=temporal_extent),
        # Open Government License (OGL) - UK version 3.0 - http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
        license="OGL-UK-3.0",
        extra_fields={"contact": "Ollie Tooth (oliver.tooth@noc.ac.uk)",
                      "project": "AtlantiS",
                      "status": "ongoing",
                      "update_frequency":
                      "biannual",
                      "last_data_update": end_date_str
                      },
        keywords=["NOC", "Near-Present Day", "AtlantiS", "hindcast", "global", "model", "ocean", "sea-ice"],
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

    logger.info(f"Completed: Created STAC Collection with ID: {npd_collection.id}")

    # ==== Define NOC Near-Present Day Model Configuration Catalogs ==== #
    npd_eorca1_era5v1 = pystac.Catalog(
        id="npd-eorca1-era5v1",
        title="eORCA1 ERA5v1 NPD Catalog",
        description="Catalog of eORCA1 ERA-5 Near-Present Day ocean sea-ice simulations performed by the National Oceanography Centre."
        )

    logger.info(f"-> Completed: Created STAC Catalog with ID: {npd_eorca1_era5v1.id}")

    npd_eorca025_era5v1 = pystac.Catalog(
        id="npd-eorca025-era5v1",
        title="eORCA025 ERA5v1 NPD Catalog",
        description="Catalog of eORCA025 ERA-5 Near-Present Day ocean sea-ice simulations performed by the National Oceanography Centre.",
        )

    logger.info(f"-> Completed: Created STAC Catalog with ID: {npd_eorca025_era5v1.id}")

    npd_eorca12_era5v1 = pystac.Catalog(
        id="npd-eorca12-era5v1",
        title="eORCA12 ERA5v1 NPD Catalog",
        description="Catalog of eORCA12 ERA-5 Near-Present Day ocean sea-ice simulations performed by the National Oceanography Centre.",
        )

    logger.info(f"-> Completed: Created STAC Catalog with ID: {npd_eorca12_era5v1.id}")

    # ==== Define NOC Near-Present Day Model Variant Catalogs ==== #
    r1i1c1f1_eorca1_era5v1 = pystac.Catalog(
        id="r1i1c1f1",
        title="eORCA1 ERA5v1 NPD: r1i1c1f1 Catalog",
        description="Catalog of eORCA1 ERA-5 Near-Present Day ocean physics & sea-ice outputs for model variant: r1i1c1f1.\n\n**Variant Label:**\n\nRealisation=1, Initialisation=1, Configuration=1, Forcing=1."
        )

    logger.info(f"-> Completed: Created STAC Catalog with ID: {r1i1c1f1_eorca1_era5v1.id}")

    r1i1c1f1_eorca025_era5v1 = pystac.Catalog(
        id="r1i1c1f1",
        title="eORCA025 ERA5v1 NPD: r1i1c1f1 Catalog",
        description="Catalog of eORCA025 ERA-5 Near-Present Day ocean physics & sea-ice outputs for model variant: r1i1c1f1.\n\n**Variant Label:**\n\nRealisation=1, Initialisation=1, Configuration=1, Forcing=1."
        )

    logger.info(f"-> Completed: Created STAC Catalog with ID: {r1i1c1f1_eorca025_era5v1.id}")

    r1i1c1f1_eorca12_era5v1 = pystac.Catalog(
        id="r1i1c1f1",
        title="eORCA12 ERA5v1 NPD: r1i1c1f1 Catalog",
        description="Catalog of eORCA12 ERA-5 Near-Present Day ocean physics & sea-ice outputs for model variant: r1i1c1f1.\n\n**Variant Label:**\n\nRealisation=1, Initialisation=1, Configuration=1, Forcing=1."
        )

    logger.info(f"-> Completed: Created STAC Catalog with ID: {r1i1c1f1_eorca12_era5v1.id}")

    # -- Add Items to NOC Near-Present Day eORCA1 ERA5v1 Sub-Catalog -- #
    # Define the store credentials for the eORCA1 ERA5v1 NPD data:
    bucket = "npd-eorca1-era5v1"

    # Open domain_cfg dataset from Icechunk repository:
    ds = open_icechunk_store(bucket=bucket, prefix="domain/domain_cfg", branch="main")

    item = create_item_with_icechunk_asset(
        ds=ds,
        id=f"noc-npd-era5/{bucket}/{ds.attrs.get('variant', 'r1i1c1f1')}/domain/domain_cfg",
        bucket=bucket,
        prefix="domain/domain_cfg",
        title="NPD eORCA1 ERA5v1 domain_cfg",
        description=description_from_prefix(prefix="domain/domain_cfg", ds=ds),
        start_date=start_date_str,
        end_date=end_date_str,
        collection=bucket
        )
    # Add item to the eORCA1 ERA5v1 NPD domain_cfg catalog:
    r1i1c1f1_eorca1_era5v1.add_item(item)

    for freq in ["1y", "1m"]:
        # Add root group for hierarchical Icechunk repository:
        ds = open_icechunk_store(bucket=bucket, prefix=f"eorca1-era5v1-{freq}", branch="main")
        ds_time = open_icechunk_store(bucket=bucket, prefix=f"eorca1-era5v1-{freq}", branch="main", group="gridT")
        item = create_item_with_icechunk_asset(
            ds=ds,
            id=f"noc-npd-era5/{bucket}/{ds.attrs.get('variant', 'r1i1c1f1')}/eorca1-era5v1-{freq}",
            bucket=bucket,
            prefix=f"eorca1-era5v1-{freq}",
            title=f"NPD eORCA1 ERA5v1 {freq} NEMODataTree",
            description=f"**{'Annual-mean' if freq == '1y' else 'Monthly-mean' if freq == '1m' else '5-day mean'} global ocean outputs.**",
            start_date=ds_time["time_counter"].dt.strftime("%Y-%m-%d").values[0],
            end_date=ds_time["time_counter"].dt.strftime("%Y-%m-%d").values[-1],
            collection=bucket,
            )
        # Add item to the eORCA1 ERA5v1 NPD global native model grid catalog:
        r1i1c1f1_eorca1_era5v1.add_item(item)

        # Add individual groups in hierarchical Icechunk repository:
        for prefix in ["T", "U", "V", "W"]:
            prefix_freq = f"{prefix}{freq}"
            # Open dataset from Icechunk repository:
            ds = open_icechunk_store(bucket=bucket, prefix=f"eorca1-era5v1-{freq}", branch="main", group=f"grid{prefix}")

            item = create_item_with_icechunk_asset(
                ds=ds,
                id=f"noc-npd-era5/{bucket}/{ds.attrs.get('variant', 'r1i1c1f1')}/{prefix_freq}",
                bucket=bucket,
                prefix=f"eorca1-era5v1-{freq}",
                title=f"NPD eORCA1 ERA5v1 NEMODataTree {prefix}-grid node",
                description=f"**{'Annual-mean' if freq == '1y' else 'Monthly-mean' if freq == '1m' else '5-day mean'} global ocean {'scalar' if prefix == 'T' else 'vector'} outputs defined at {prefix}-points.**",
                collection=bucket,
                group=f"grid{prefix}"
                )
            # Add item to the eORCA1 ERA5v1 NPD global native model grid catalog:
            r1i1c1f1_eorca1_era5v1.add_item(item)

    # Define the store credentials for the eORCA1 ERA5v1 NPD data:
    for prefix in ["M1m/MOVE_16N", "M1m/SAMBA_34_5S", "M1m/RAPID_26N", "M1m/OSNAP"]:
        # Open dataset from Icechunk repository:
        ds = open_icechunk_store(bucket=bucket, prefix=prefix, branch="main")
        
        item = create_item_with_icechunk_asset(
            ds=ds,
            id=f"noc-npd-era5/{bucket}/{ds.attrs.get('variant', 'r1i1c1f1')}/{prefix}",
            bucket=bucket,
            prefix=prefix,
            title=f"NPD eORCA1 ERA5v1 {prefix}",
            description=description_from_prefix(prefix=prefix, ds=ds),
            platform=ds.attrs.get('platform', 'tn'),
            start_date=start_date_str,
            end_date=end_date_str,
            collection=bucket
            )
        # Add item to the eORCA1 ERA5v1 NPD transect catalog:
        r1i1c1f1_eorca1_era5v1.add_item(item)

    logger.info(f"-> Completed: Added Items to STAC Catalog with ID: {npd_collection.id}/{npd_eorca1_era5v1.id}/{r1i1c1f1_eorca1_era5v1.id}")

    # -- Add Items to NOC Near-Present Day eORCA025 ERA5v1 Sub-Catalog -- #
    # Define the store credentials for the eORCA025 ERA5v1 NPD data:
    bucket = "npd-eorca025-era5v1"

    # Open domain_cfg dataset from Icechunk repository:
    ds = open_icechunk_store(bucket=bucket, prefix="domain/domain_cfg", branch="main")

    item = create_item_with_icechunk_asset(
        ds=ds,
        id=f"noc-npd-era5/{bucket}/{ds.attrs.get('variant', 'r1i1c1f1')}/domain/domain_cfg",
        bucket=bucket,
        prefix="domain/domain_cfg",
        title="NPD eORCA025 ERA5v1 domain_cfg",
        description=description_from_prefix(prefix="domain/domain_cfg", ds=ds),
        start_date=start_date_str,
        end_date=end_date_str,
        collection=bucket
        )
    # Add item to the eORCA025 ERA5v1 NPD domain_cfg catalog:
    r1i1c1f1_eorca025_era5v1.add_item(item)

    for freq in ["1y", "1m", "5d"]:
        # Add root group for hierarchical Icechunk repository:
        ds = open_icechunk_store(bucket=bucket, prefix=f"eorca025-era5v1-{freq}", branch="main")
        ds_time = open_icechunk_store(bucket=bucket, prefix=f"eorca025-era5v1-{freq}", branch="main", group="gridT")
        item = create_item_with_icechunk_asset(
            ds=ds,
            id=f"noc-npd-era5/{bucket}/{ds.attrs.get('variant', 'r1i1c1f1')}/eorca025-era5v1-{freq}",
            bucket=bucket,
            prefix=f"eorca025-era5v1-{freq}",
            title=f"NPD eORCA025 ERA5v1 {freq} NEMODataTree",
            description=f"**{'Annual-mean' if freq == '1y' else 'Monthly-mean' if freq == '1m' else '5-day mean'} global ocean outputs.**",
            start_date=ds_time["time_counter"].dt.strftime("%Y-%m-%d").values[0],
            end_date=ds_time["time_counter"].dt.strftime("%Y-%m-%d").values[-1],
            collection=bucket,
            )
        # Add item to the eORCA025 ERA5v1 NPD global native model grid catalog:
        r1i1c1f1_eorca025_era5v1.add_item(item)

        # Add individual groups in hierarchical Icechunk repository:
        for prefix in ["T", "U", "V", "W"]:
            prefix_freq = f"{prefix}{freq}"
            # Open dataset from Icechunk repository:
            ds = open_icechunk_store(bucket=bucket, prefix=f"eorca025-era5v1-{freq}", branch="main", group=f"grid{prefix}")
            item = create_item_with_icechunk_asset(
                ds=ds,
                id=f"noc-npd-era5/{bucket}/{ds.attrs.get('variant', 'r1i1c1f1')}/{prefix_freq}",
                bucket=bucket,
                prefix=f"eorca025-era5v1-{freq}",
                title=f"NPD eORCA025 ERA5v1 NEMODataTree {prefix}-grid node",
                description=f"**{'Annual-mean' if freq == '1y' else 'Monthly-mean' if freq == '1m' else '5-day mean'} global ocean {'scalar' if prefix == 'T' else 'vector'} outputs defined at {prefix}-points.**",
                collection=bucket,
                group=f"grid{prefix}"
                )
            # Add item to the eORCA025 ERA5v1 NPD global native model grid catalog:
            r1i1c1f1_eorca025_era5v1.add_item(item)

    # Define the store credentials for the eORCA025 ERA5v1 NPD data:
    for prefix in ["M1m/MOVE_16N", "M1m/SAMBA_34_5S", "M1m/RAPID_26N", "M1m/OSNAP"]:
        # Open dataset from Icechunk repository:
        ds = open_icechunk_store(bucket=bucket, prefix=prefix, branch="main")

        item = create_item_with_icechunk_asset(
            ds=ds,
            id=f"noc-npd-era5/{bucket}/{ds.attrs.get('variant', 'r1i1c1f1')}/{prefix}",
            bucket=bucket,
            prefix=prefix,
            title=f"NPD eORCA025 ERA5v1 {prefix}",
            description=description_from_prefix(prefix=prefix, ds=ds),
            platform=ds.attrs.get('platform', 'tn'),
            start_date=start_date_str,
            end_date=end_date_str,
            collection=bucket
            )
        # Add item to the eORCA025 ERA5v1 NPD transect catalog:
        r1i1c1f1_eorca025_era5v1.add_item(item)

    logger.info(f"-> Completed: Added Items to STAC Catalog with ID: {npd_collection.id}/{npd_eorca025_era5v1.id}/{r1i1c1f1_eorca025_era5v1.id}")

    # -- Add Items to NOC Near-Present Day eORCA12 ERA5v1 Sub-Catalog -- #
    # Define the store credentials for the eORCA12 ERA5v1 NPD data:
    bucket = "npd-eorca12-era5v1"

    # Open domain_cfg dataset from Icechunk repository:
    ds = open_icechunk_store(bucket=bucket, prefix="domain/domain_cfg", branch="main")

    item = create_item_with_icechunk_asset(
        ds=ds,
        id=f"noc-npd-era5/{bucket}/{ds.attrs.get('variant', 'r1i1c1f1')}/domain/domain_cfg",
        bucket=bucket,
        prefix="domain/domain_cfg",
        title="NPD eORCA12 ERA5v1 domain_cfg",
        description=description_from_prefix(prefix="domain/domain_cfg", ds=ds),
        start_date=start_date_str,
        end_date=end_date_str,
        collection=bucket
        )
    # Add item to the eORCA12 ERA5v1 NPD domain_cfg catalog:
    r1i1c1f1_eorca12_era5v1.add_item(item)

    for freq in ["1y", "1m", "5d"]:
        # Add root group for hierarchical Icechunk repository:
        ds = open_icechunk_store(bucket=bucket, prefix=f"eorca12-era5v1-{freq}", branch="main")
        ds_time = open_icechunk_store(bucket=bucket, prefix=f"eorca12-era5v1-{freq}", branch="main", group="gridT")
        item = create_item_with_icechunk_asset(
            ds=ds,
            id=f"noc-npd-era5/{bucket}/{ds.attrs.get('variant', 'r1i1c1f1')}/eorca12-era5v1-{freq}",
            bucket=bucket,
            prefix=f"eorca12-era5v1-{freq}",
            title=f"NPD eORCA12 ERA5v1 {freq} NEMODataTree",
            description=f"**{'Annual-mean' if freq == '1y' else 'Monthly-mean' if freq == '1m' else '5-day mean'} global ocean outputs.**",
            start_date=ds_time["time_counter"].dt.strftime("%Y-%m-%d").values[0],
            end_date=ds_time["time_counter"].dt.strftime("%Y-%m-%d").values[-1],
            collection=bucket,
            )
        # Add item to the eORCA12 ERA5v1 NPD global native model grid catalog:
        r1i1c1f1_eorca12_era5v1.add_item(item)

        # Add individual groups in hierarchical Icechunk repository:
        for prefix in ["T", "U", "V", "W"]:
            prefix_freq = f"{prefix}{freq}"
            # Open dataset from Icechunk repository:
            ds = open_icechunk_store(bucket=bucket, prefix=f"eorca12-era5v1-{freq}", branch="main", group=f"grid{prefix}")
            if "time_counter" in ds:
                item = create_item_with_icechunk_asset(
                    ds=ds,
                    id=f"noc-npd-era5/{bucket}/{ds.attrs.get('variant', 'r1i1c1f1')}/{prefix_freq}",
                    bucket=bucket,
                    prefix=f"eorca12-era5v1-{freq}",
                    title=f"NPD eORCA12 ERA5v1 NEMODataTree {prefix}-grid node",
                    description=f"**{'Annual-mean' if freq == '1y' else 'Monthly-mean' if freq == '1m' else '5-day mean'} global ocean {'scalar' if prefix == 'T' else 'vector'} outputs defined at {prefix}-points.**",
                    collection=bucket,
                    group=f"grid{prefix}"
                    )
                # Add item to the eORCA12 ERA5v1 NPD global native model grid catalog:
                r1i1c1f1_eorca12_era5v1.add_item(item)

    # Define the store credentials for the eORCA12 ERA5v1 NPD data:
    for prefix in ["M1m/MOVE_16N", "M1m/SAMBA_34_5S", "M1m/RAPID_26N", "M1m/OSNAP"]:
        # Open dataset from Icechunk repository:
        ds = open_icechunk_store(bucket=bucket, prefix=prefix, branch="main")

        item = create_item_with_icechunk_asset(
            ds=ds,
            id=f"noc-npd-era5/{bucket}/{ds.attrs.get('variant', 'r1i1c1f1')}/{prefix}",
            bucket=bucket,
            prefix=prefix,
            title=f"NPD eORCA12 ERA5v1 {prefix}",
            description=description_from_prefix(prefix=prefix, ds=ds),
            platform=ds.attrs.get('platform', 'tn'),
            start_date=start_date_str,
            end_date=end_date_str,
            collection=bucket
            )
        # Add item to the eORCA12 ERA5v1 NPD transect catalog:
        r1i1c1f1_eorca12_era5v1.add_item(item)

    logger.info(f"-> Completed: Added Items to STAC Catalog with ID: {npd_collection.id}/{npd_eorca12_era5v1.id}/{r1i1c1f1_eorca12_era5v1.id}")

    # ==== Add Nested Catalogs to NOC Near-Present Day Collection ==== #

    # Model Simulation Variant Catalogs -> Model Simulation Catalogs:
    npd_eorca1_era5v1.add_child(r1i1c1f1_eorca1_era5v1)
    npd_eorca025_era5v1.add_child(r1i1c1f1_eorca025_era5v1)
    npd_eorca12_era5v1.add_child(r1i1c1f1_eorca12_era5v1)

    # Model Simulation Catalogs -> Near-Present Day Collection:
    npd_collection.add_child(npd_eorca1_era5v1)
    npd_collection.add_child(npd_eorca025_era5v1)
    npd_collection.add_child(npd_eorca12_era5v1)

    return npd_collection