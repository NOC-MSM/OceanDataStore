"""
create_noc_stac.py

Description:
Script to define the National Oceanography Centre (NOC)
Spatio-Temporal Access Catalog and write to JSON files.

Authors:
    - Ollie Tooth (oliver.tooth@noc.ac.uk)
"""
# -- Import Python Modules -- #
import os
import sys
import logging
import pystac
import datetime

from OceanDataStore.catalog.stac import create_npd_era5_collection
from OceanDataStore.catalog.stac import create_npd_jra55_collection
from OceanDataStore.catalog.stac import create_rapid_evo_collection
from OceanDataStore.catalog.stac.utils import create_logging_banner, initialise_logging

def create_noc_stac():
    """
    Create the NOC STAC and write to JSON files.
    """
    # -- Define NOC STAC Base Catalog -- #
    noc_stac = pystac.Catalog(id="noc-stac",
                            title="NOC STAC Catalog",
                            description="National Oceanography Centre Spatio-Temporal Asset Catalog for Ocean Model and Observational Data.\n\n**About:**\n\nThe National Oceanography Centre (NOC) is one of the world's leading oceanographic institutions and has been in existence, in its various forms, for over six decades.\nWe undertake world-leading research from coastal seas to deep water, to enhance understanding of the ocean and to address critical environmental challenges.\n\n**Links:**\n- [Website](https://noc.ac.uk)\n- [OceanDataStore](https://noc-msm.github.io/OceanDataStore/)",
                            stac_extensions=None,
                            extra_fields={
                                "last_update": datetime.datetime.now().isoformat(timespec="hours"),
                                "catalog_version": "0.2.0",
                                "contacts": "Oliver Tooth (oliver.tooth@noc.ac.uk), Adam Blaker (atb299@noc.ac.uk), Andrew Coward (acc@noc.ac.uk)",
                                },
                            )

    logging.info(f"Completed: Created NOC STAC Catalog with ID: {noc_stac.id}")

    # -- Create & Add Rapid-EVO Collection to NOC STAC Catalog -- #
    rapid_evo_collection = create_rapid_evo_collection()
    noc_stac.add_child(rapid_evo_collection)

    # -- Create & Add NOC Near-Present Day JRA55-do Collection to NOC STAC Catalog -- #
    npd_jra55v1_collection = create_npd_jra55_collection()
    noc_stac.add_child(npd_jra55v1_collection)

    # -- Create & Add NOC Near-Present Day ERA5 Collection to NOC STAC Catalog -- #
    npd_era5v1_collection = create_npd_era5_collection()
    noc_stac.add_child(npd_era5v1_collection)

    logging.info(f"Completed: Added NOC Near-Present Day Collection Catalogs to NOC STAC: {noc_stac.id}")

    # -- Write NOC STAC Catalog to local filesystem -- #
    logging.info(f"NOC STAC {noc_stac.id} Summary:")
    print(noc_stac.describe())

    noc_stac.normalize_hrefs(root_href="https://noc-msm-o.s3-ext.jc.rl.ac.uk/noc-stac/")
    noc_stac.save(catalog_type=pystac.CatalogType.SELF_CONTAINED, dest_href=os.path.join(os.getcwd(), "noc-stac"))
    logging.info(f"Completed: Write NOC STAC to -> {os.path.join(os.getcwd(), 'noc-stac')}")

if __name__ == "__main__":
    # -- Configure Logging -- #
    logger = logging.getLogger(__name__)

    initialise_logging(logger)
    create_logging_banner(logger)

    # -- Create NOC STAC Catalog -- #
    try:
        create_noc_stac()
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)