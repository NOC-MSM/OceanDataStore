"""
send_npd_eorca1_era5v1_medusa_rivers_to_icechunk.py

Description:
This script writes NOC Near-Present Day output netCDF files
to a remote Icechunk repository in JASMIN cloud object storage.

Authors:
    - Ollie Tooth
"""
# === Import Dependencies === #
import argparse
import logging
import os

import numpy as np
import xarray as xr
import zarr
from nemo_cookbook import NEMODataTree

from OceanDataStore.cli import initialise_logging, send_to_icechunk, update_icechunk

logger = logging.getLogger(__name__)

# === Utility Functions === #
def add_ancillary_attrs(
    ds: xr.Dataset,
    grid_type: str="T"
    ) -> xr.Dataset:
    """
    Add attributes to NEMO model grid ancillary variables.

    Parameters
    ----------
    ds : xr.Dataset
        Input xarray.Dataset.
    grid_type : str, optional
        Type of NEMO grid to add ancillary attributes.
        Default is "T".

    Returns
    -------
    xr.Dataset
        xarray.Dataset with added ancillary variable attributes.
    """
    ugrid_type = grid_type.upper()
    lgrid_type = grid_type.lower()

    # Longitude:
    if f"glam{lgrid_type}." in ds:
        ds[f"glam{lgrid_type}."].encoding.update({"dtype": "float32"})
        ds[f"glam{lgrid_type}."].attrs["standard_name"] = "longitude"
        ds[f"glam{lgrid_type}."].attrs["long_name"] = f"Longitude of Ocean {ugrid_type}-Grid Points"
        ds[f"glam{lgrid_type}."].attrs["units"] = "degree_east"
    # Latitude:
    if f"gphit{lgrid_type}." in ds:
        ds[f"gphit{lgrid_type}."].encoding.update({"dtype": "float32"})
        ds[f"gphit{lgrid_type}."].attrs["standard_name"] = "latitude"
        ds[f"gphit{lgrid_type}."].attrs["long_name"] = f"Latitude of Ocean {ugrid_type}-Grid Points"
        ds[f"gphit{lgrid_type}."].attrs["units"] = "degree_north"
    # Depth:
    if f"depth{lgrid_type}." in ds:
        ds[f"depth{lgrid_type}."].encoding.update({"dtype": "float32"})
        ds[f"depth{lgrid_type}."].attrs["standard_name"] = "depth"
        ds[f"depth{lgrid_type}."].attrs["long_name"] = f"Depth of Ocean {ugrid_type}-Grid Points"
        ds[f"depth{lgrid_type}."].attrs["positive"] = "down"
        ds[f"depth{lgrid_type}."].attrs["units"] = "m"
    # Land-Sea Masks:
    if f"{lgrid_type}mask" in ds:
        ds[f"{lgrid_type}mask"].attrs["standard_name"] = "land_sea_mask"
        ds[f"{lgrid_type}mask"].attrs["long_name"] = f"Ocean {ugrid_type}-Grid Land-Sea Mask"
    if f"{lgrid_type}maskutil" in ds:
        ds[f"{lgrid_type}maskutil"].attrs["standard_name"] = "land_sea_unique_point_mask"
        ds[f"{lgrid_type}maskutil"].attrs["long_name"] = f"Ocean {ugrid_type}-Grid Land-Sea Unique Point Mask"
    # Grid Scale Factors:
    if f"e1{lgrid_type}" in ds:
        ds[f"e1{lgrid_type}"].attrs["standard_name"] = "cell_x_length"
        ds[f"e1{lgrid_type}"].attrs["long_name"] = f"Horizontal {ugrid_type}-Grid Scale Factor in X-Direction"
        ds[f"e1{lgrid_type}"].attrs["units"] = "m"
    if f"e2{lgrid_type}" in ds:
        ds[f"e2{lgrid_type}"].attrs["standard_name"] = "cell_y_length"
        ds[f"e2{lgrid_type}"].attrs["long_name"] = f"Horizontal {ugrid_type}-Grid Scale Factor in Y-Direction"
        ds[f"e2{lgrid_type}"].attrs["units"] = "m"
    if f"e3{lgrid_type}" in ds:
        ds[f"e3{lgrid_type}"].attrs["standard_name"] = "cell_thickness"
        ds[f"e3{lgrid_type}"].attrs["long_name"] = f"Vertical {ugrid_type}-Grid Scale Factor in Z-Direction"
        ds[f"e3{lgrid_type}"].attrs["units"] = "m"

    return ds

# === Main Function === #
def main(store_credentials_json: str,
         datestr: str = "197601",
         frequency: str = "1y",
         group_list: list | None = None,
         mode: str = "send",
         exists: bool = False
         ) -> None:
    """
    Send NEMO output netCDF files to a material NEMODataTree
    stored in an Icechunk Repository in JASMIN OS.

    Parameters
    ----------
    store_credentials_json : str
        Path to JSON file containing Icechunk Repository credentials.
    datestr : str, optional
        Date string of NEMO output netCDF files used
        to identify the specific files to send via "YYYY" or "YYYYMM".
        Default is "197601" -> 1976-01.
    frequency : str, optional
        Frequency of NEMO output netCDF files. Default is "1y" -> annual mean.
    group_list : list, optional
        List of NEMODataTree grid nodes to send to Icechunk Repository.
        Default is ["gridT", "gridU", "gridV", "gridW", "gridF"].
    mode : str, optional
        Mode of operation for writing data to Icechunk Repository.
        Options are "send" (default) or "update".
    exists : bool, optional
        Flag indicating whether the Icechunk Repository already exists.
        Default is False.

    Returns
    -------
    None
    """
    # === Initialize logging === #
    initialise_logging()

    # === Open NOC Near-Present Day domain configuration files === #
    # Define simulation output data directory:
    data_dir = "/dssgfs01/working/jpp1m13/STORE-OUT/OUT_NPD_SPUN_eORCA1-MEDUSA_river"
    ds_dom_parent = xr.open_dataset("/dssgfs01/scratch/npd/simulations/eORCA1_ERA5_v1/eORCA1_ERA5v1_domain_cfg_mesh_mask.nc").squeeze(drop=True)

    logger.info("Completed: Opened NEMO parent domain_cfg files.")

    # === Open NOC Near-Present Day netCDF files === #
    # MEDUSA BGC variables on NEMO T-points:
    ds_diad_parent = xr.open_mfdataset(f"{data_dir}/????/eORCA1_ERA5_{frequency}_diad_{datestr}*.nc",
                                       data_vars="all",
                                       chunks={}
                                       )

    logger.info(f"Completed: Opened MEDUSA diad {frequency} netCDF files.")

    ds_ptrc_parent = xr.open_mfdataset(f"{data_dir}/????/eORCA1_ERA5_{frequency}_ptrc_{datestr}*.nc",
                                       data_vars="all",
                                       chunks={}
                                       )

    logger.info(f"Completed: Opened MEDUSA ptrc {frequency} netCDF files.")

    # Merge gridT and MEDUSA BGC variables for convenience:
    ds_gridT_parent = xr.merge([ds_diad_parent, ds_ptrc_parent], compat="override")

    logger.info(f"Completed: Merged NEMO gridT and MEDUSA BGC {frequency} netCDF files.")

    # === Create NEMODataTree from NEMO model datasets === #
    # Define datasets dictionary for NEMODataTree:
    datasets = {"parent": {"domain": ds_dom_parent,
                           "gridT": ds_gridT_parent,
                           },
                }

    # Create NEMODataTree - building land-sea masks on-the-fly:
    nemo = NEMODataTree.from_datasets(datasets=datasets,
                                      nests=None,
                                      iperio=True,
                                      nftype="F",
                                      vco_ref=False,
                                      read_mask=True,
                                      )
    
    logger.info(f"Completed: Created NEMODataTree from NEMO model datasets for {frequency} data.")

    # === Write NEMODataTree to Icechunk Repository === #
    bucket = "npd-eorca1-era5v1"
    prefix = f"eorca1-medusa-river-era5v1-{frequency}"
    variable_commits = True
    config_kwargs = {
            "temporary_directory":f"{os.getcwd()}/{frequency}/",
            "local_directory":f"{os.getcwd()}/{frequency}/"
        }
    cluster_kwargs = {
            "n_workers" : 20,
            "threads_per_worker" : 1,
            "memory_limit":"6GB"
        }

    if group_list is None:
        group_list = ["gridT", "gridU", "gridV", "gridW", "gridF"]

    for group in group_list:
        logger.info(f"In Progress: Sending {group} to Icechunk Repository: {bucket}/{prefix}")
        # Extract NEMODataTree grid node as xarray.Dataset:
        ds = add_ancillary_attrs(nemo[group].to_dataset(), grid_type=group[-1])

        # Update variable encodings:
        blosccodec = zarr.codecs.BloscCodec(cname="zstd", clevel=3, shuffle="shuffle")
        for var in list(ds.data_vars) + list(ds.coords):
            # Set variable compression:
            ds[var].encoding.clear()
            ds[var].encoding['compressors'] = [blosccodec]

            # Rechunking by variable dimensionality:
            if ds[var].dims == ("j", "i"):
                ds[var] = ds[var].chunk({"j": 331, "i": 360})
            elif ds[var].dims == ("time_counter", "j", "i"):
                ds[var] = ds[var].chunk({"time_counter": 1, "j": 331, "i": 360})
            elif ds[var].dims == ("time_counter", "ncatice", "j", "i"):
                ds[var] = ds[var].chunk({"time_counter": 1, "ncatice": 5, "j": 331, "i": 360})
            elif ds[var].dims == ("time_counter", "k", "j", "i"):
                ds[var] = ds[var].chunk({"time_counter": 1, "k": 25, "j": 331, "i": 360})

        # Remove Dataset global attributes:
        ds.attrs.clear()

        # Define commit message for Icechunk Repository:
        time_start = np.datetime_as_string(ds["time_counter"][0].values, unit='D')
        time_end = np.datetime_as_string(ds["time_counter"][-1].values, unit='D')
        commit_message = f"Added NOC Near-Present Day eORCA1 {group} {frequency} ({time_start} - {time_end})"

        # Send xarray.Dataset to Icechunk Repository:
        if mode == "send":
            send_to_icechunk(
                file=ds,
                bucket=bucket,
                object_prefix=prefix,
                store_credentials_json=store_credentials_json,
                exists=exists,
                group=group,
                variables=None,
                append_dim='time_counter',
                grid_filepath=None,
                update_coords=None,
                rechunk=None,
                attrs=None,
                branch="main",
                commit_message=commit_message,
                variable_commits=variable_commits,
                dask_config_kwargs=config_kwargs,
                dask_cluster_kwargs=cluster_kwargs,
                icechunk_config=None,
                )

        # Update existing xarray.Dataset in Icechunk Repository:
        elif mode == "update":
            update_icechunk(
                file=ds,
                bucket=bucket,
                object_prefix=prefix,
                store_credentials_json=store_credentials_json,
                group=group,
                variables=None,
                append_dim='time_counter',
                grid_filepath=None,
                update_coords=None,
                rechunk=None,
                attrs=None,
                branch="main",
                commit_message=commit_message,
                dask_config_kwargs=config_kwargs,
                dask_cluster_kwargs=cluster_kwargs,
                icechunk_config=None,
                )
        
        # Update exists flag to True following first NEMODataTree grid node:
        if (mode == "send") and (exists is False):
            exists = True
        logger.info(f"Completed: Sent {group} to Icechunk Repository: {bucket}/{prefix}")


if __name__ == "__main__":
    # =========== INPUTS =========== #
    parser = argparse.ArgumentParser(
        description="Send NEMO output netCDF files to NEMODataTree stored in an Icechunk Repository in JASMIN OS."
    )
    parser.add_argument(
        "--credentials",
        type=str,
        help="Path to the JSON file containing JASMIN OS credentials",
    )
    parser.add_argument(
        "--datestr",
        type=str,
        default="1976",
        help="Date string of the output dataset in 'YYYY' or 'YYYYMM' format",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="send",
        help="Mode of operation: 'send' or 'update'",
    )
    parser.add_argument(
        "--exists",
        action="store_true",
        help="Flag indicating whether the Icechunk Repository already exists",
    )
    parser.add_argument(
        "--frequency",
        type=str,
        default="1y",
        help="Frequency of the output dataset: '1y', '1m', or '5d'",
    )
    parser.add_argument(
        "--group_list",
        type=str,
        nargs="+",
        default=["gridT", "gridU", "gridV", "gridW", "gridF"],
        help="List of NEMODataTree grid nodes to send to Icechunk Repository",
    )

    # Parse command-line arguments
    args = parser.parse_args()

    # =========== MAIN =========== #
    main(store_credentials_json=args.credentials,
         datestr=args.datestr,
         frequency=args.frequency,
         group_list=args.group_list,
         mode=args.mode,
         exists=args.exists
         )
