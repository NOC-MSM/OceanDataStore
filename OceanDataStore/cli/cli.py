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

import argparse
import copy
import json
import logging
from typing import Any

from OceanDataStore.cli.arg_parser import create_parser
from OceanDataStore.cli.icechunk import send_to_icechunk, update_icechunk
from OceanDataStore.cli.logging import initialise_logging
from OceanDataStore.cli.object_store import DEFAULT_ICECHUNK_CONFIG
from OceanDataStore.cli.utils import list_objects
from OceanDataStore.cli.zarr import send_to_zarr, update_zarr

logger = logging.getLogger(__name__)


def _load_json_config(path: str, required_keys: list[str], name: str) -> dict[str, Any]:
    """
    Load a JSON configuration file and check that the required keys exist.

    Parameters
    ----------
    path : str
        Filepath to the JSON configuration file.
    required_keys : list[str]
        Keys which must be present in the configuration.
    name : str
        Name of the configuration used in error messages (e.g., 'Dask').

    Returns
    -------
    dict[str, Any]
        Configuration loaded from the JSON file.

    Raises
    ------
    ValueError
        If a required key is missing from the configuration.
    """
    with open(path) as f:
        config = json.load(f)
    for key in required_keys:
        if key not in config:
            raise ValueError(f"{key} not found in {name} configuration.")
    return config


def process_action(args: argparse.Namespace) -> None:
    """
    Process the action selected using the command line interface.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command line arguments (see ``create_parser``).

    Raises
    ------
    ValueError
        If a Dask or Icechunk JSON configuration is missing required keys.
    NotImplementedError
        If the selected action is not implemented.
    """
    # === Process Arguments === #
    if args.dask_config_json is None:
        dask_config = {"config_kwargs": None, "cluster_kwargs": None}
    else:
        dask_config = _load_json_config(
            args.dask_config_json, required_keys=["config_kwargs", "cluster_kwargs"], name="Dask"
        )

    if args.icechunk_config_json is None:
        icechunk_config = copy.deepcopy(DEFAULT_ICECHUNK_CONFIG)
    else:
        icechunk_config = _load_json_config(
            args.icechunk_config_json,
            required_keys=["storage_config_kwargs", "repository_config_kwargs", "storage_settings_kwargs"],
            name="Icechunk",
        )

    # Keyword arguments common to all send / update actions:
    common_kwargs = {
        "file": args.filepaths,
        "bucket": args.bucket,
        "object_prefix": args.object_prefix,
        "store_credentials_json": args.store_credentials_json,
        "variables": args.variables,
        "append_dim": args.append_dim,
        "grid_filepath": args.grid_filepath,
        "update_coords": args.update_coords,
        "rechunk": args.chunk_strategy,
        "attrs": args.attrs,
        "dask_config_kwargs": dask_config["config_kwargs"],
        "dask_cluster_kwargs": dask_config["cluster_kwargs"],
    }
    zarr_kwargs = {"client": None, "zarr_version": int(args.zarr_version)}
    icechunk_kwargs = {
        "branch": args.branch,
        "commit_message": args.commit_message,
        "icechunk_config": icechunk_config,
    }

    # === Process Actions === #
    if args.action == "send_to_zarr":
        send_to_zarr(**common_kwargs, **zarr_kwargs)

    elif args.action == "update_zarr":
        update_zarr(**common_kwargs, **zarr_kwargs)

    elif args.action == "send_to_icechunk":
        send_to_icechunk(**common_kwargs, **icechunk_kwargs, variable_commits=args.var_commits)

    elif args.action == "update_icechunk":
        if args.var_commits:
            logger.warning("--var-commits flag will be ignored when updating an Icechunk repository.")
        update_icechunk(**common_kwargs, **icechunk_kwargs)

    elif args.action == "list":
        dest = f"{args.bucket}/{args.object_prefix}" if args.object_prefix is not None else args.bucket
        list_objects(dest=dest, store_credentials_json=args.store_credentials_json)

    else:
        raise NotImplementedError(f"Action {args.action} not implemented.")


def ods() -> None:
    """Run the OceanDataStore command line interface."""
    initialise_logging()

    parser = create_parser()
    args = parser.parse_args()

    process_action(args)

    logger.info("✔ OceanDataStore terminated successfully ✔")
