# OceanDataStore

A Python library designed to streamline writing, updating & accessing ocean model and observational data stored in cloud object storage.

## Installation

To install the **OceanDataStore** package, first clone the repository from GitHub:

```bash
git clone git@github.com:NOC-MSM/OceanDataStore.git
```

Next, install **OceanDataStore** in editable mode by:

```bash
cd OceanDataStore

pip install -e .
```

**Note:** we strongly recommend installing **OceanDataStore** into a new virtual environment using either ``venv`` or ``conda / mamba``.

## User Guide

### Creating a Credentials File

To get started using **OceanDataStore**, users need to create a ``credentials.json`` file containing the following information:

```json
{
    "secret": "your_secret",
    "token": "your_token",
    "endpoint_url": "https://noc-msm-o.s3-ext.jc.rl.ac.uk"
}
```

### Sending Individual Files

To create a new zarr store in an object store from a local file, use the `send` command:

```bash
ods send -f /path/to/file.nc -c credentials.json -b bucket_name -v var
```

The arguments used are:
- `-f`: Path to the netCDF file containing the variables.
- `-c`: Path to the JSON file containing the object store credentials.
- `-b`: Bucket name in the object store where the variables will be stored.
- `-v`: Variable within the netCDF file to send to the object store.

In the example above, without a `-p` (or `--prefix`), the variables will be stored in `<bucket_name>/<var>`. If a `--prefix` is provided, the variables will be stored in `<bucket_name>/<prefix>/<var>`.

### Sending Lots of Files

To create a new zarr store in an object store from a large number of files, we can use [dask](https://www.dask.org) via the `send_with_dask` command:

```bash
ods send_with_dask -f filepaths -c credentials.json -b bucket_name -p prefix \
                      -gf filepath_domain -uc '{"lat":"lat_new", "lon":"lon_new"}' \
                      -cs '{"x":500, "y":500, "depthw":25}' \
                      -dc dask_config.json
```

The arguments used are:
- `-f`: Paths to the multiple netCDF files containing the variables.
- `-c`: Path to the JSON file containing the object store credentials.
- `-b`: Bucket name in the object store where the variables will be stored.
- `-p`: Prefix used to define path to object (see above).
- `-gf`: Path to model grid file containing domain variables.
- `-uc`: Coordinates dimension variables to update given as a JSON string '{current_coord : new_coord}'.
- `-cs`: Chunk strategy used to rechunk model data.
- `-dc`: Path to JSON file containing Dask configuration.

where the contents of the ``dask_config.json`` are:

```json
{
    "config_kwargs": {
        "temporary_directory":"..../jasmin_os_tmp/",
        "local_directory":"..../jasmin_os_tmp/"
    },
    "cluster_kwargs": {
        "n_workers" : 12,
        "threads_per_worker" : 1,
        "memory_limit":"2GB"
    }
}
```

In the example, a LocalCluster with 12 single threaded workers, each with 2 GB of available memory, is used to transfer a large collection of files to an object store.

Users are recommended to implement send_with_dask workflows using a job scheduler, such as SLURM or PBS, to run the LocalCluster on a single compute node.

**Note:** the netCDF4 library does not support multi-threaded access to datasets, so users should ensure that ``threads_per_worker : 1`` in their dask configuration .json file to avoid raising CancelledError exceptions when using send_with_dask or update_with_dask.

### Updating Existing Stores

To update an existing zarr store in an object store, we can use the `update` command:

```bash
ods update -f /path/to/file.nc -c credentials.json -b bucket_name -p prefix -v var
```

This command will append the values of variable `var` stored at the local filepath to the `/bucket_name/prefix/var` store provided it already exists in the object store.

**Note:** compatability checks must be passed before local data will be appended to an existing store, these include chunk size & dimension compatability.

### Updating Existing Stores With Lots of Files

To update an existing zarr store in an object store using a large number of files, we can use the `update_with_dask` command analogously to `send_with_dask`:

```bash
ods update_with_dask -f filepaths -c credentials.json -b bucket_name -p prefix \
                        -gf filepath_domain -uc '{"lat":"lat_new", "lon":"lon_new"}' \
                        -cs '{"x":500, "y":500, "depthw":25}' -ad time \
                        -dc dask_config.json
```

## Examples

For further examples of how to implement the commands in **OceanDataStore** in your own workflows, see the bash scripts in the `examples` directory.

## OceanDataStore Arguments

### Mandatory Arguments

| Long version | Short Version | Description |
|---|---|---|
| action | | Specify the action: `send` to send a file or `update` to update an existing object. |
| `--filepaths` | `-f` | Paths to the files to send or update. |
| `--credentials` | `-c` | Path to the JSON file containing the credentials for the object store. |
| `--bucket` | `-b` | Bucket name. |

### Optional Arguments

| Flag | Short Version | Description |
|---|---|---|
| `--prefix` | `-p` | Object prefix (default=`None`). |
| `--append-dim` | `-ad` | Append dimension (default=`time_counter`). |
| `--variables` | `-v` | Variables to send (default=`None`). If `None`, all variables will be sent. If `consolidated`, the variables will be sent to a single consolidated zarr store. |
| `--chunk-strategy` | `-cs` | Chunk strategy as a JSON string (default=`None`). E.g., '{\"time_counter\": 1, \"x\": 100, \"y\": 100}' |
| `--dask-configuration` | `-dc` | Path to the JSON file defining the Dask Local Cluster configuration (default=`None`). |
| `--grid-filepath` | `-gf` | File path to model grid file containing domain information (default=`None`). |
| `--update-coords` | `-uc` | Coordinate dimensions to update as a JSON string (default=`None`). E.g., '{\"nav_lon\": \"glamt\", \"nav_lat\": \"gphit\"}' |
| `--attributes` | `-at` | Attributes to add to the dataset as a JSON string. E.g., '{\"title\": \"my_dataset\"}' |
| `--zarr-version` | `-zv` | Zarr version used to create the zarr store (default=`3`). Options are `2` (v2) or `3` (v3). |

---
