"""
main_cli.py

Description:
This module defines the command line interface
for the OceanDataStore package.

Authors:
    - Joao Morado
    - Tobias Ferreira
    - Ollie Tooth
"""
import sys
import json
import logging

from ..object_store_handler import send_to_zarr, send_to_icechunk, update_zarr, update_icechunk, list_objects
from .argument_parser import __version__, create_parser

logger = logging.getLogger(__name__)


def banner():
    """Log the OceanDataStore banner."""
    logger.info(
        f"""
          .-~~~-.
  .- ~ ~-(       )_ _
 /                    ~ -.
~      OceanDataStore     ',
\                         .'
 - ._ ,. ,.,.,., ,.. -~ ~ '
        '       '
    version: {__version__}

""",
        extra={"simple": True},
    )


def initialise_logging():
    """Initialise logging configuration."""
    logging.basicConfig(
        stream=sys.stdout,
        format="☁  OceanDataStore  ☁  | %(levelname)10s | %(asctime)s | %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def process_action(args):
    """Process the selected action."""
    if len(sys.argv) == 1:
        args.parser.print_help()
        sys.exit(0)

    # === Process Arguments === #
    if args.variables is not None:
        variables = list(args.variables)
    else:
        variables = None

    if args.filepaths is not None:
        if len(args.filepaths) > 1:
            filepaths = list(args.filepaths)
        else:
            filepaths = args.filepaths

    if args.zarr_version is not None:
        zarr_version = int(args.zarr_version)

    if args.dask_config_json is None:
        dask_config = {
            "config_kwargs": None,
            "cluster_kwargs": None,
        }
    else:
        dask_config = json.load(open(args.dask_config_json))
        if "config_kwargs" not in dask_config:
            raise ValueError("config_kwargs not found in Dask configuration.")
        if "cluster_kwargs" not in dask_config:
            raise ValueError("cluster_kwargs not found in Dask configuration.")

    if args.icechunk_config_json is None:
        # Default: use Icechunk configuration for JASMIN OS:
        icechunk_config = {
            "storage_config_kwargs": {"region": "", "force_path_style": True},
            "repository_config_kwargs": {},
            "storage_settings_kwargs": {"unsafe_use_conditional_update": False, "unsafe_use_conditional_create": False},
        }
    else:
        icechunk_config = json.load(open(args.icechunk_config_json))
        if "storage_config_kwargs" not in icechunk_config:
            raise ValueError("storage_config_kwargs not found in Icechunk configuration.")
        if "repository_config_kwargs" not in icechunk_config:
            raise ValueError("repository_config_kwargs not found in Icechunk configuration.")
        if "storage_settings_kwargs" not in icechunk_config:
            raise ValueError("storage_settings_kwargs not found in Icechunk configuration.")

    # === Process Actions === #
    if args.action == "send_to_zarr":

        send_to_zarr(
            file=filepaths,
            bucket=args.bucket,
            object_prefix=args.object_prefix,
            store_credentials_json=args.store_credentials_json,
            variables=variables,
            append_dim=args.append_dim,
            send_vars_indep=args.var_stores,
            grid_filepath=args.grid_filepath,
            update_coords=args.update_coords,
            rechunk=args.chunk_strategy,
            attrs=args.attrs,
            dask_config_kwargs=dask_config["config_kwargs"],
            dask_cluster_kwargs=dask_config["cluster_kwargs"],
            zarr_version=zarr_version,
        )
    
    elif args.action == "update_zarr":

        update_zarr(
            file=filepaths,
            bucket=args.bucket,
            object_prefix=args.object_prefix,
            store_credentials_json=args.store_credentials_json,
            variables=variables,
            send_vars_indep=args.var_stores,
            append_dim=args.append_dim,
            grid_filepath=args.grid_filepath,
            update_coords=args.update_coords,
            rechunk=args.chunk_strategy,
            attrs=args.attrs,
            dask_config_kwargs=dask_config["config_kwargs"],
            dask_cluster_kwargs=dask_config["cluster_kwargs"],
            zarr_version=zarr_version,
            )

    elif args.action == "send_to_icechunk":

        send_to_icechunk(
            file=filepaths,
            bucket=args.bucket,
            object_prefix=args.object_prefix,
            store_credentials_json=args.store_credentials_json,
            variables=variables,
            send_vars_indep=args.var_stores,
            append_dim=args.append_dim,
            grid_filepath=args.grid_filepath,
            update_coords=args.update_coords,
            rechunk=args.chunk_strategy,
            attrs=args.attrs,
            branch=args.branch,
            commit_message=args.commit_message,
            variable_commits=args.var_commits,
            dask_config_kwargs=dask_config["config_kwargs"],
            dask_cluster_kwargs=dask_config["cluster_kwargs"],
            icechunk_config=icechunk_config,
            )
    
    elif args.action == "update_icechunk":

        update_icechunk(
            file=filepaths,
            bucket=args.bucket,
            object_prefix=args.object_prefix,
            store_credentials_json=args.store_credentials_json,
            variables=variables,
            send_vars_indep=args.var_stores,
            append_dim=args.append_dim,
            grid_filepath=args.grid_filepath,
            update_coords=args.update_coords,
            rechunk=args.chunk_strategy,
            attrs=args.attrs,
            branch=args.branch,
            commit_message=args.commit_message,
            variable_commits=args.var_commits,
            dask_config_kwargs=dask_config["config_kwargs"],
            dask_cluster_kwargs=dask_config["cluster_kwargs"],
            icechunk_config=icechunk_config,
            )

    elif args.action == "list":

        if args.object_prefix is not None:
            dest = f"{args.bucket}/{args.object_prefix}"
        else:
            dest = args.bucket

        list_objects(
            dest=dest,
            store_credentials_json=args.store_credentials_json,
        )

    else:
        raise NotImplementedError(f"Action {args.action} not implemented.")


def ods():
    """Run the OceanDataStore CLI."""
    initialise_logging()
    banner()

    parser = create_parser()
    args = parser.parse_args()

    process_action(args)

    logging.info("✔ OceanDataStore terminated successfully ✔")
    sys.exit(0)
