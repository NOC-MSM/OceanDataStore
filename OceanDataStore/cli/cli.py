# ===================================================================
# Copyright 2026 National Oceanography Centre
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#  http://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.
# ===================================================================
"""
cli.py

Description:
This module defines the command line interface for the OceanDataStore
package.

Authors:
    - Ollie Tooth
    - Joao Morado
    - Tobias Ferreira
"""
import sys
import json
import logging

from OceanDataStore.cli import (
    send_to_zarr,
    send_to_icechunk,
    update_zarr,
    update_icechunk,
    list_objects
)
from OceanDataStore.cli.arg_parser import create_parser
from OceanDataStore.cli.logging import initialise_logging

logger = logging.getLogger(__name__)


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
            grid_filepath=args.grid_filepath,
            update_coords=args.update_coords,
            rechunk=args.chunk_strategy,
            attrs=args.attrs,
            client=None,
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
            append_dim=args.append_dim,
            grid_filepath=args.grid_filepath,
            update_coords=args.update_coords,
            rechunk=args.chunk_strategy,
            attrs=args.attrs,
            client=None,
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

        if args.var_commits:
            logger.warning("The --var-commits flag will be ignored when updating an Icechunk repository.")

        update_icechunk(
            file=filepaths,
            bucket=args.bucket,
            object_prefix=args.object_prefix,
            store_credentials_json=args.store_credentials_json,
            variables=variables,
            append_dim=args.append_dim,
            grid_filepath=args.grid_filepath,
            update_coords=args.update_coords,
            rechunk=args.chunk_strategy,
            attrs=args.attrs,
            branch=args.branch,
            commit_message=args.commit_message,
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
    """
    Run the OceanDataStore CLI.
    """
    initialise_logging()

    parser = create_parser()
    args = parser.parse_args()

    process_action(args)

    logging.info("✔ OceanDataStore terminated successfully ✔")
    sys.exit(0)
