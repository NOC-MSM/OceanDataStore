"""
create_noc_stac.py

Description:
Script to define the National Oceanography Centre (NOC)
Spatio-Temporal Access Catalog and write to JSON files.

Authors:
    - Ollie Tooth (oliver.tooth@noc.ac.uk)
"""
# -- Import Python Modules -- #
import datetime
import logging
import os

import pystac

from OceanDataStore.catalog.stac import (
    create_npd_era5_collection,
    create_npd_jra55_collection,
    create_rapid_evo_collection,
    create_nsidc_collection,
    create_woa23_collection,
    create_oisst_collection,
    create_en4_collection,
    create_armor3d_collection,
    create_hadisst_collection,
    create_era5_collection
)
from OceanDataStore.cli import initialise_logging

logger = logging.getLogger(__name__)

def create_noc_stac():
    """
    Create the NOC STAC and write to JSON files.
    """
    # =========== Configure OceanDataStore Logging =========== #
    initialise_logging()

    # =========== Define NOC STAC =========== #
    noc_stac = pystac.Catalog(id="noc-stac",
                            title="NOC STAC Catalog",
                            description="National Oceanography Centre Spatio-Temporal Asset Catalog for Ocean Model and Observational Data.\n\n**About:**\n\nThe National Oceanography Centre (NOC) is one of the world's leading oceanographic institutions and has been in existence, in its various forms, for over six decades.\nWe undertake world-leading research from coastal seas to deep water, to enhance understanding of the ocean and to address critical environmental challenges.\n\n**Links:**\n- [Website](https://noc.ac.uk)\n- [OceanDataStore](https://noc-msm.github.io/OceanDataStore/)",
                            stac_extensions=None,
                            extra_fields={
                                "last_update": datetime.datetime.now().isoformat(timespec="hours"),
                                "catalog_version": "0.3.0",
                                "contacts": "Oliver Tooth (oliver.tooth@noc.ac.uk), Adam Blaker (atb299@noc.ac.uk), Andrew Coward (acc@noc.ac.uk)",
                                },
                            )

    logging.info(f"Completed: Created NOC STAC Catalog with ID: {noc_stac.id}")

    # -- Add Rapid-Evolution Collection to NOC STAC Catalog -- #
    rapid_evo_collection = create_rapid_evo_collection(credentials_json="/dssgfs01/working/otooth/AtlantiS/credentials/rapid_evo_credentials.json")
    noc_stac.add_child(rapid_evo_collection)

    # -- Add NOC Near-Present Day JRA55-do Collection to NOC STAC Catalog -- #
    npd_jra55v1_collection = create_npd_jra55_collection()
    noc_stac.add_child(npd_jra55v1_collection)

    # -- Add NOC Near-Present Day ERA5 Collection to NOC STAC Catalog -- #
    npd_era5v1_collection = create_npd_era5_collection()
    noc_stac.add_child(npd_era5v1_collection)

    logging.info(f"Completed: Added NOC Near-Present Day Collections to NOC STAC: {noc_stac.id}")

    # -- Add NSIDC Sea Ice Index Collection to NOC STAC Catalog -- #
    nsidc_collection = create_nsidc_collection()
    noc_stac.add_child(nsidc_collection)

    # -- Add WOA23 Collection to NOC STAC Catalog -- #
    woa23_collection = create_woa23_collection()
    noc_stac.add_child(woa23_collection)

    # -- Add OISST Collection to NOC STAC Catalog -- #
    oisst_collection = create_oisst_collection()
    noc_stac.add_child(oisst_collection)

    # -- Add EN4.2.2 Collection to NOC STAC Catalog -- #
    en4_collection = create_en4_collection()
    noc_stac.add_child(en4_collection)

    # -- Add ARMOR3D Collection to NOC STAC Catalog -- #
    armor3d_collection = create_armor3d_collection()
    noc_stac.add_child(armor3d_collection)

    # -- Add HadISST1 Collection to NOC STAC Catalog -- #
    hadisst_collection = create_hadisst_collection()
    noc_stac.add_child(hadisst_collection)

    # -- Add ERA5 Collection to NOC STAC Catalog -- #
    era5_collection = create_era5_collection()
    noc_stac.add_child(era5_collection)

    logging.info(f"Completed: Added Ocean Observation Collections to NOC STAC: {noc_stac.id}")

    # -- Write NOC STAC Catalog to local filesystem -- #
    logging.info(f"NOC STAC {noc_stac.id} Summary:")
    print(noc_stac.describe())

    noc_stac.normalize_hrefs(root_href="https://noc-msm-o.s3-ext.jc.rl.ac.uk/noc-stac/")
    noc_stac.save(catalog_type=pystac.CatalogType.RELATIVE_PUBLISHED, dest_href=os.path.join(os.getcwd(), "noc-stac"))
    logging.info(f"Completed: Write NOC STAC to -> {os.path.join(os.getcwd(), 'noc-stac')}")

if __name__ == "__main__":
    # -- Create NOC STAC Catalog -- #
    create_noc_stac()
