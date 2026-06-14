# =========================================================
# send_NSIDC_SII_v4.0_to_os.py
#
# Script to write NSIDC Sea Ice Index version 4.0 to
# Icechunk repositories in JASMIN cloud object storage.
#
# Created By: Ollie Tooth (oliver.tooth@noc.ac.uk)
# =========================================================
import logging

import xarray as xr
import zarr

from OceanDataStore.cli import send_to_icechunk, initialise_logging

logger = logging.getLogger(__name__)


def main():
    # ========== Initialise OceanDataStore Logging ========== #
    initialise_logging()

    # ========== Prepare Data ========== #
    # Open NSIDC Sea Ice Index v4.0 datasets:
    ds_si_arctic = xr.open_dataset("/dssgfs01/scratch/otooth/npd_data/observations/NSIDC/NSIDC_Sea_Ice_Index_v4_Arctic_combined_1978_2025.nc")

    ds_si_antarctic = xr.open_dataset("/dssgfs01/scratch/otooth/npd_data/observations/NSIDC/NSIDC_Sea_Ice_Index_v4_Antarctic_combined_1978_2025.nc")

    # Optimise chunk sizes for spatial analysis:
    ds_si_arctic = ds_si_arctic.chunk({'time': 12, 'y': 448, 'x': 304})
    ds_si_antarctic = ds_si_antarctic.chunk({'time': 12, 'y': 332, 'x': 316})

    # Update variable encodings:
    blosccodec = zarr.codecs.BloscCodec(cname="zstd", clevel=3, shuffle=zarr.codecs.BloscShuffle.shuffle)
    for var in list(ds_si_arctic.data_vars) + list(ds_si_arctic.coords):
        ds_si_arctic[var].encoding['compressors'] = [blosccodec]
    for var in list(ds_si_antarctic.data_vars) + list(ds_si_antarctic.coords):
        ds_si_antarctic[var].encoding['compressors'] = [blosccodec]

    # Update global CF-metadata attributes:
    ds_si_arctic.attrs.clear()
    ds_si_arctic = ds_si_arctic.assign_attrs({
        "Conventions": "CF-1.6",
        "title": "NSIDC Sea Ice Index, Version 4 - Arctic",
        "description": "NSIDC Sea Ice Index version 4.0 - Arctic sea ice area fraction, sea ice extent and total sea ice area timeseries.",
        "source": "Satellite observations: Sea Ice Concentrations from Nimbus-7 SMMR and DMSP SSM/I-SSMIS Passive Microwave Data (GSFC). AMSR2 Daily Polar Gridded Sea Ice Concentrations (AMSR2).",
        "dataset_type": "observation",
        "product_type": "timeseries",
        "product_version" : "1.0",
        "institution": "National Snow and Ice Data Center; Cooperative Institute for Research in Environmental Sciences; University of Colorado at Boulder; Boulder, CO",
        "citation": "Fetterer, F., Knowles, K., Meier, W. N., Savoie, M., Windnagel, A. K. & Stafford, T. (2025). Sea Ice Index. (G02135, Version 4). [Data Set]. Boulder, Colorado USA. National Snow and Ice Data Center. https://doi.org/10.7265/a98x-0f50. Date Accessed 05-29-2026.",
        "references": "Windnagel, A., Stafford, T., Fetterer, F., Meier, W. (2025). Sea Ice Index Version 4 Analysis. NSIDC Special Report 28. Boulder CO, USA: National Snow and Ice Data Center.",
        "acknowledgement": "These data are produced and supported by the NASA National Snow and Ice Data Center Distributed Active Archive Center.",
        "license": "NSIDC Sea Ice Index, Version 4 data were obtained from https://nsidc.org/data/g02135/versions/4 and are provided under a U.S. Government Works License https://www.usa.gov/government-works",
        "doi": "10.7265/a98x-0f50",
        "platform": "gn",
        "horizontal_grid_type": "curvilinear",
        "horizontal_grid_resolution": "25 km",
        "aggregation": "mean",
        "aggregation_frequency": "monthly",
        "status": "ongoing",
        "update_frequency": "quarterly",
        "bbox": "[-180.0, 180.0, 30.98, 90.0]",
    })

    ds_si_antarctic.attrs.clear()
    ds_si_antarctic = ds_si_antarctic.assign_attrs({
        "Conventions": "CF-1.6",
        "title": "NSIDC Sea Ice Index, Version 4 - Antarctic",
        "description": "NSIDC Sea Ice Index, Version 4 - Antarctic sea ice area fraction, sea ice extent and total sea ice area timeseries.",
        "source": "Satellite observations: Sea Ice Concentrations from Nimbus-7 SMMR and DMSP SSM/I-SSMIS Passive Microwave Data (GSFC). AMSR2 Daily Polar Gridded Sea Ice Concentrations (AMSR2).",
        "dataset_type": "observation",
        "product_type": "timeseries",
        "product_version" : "1.0",
        "institution": "National Snow and Ice Data Center; Cooperative Institute for Research in Environmental Sciences; University of Colorado at Boulder; Boulder, CO",
        "citation": "Fetterer, F., Knowles, K., Meier, W. N., Savoie, M., Windnagel, A. K. & Stafford, T. (2025). Sea Ice Index. (G02135, Version 4). [Data Set]. Boulder, Colorado USA. National Snow and Ice Data Center. https://doi.org/10.7265/a98x-0f50. Date Accessed 05-29-2026.",
        "references": "Windnagel, A., Stafford, T., Fetterer, F., Meier, W. (2025). Sea Ice Index Version 4 Analysis. NSIDC Special Report 28. Boulder CO, USA: National Snow and Ice Data Center.",
        "acknowledgement": "These data are produced and supported by the NASA National Snow and Ice Data Center Distributed Active Archive Center.",
        "license": "NSIDC Sea Ice Index, Version 4 data were obtained from https://nsidc.org/data/g02135/versions/4 and are provided under a U.S. Government Works License https://www.usa.gov/government-works",
        "doi": "10.7265/a98x-0f50",
        "platform": "gn",
        "horizontal_grid_type": "curvilinear",
        "horizontal_grid_resolution": "25 km",
        "aggregation": "mean",
        "aggregation_frequency": "monthly",
        "status": "ongoing",
        "update_frequency": "quarterly",
        "bbox": "[-180.0, 180.0, -90.0, -39.23089]",
    })

    # ========== Send to Icechunk Repository ========== #
    bucket = "nsidc"
    exists = False
    store_credentials_json = ".../credentials/jasmin_os_credentials.json"
    branch = "main"
    variable_commits = True
    config_kwargs = {
            "temporary_directory":".../OceanDataStore/OceanDataStore/data/NSIDC/",
            "local_directory":".../OceanDataStore/OceanDataStore/data/NSIDC/"
        }
    cluster_kwargs = {
            "n_workers" : 10,
            "threads_per_worker" : 1,
            "memory_limit":"3GB"
        }

    # -- Sea Ice Index v4.0 - Arctic -- #
    send_to_icechunk(
        file=ds_si_arctic,
        bucket=bucket,
        object_prefix="nsidc_sea_ice_index_v4_arctic_monthly",
        store_credentials_json=store_credentials_json,
        exists=exists,
        append_dim='time',
        attrs=ds_si_arctic.attrs,
        branch=branch,
        commit_message="Added NSIDC Sea Ice Index version 4 - Arctic (1978-01-2025-12).",
        variable_commits=variable_commits,
        dask_config_kwargs=config_kwargs,
        dask_cluster_kwargs=cluster_kwargs,
        )
    
    # -- Sea Ice Index v4.0 - Antarctic -- #
    send_to_icechunk(
        file=ds_si_antarctic,
        bucket=bucket,
        object_prefix="nsidc_sea_ice_index_v4_antarctic_monthly",
        store_credentials_json=store_credentials_json,
        exists=exists,
        append_dim='time',
        attrs=ds_si_antarctic.attrs,
        branch=branch,
        commit_message="Added NSIDC Sea Ice Index version 4 - Antarctic (1978-01-2025-12).",
        variable_commits=variable_commits,
        dask_config_kwargs=config_kwargs,
        dask_cluster_kwargs=cluster_kwargs,
        )

if __name__ == "__main__":
    main()
