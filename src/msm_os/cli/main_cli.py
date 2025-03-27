"""
main_cli.py

Description:
This module defines the command line interface
for the msm-os package.

Authors:
    - Joao Morado
    - Tobias Ferreira
    - Ollie Tooth
"""
import sys
import json
import logging

from ..object_store_handler import send, send_with_dask, update, update_with_dask, list_objects
from .argument_parser import __version__, create_parser

logger = logging.getLogger(__name__)


def banner():
    """Log the msm_os banner."""
    logger.info(
        f"""
        .-~~~-.
.- ~ ~-(       )_ _
/                    ~ -.
|          msm-os         ',
¬                         .'
~- ._ ,. ,.,.,., ,.. -~
        '       '
    version: {__version__}

""",
        extra={"simple": True},
    )


def initialise_logging():
    """Initialise logging configuration."""
    logging.basicConfig(
        stream=sys.stdout,
        format="☁  msm_os ☁  | %(levelname)10s | %(asctime)s | %(message)s",
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

    if (args.variables is not None) and ("consolidated" in args.variables):
        send_vars_indep = False
    else:
        send_vars_indep = True
    
    if args.filepaths is not None:
        if len(args.filepaths) > 1:
            filepaths = list(args.filepaths)
        else:
            filepaths = args.filepaths

    if args.zarr_version is not None:
        zarr_version = int(args.zarr_version)

    if args.dask_config_json is not None:
        dask_config = json.load(open(args.dask_config_json))
        if "config_kwargs" not in dask_config:
            raise ValueError("config_kwargs not found in Dask configuration.")
        if "cluster_kwargs" not in dask_config:
            raise ValueError("cluster_kwargs not found in Dask configuration.")

    # === Process Actions === #
    if args.action == "send":

        send(
            filepaths=filepaths,
            bucket=args.bucket,
            object_prefix=args.object_prefix,
            store_credentials_json=args.store_credentials_json,
            variables=variables,
            append_dim=args.append_dim,
            send_vars_indep=send_vars_indep,
            grid_filepath=args.grid_filepath,
            update_coords=args.update_coords,
            rechunk=args.chunk_strategy,
            zarr_version=zarr_version,
        )

    elif args.action == "send_with_dask":

        send_with_dask(
            filepaths=filepaths,
            bucket=args.bucket,
            object_prefix=args.object_prefix,
            store_credentials_json=args.store_credentials_json,
            variables=variables,
            append_dim=args.append_dim,
            send_vars_indep=send_vars_indep,
            grid_filepath=args.grid_filepath,
            update_coords=args.update_coords,
            rechunk=args.chunk_strategy,
            dask_config_kwargs=dask_config["config_kwargs"],
            dask_cluster_kwargs=dask_config["cluster_kwargs"],
            zarr_version=zarr_version,
        )

    elif args.action == "update":

        update(
            filepaths=filepaths,
            bucket=args.bucket,
            object_prefix=args.object_prefix,
            store_credentials_json=args.store_credentials_json,
            variables=variables,
            send_vars_indep=send_vars_indep,
            append_dim=args.append_dim,
            grid_filepath=args.grid_filepath,
            update_coords=args.update_coords,
            rechunk=args.chunk_strategy,
            zarr_version=zarr_version,
                )
        
    elif args.action == "update_with_dask":

        update_with_dask(
            filepaths=filepaths,
            bucket=args.bucket,
            object_prefix=args.object_prefix,
            store_credentials_json=args.store_credentials_json,
            variables=variables,
            send_vars_indep=send_vars_indep,
            append_dim=args.append_dim,
            grid_filepath=args.grid_filepath,
            update_coords=args.update_coords,
            rechunk=args.chunk_strategy,
            dask_config_kwargs=dask_config["config_kwargs"],
            dask_cluster_kwargs=dask_config["cluster_kwargs"],
            zarr_version=zarr_version,
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


def msm_os():
    """Run the msm_os cli."""
    initialise_logging()
    banner()

    parser = create_parser()
    args = parser.parse_args()

    process_action(args)

    logging.info("✔ msm_os terminated successfully ✔")
    sys.exit(0)
