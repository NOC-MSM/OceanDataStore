"""
argument_parser.py

Description:
This module defines the argument parser for the
OceanDataStore command line interface.

Authors:
    - Joao Morado
    - Tobias Ferreira
    - Ollie Tooth
"""
import json
import argparse

from ..__init__ import __version__


def create_parser():
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description=f"OceanDataStore {__version__} command line interface",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Send and Update are mutually exclusive operations
    parser.add_argument(
        "action",
        choices=["send_to_zarr", "update_zarr", "send_to_icechunk", "update_icechunk", "list"],
        help="Specify the action: 'send_to_zarr' or 'send_to_icechunk' to send a file(s) to an object store, "
        "'update_zarr' or 'update_icechunk' to update an existing object, or 'list' to list the files in a bucket.",
    )

    # Always required
    parser.add_argument(
        "-f",
        "--filepaths",
        dest="filepaths",
        help="Paths to the files to send.",
        nargs="+",
        required=True,
    )

    parser.add_argument(
        "-c",
        "--credentials",
        dest="store_credentials_json",
        help="Path to the JSON file containing the credentials for the object store.",
        required=True,
    )

    parser.add_argument(
        "-b",
        "--bucket",
        dest="bucket",
        help="Bucket name.",
        required=True,
    )

    # Optional arguments
    parser.add_argument(
        "-p",
        "--prefix",
        dest="object_prefix",
        help="Object prefix.",
        default=None,
    )

    parser.add_argument(
        "-ad",
        "--append-dim",
        dest="append_dim",
        help="Append dimension.",
        default="time_counter",
    )

    parser.add_argument(
        "-v",
        "--variables",
        dest="variables",
        help="Variables to send to store. Default None will send all variables.",
        nargs="+",
        default=None,
    )

    parser.add_argument(
        "-vs",
        "--variable-stores",
        dest="var_stores",
        action="store_true",
        help="Send variables to independent stores.",
    )

    parser.add_argument(
        "-cs",
        "--chunk-strategy",
        dest="chunk_strategy",
        help="Chunk strategy as a JSON string. E.g., '{\"time_counter\": 1, \"x\": 100, \"y\": 100}'",
        type=json.loads,
        default=None,
    )

    parser.add_argument(
        "-dc",
        "--dask-configuration",
        dest="dask_config_json",
        help="Path to the JSON file defining the Dask Local Cluster configuration.",
        default=None,
    )

    parser.add_argument(
        "-gf",
        "--grid-filepath",
        dest="grid_filepath",
        help="File path to model grid file containing domain information.",
        default=None,
    )

    parser.add_argument(
        "-uc",
        "--update-coords",
        dest="update_coords",
        help="Coordinate dimensions to update as a JSON string. E.g., '{\"nav_lon\": \"glamt\", \"nav_lat\": \"gphit\"}'",
        type=json.loads,
        default=None,
    )

    parser.add_argument(
        "-at",
        "--attributes",
        dest="attrs",
        help="Attributes to add to the dataset as a JSON string. E.g., '{\"title\": \"my_dataset\"}'",
        type=json.loads,
        default=None,
    )

    parser.add_argument(
        "-zv",
        "--zarr-version",
        dest="zarr_version",
        help="Zarr version used to create the zarr store. Options are 2 (v2) or 3 (v3).",
        default=3,
    )

    parser.add_argument(
        "-br",
        "--branch",
        dest="branch",
        help="Branch of Icechunk repository to commit changes to.",
        default="main",
    )

    parser.add_argument(
        "-cm",
        "--commit_message",
        dest="commit_message",
        help="Commit message to be recorded when committing changes to Icechunk repository.",
        default="Add new data to my Icechunk repository",
    )

    parser.add_argument(
        "-vc",
        "--variable-commits",
        dest="var_commits",
        action="store_true",
        help="Send variables to Icechunk repository using independent commits.",
    )

    parser.add_argument(
        "-ic",
        "--icechunk-configuration",
        dest="icechunk_config_json",
        help="Path to the JSON file defining the Icechunk storage and repository configurations.",
        default=None,
    )

    return parser
