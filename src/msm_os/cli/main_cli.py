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

import logging
import sys

from ..object_store_handler import get_files, send, send_with_dask, update
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

    variables = list(args.variables) if args.variables is not None else None

    if args.action == "send":
        if args.variables is not None and "compact" in args.variables:
            send_vars_indep = True
        else:
            send_vars_indep = False

        send(
            filepaths=list(args.filepaths),
            bucket=args.bucket,
            store_credentials_json=args.store_credentials_json,
            variables=variables,
            append_dim=args.append_dim,
            send_vars_indep=not send_vars_indep,
            object_prefix=args.object_prefix,
            rechunk=args.chunk_strategy,
            reproject=args.reproject,
            skip_integrity_check=args.skip_integrity_check,
            to_zarr_kwargs=None,
        )

    elif args.action == "send_with_dask":
        if args.variables is not None and "compact" in args.variables:
            send_vars_indep = True
        else:
            send_vars_indep = False

        if len(args.filepaths) > 1:
            filepaths = list(args.filepaths)
        else:
            filepaths = args.filepaths

        send_with_dask(
            filepaths=filepaths,
            bucket=args.bucket,
            store_credentials_json=args.store_credentials_json,
            variables=variables,
            append_dim=args.append_dim,
            send_vars_indep=not send_vars_indep,
            grid_filepath=args.grid_filepath,
            update_coords=args.update_coords,
            object_prefix=args.object_prefix,
            rechunk=args.chunk_strategy,
            dask_config_kwargs=args.dask_config_kwargs,
            dask_cluster_kwargs=args.dask_cluster_kwargs,
            to_zarr_kwargs=None,
        )

    elif args.action == "update":
        update(
            filepaths=list(args.filepaths),
            bucket=args.bucket,
            store_credentials_json=args.store_credentials_json,
            variables=variables,
            object_prefix=args.object_prefix,
            to_zarr_kwargs=None,
        )

    elif args.action == "list":
        get_files(
            bucket=args.bucket,
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
