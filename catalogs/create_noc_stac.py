"""
create_noc_stac.py

Description:
Script to define the National Oceanography Centre (NOC)
Spatio-Temporal Access Catalog and write to JSON files.

Authors:
    - Ollie Tooth
"""
# -- Import Python Modules -- #
import os
import sys
import logging
import pystac
import datetime

from npd_collections import create_npd_jra55_collection, create_npd_era5_collection
from rapid_evo_collection import create_rapid_evo_collection
from utils import create_logging_banner, initialise_logging

def create_noc_stac():
    """
    Create the NOC Model STAC and write to JSON files.
    """
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

    logging.info(f"Completed: Created NOC STAC Catalog with ID: {noc_stac.id}")

    # -- Create & Add Rapid-EVO Collection to NOC STAC Catalog -- #
    rapid_evo_collection = create_rapid_evo_collection()
    noc_stac.add_child(rapid_evo_collection)

    # -- Create & Add NOC Near-Present Day Collection to NOC STAC Catalog -- #
    npd_jra55v1_collection = create_npd_jra55_collection()
    noc_stac.add_child(npd_jra55v1_collection)

    npd_era5v1_collection = create_npd_era5_collection()
    noc_stac.add_child(npd_era5v1_collection)

    logging.info(f"Completed: Added NOC Near-Present Day Collection Catalogs to NOC STAC: {noc_stac.id}")

    # -- Write NOC Model STAC Catalog to local filesystem -- #
    logging.info(f"NOC STAC {noc_stac.id} Summary:")
    print(noc_stac.describe())

    noc_stac.normalize_hrefs(root_href="https://noc-msm-o.s3-ext.jc.rl.ac.uk/noc-model-stac/")
    noc_stac.save(catalog_type=pystac.CatalogType.SELF_CONTAINED, dest_href=os.path.join(os.getcwd(), "noc-model-stac"))
    logging.info(f"Completed: Write NOC STAC to -> {os.path.join(os.getcwd(), 'noc-model-stac')}")

if __name__ == "__main__":
    # -- Configure Logging -- #
    logger = logging.getLogger(__name__)

    initialise_logging(logger)
    create_logging_banner(logger)

    # -- Create NOC Model STAC Catalog -- #
    try:
        create_noc_stac()
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)