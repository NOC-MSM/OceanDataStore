"""
create_ods_stac.py

Description:
Script to define the National Oceanography Centre (NOC)
OceanDataStore Spatio-Temporal Asset Catalog and write
to JSON files.

Authors:
    - Ollie Tooth (oliver.tooth@noc.ac.uk)
"""
# -- Import Python Modules -- #
import datetime
import logging
import os

import pystac

from OceanDataStore.catalog.stac import (
    create_armor3d_collection,
    create_en4_collection,
    create_era5_collection,
    create_hadisst_collection,
    create_lops_collection,
    create_npd_era5_collection,
    create_npd_jra55_collection,
    create_nsidc_collection,
    create_oisst_collection,
    create_ostia_collection,
    create_rapid_evo_collection,
    create_woa23_collection,
)
from OceanDataStore.cli import initialise_logging

logger = logging.getLogger(__name__)

def create_ods_stac():
    """
    Create the OceanDataStore STAC and write to JSON files.
    """
    # =========== Configure OceanDataStore Logging =========== #
    initialise_logging()

    # =========== Define ODS STAC =========== #
    date = datetime.datetime.now(tz=datetime.timezone.utc)
    ods_stac = pystac.Catalog(id="ods-stac",
                            title="OceanDataStore Spatio-Temporal Asset Catalog",
                            description="OceanDataStore Spatio-Temporal Asset Catalog for Ocean Model and Observational Data.\n\n**About:**\n\nThe National Oceanography Centre (NOC) is one of the world's leading oceanographic institutions and has been in existence, in its various forms, for over six decades.\nWe undertake world-leading research from coastal seas to deep water, to enhance understanding of the ocean and to address critical environmental challenges.\n\n**Links:**\n- [Website](https://noc.ac.uk)\n- [OceanDataStore](https://noc-msm.github.io/OceanDataStore/)",
                            stac_extensions=None,
                            extra_fields={
                                "last_update": date.isoformat(timespec="hours"),
                                "catalog_version": f"{date.year}.{date.month:02}.{date.day:02}",
                                "contacts": "Oliver Tooth (oliver.tooth@noc.ac.uk), Adam Blaker (atb299@noc.ac.uk), Andrew Coward (acc@noc.ac.uk)",
                                },
                            )

    logger.info(f"Completed: Created ODS STAC Catalog with ID: {ods_stac.id}")

    # -- Add Rapid-Evolution Collection to ODS STAC Catalog -- #
    rapid_evo_collection = create_rapid_evo_collection()
    ods_stac.add_child(rapid_evo_collection)

    # -- Add NOC Near-Present Day JRA55-do Collection to ODS STAC Catalog -- #
    npd_jra55v1_collection = create_npd_jra55_collection()
    ods_stac.add_child(npd_jra55v1_collection)

    # -- Add NOC Near-Present Day ERA5 Collection to ODS STAC Catalog -- #
    npd_era5v1_collection = create_npd_era5_collection()
    ods_stac.add_child(npd_era5v1_collection)

    logger.info(f"Completed: Added NOC Near-Present Day Collections to ODS STAC: {ods_stac.id}")

    # -- Add NSIDC Sea Ice Index Collection to ODS STAC Catalog -- #
    nsidc_collection = create_nsidc_collection()
    ods_stac.add_child(nsidc_collection)

    # -- Add WOA23 Collection to ODS STAC Catalog -- #
    woa23_collection = create_woa23_collection()
    ods_stac.add_child(woa23_collection)

    # -- Add OISST Collection to ODS STAC Catalog -- #
    oisst_collection = create_oisst_collection()
    ods_stac.add_child(oisst_collection)

    # -- Add EN4.2.2 Collection to ODS STAC Catalog -- #
    en4_collection = create_en4_collection()
    ods_stac.add_child(en4_collection)

    # -- Add ARMOR3D Collection to ODS STAC Catalog -- #
    armor3d_collection = create_armor3d_collection()
    ods_stac.add_child(armor3d_collection)

    # -- Add HadISST1 Collection to ODS STAC Catalog -- #
    hadisst_collection = create_hadisst_collection()
    ods_stac.add_child(hadisst_collection)

    # -- Add ERA5 Collection to ODS STAC Catalog -- #
    era5_collection = create_era5_collection()
    ods_stac.add_child(era5_collection)

    # -- Add OSTIA Collection to ODS STAC Catalog -- #
    ostia_collection = create_ostia_collection()
    ods_stac.add_child(ostia_collection)

    # -- Add LOPS Collection to ODS STAC Catalog -- #
    lops_collection = create_lops_collection()
    ods_stac.add_child(lops_collection)

    logger.info(f"Completed: Added Ocean Observation Collections to ODS STAC: {ods_stac.id}")

    # -- Write ODS STAC Catalog to local filesystem -- #
    logger.info(f"ODS STAC {ods_stac.id} Summary:")
    print(ods_stac.describe())

    ods_stac.normalize_hrefs(root_href="https://noc-msm-o.s3-ext.jc.rl.ac.uk/ods-stac/")
    ods_stac.save(catalog_type=pystac.CatalogType.RELATIVE_PUBLISHED, dest_href=os.path.join(os.getcwd(), "ods-stac"))
    logger.info(f"Completed: Write ODS STAC to -> {os.path.join(os.getcwd(), 'ods-stac')}")

if __name__ == "__main__":
    # -- Create OceanDataStore STAC Catalog -- #
    create_ods_stac()
