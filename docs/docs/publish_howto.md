# How-To Guide — Publish :material-cloud-upload:

Here, we describe some of the most common OceanDataStore publishing operations in a concise how-to guide (inspired by the excellent documentation of [Icechunk](https://icechunk.io/en/latest/howto/)).

For more detailed documentation on the OceanDataStore CLI, users should visit the API [Reference].

[Reference]: cli_reference.md

---

## How do I set up my credentials?

* Create a `credentials.json` file containing your object store access key, secret, and endpoint:

```json
{
    "token": "my_token",
    "secret": "my_secret",
    "endpoint_url": "https://my.object.store"
}
```

* Here `token` is your access key ID, `secret` is your secret access key and `endpoint_url` is the optional endpoint URL of your S3-compatible object store.

* We need to pass this file to every `ods` command using the `-c` flag.

---

## How do I send a single NetCDF file to a Zarr store?

* To send a local netCDF file to a Zarr store in an S3-compatible object store, we can use the `send_to_zarr` command:

```bash
ods send_to_zarr -f /path/to/file.nc -c credentials.json -b bucket_name -p prefix -zv 3
```

| Flag | Description |
|------|-------------|
| `-f` | Path to the local NetCDF file |
| `-c` | Path to the credentials JSON file |
| `-b` | Bucket name in the object store |
| `-p` | Object prefix (path within the bucket) |
| `-zv` | Zarr version — `2` or `3` |

* In the example above, the variable(s) will be stored in a single Zarr v3 store at the <bucket_name>/<prefix> path.

---

## How do I send a single NetCDF file to an Icechunk repository?

* To create a new Icechunk repository in an S3-compatible object store from a variable var contained in a local netCDF file, we can use the `send_to_icechunk` command:

```bash
ods send_to_icechunk -f /path/to/file.nc -c credentials.json -b bucket_name -p prefix \
                     -v var -br "main" -cm "Initial commit"
```

| Flag | Description |
|------|-------------|
| `-f` | Path to the local NetCDF file |
| `-c` | Path to the credentials JSON file |
| `-b` | Bucket name in the object store |
| `-p` | Object prefix (path within the bucket) |
| `-v` | Name of the variable(s) to write/update to the Icechunk repository |
| `-br` | Icechunk branch to commit to |
| `-cm` | Commit message recorded with this transaction |

* Note, `send_to_icechunk` requires two additional keyword arguments, `-br` and `-cm`, which define the branch on which to perform the transaction and the commit message to record.

---

## How do I send multiple NetCDF files to a Zarr store in parallel?

* To create a new Zarr store using a large number of NetCDF files, we can use [dask](https://www.dask.org) with the `send_to_zarr` command by passing a dask configuration JSON file:

```bash
ods send_to_zarr -f /path/to/files*.nc -c credentials.json -b bucket_name -p prefix \
                 -cs '{"x":2160, "y":1803}' -dc dask_config.json -zv 3
```

| Flag | Description |
|------|-------------|
| `-f` | Path to the local NetCDF file |
| `-c` | Path to the credentials JSON file |
| `-b` | Bucket name in the object store |
| `-p` | Object prefix (path within the bucket) |
| `-cs` | Chunk strategy used to rechunk model data |
| `-dc` | Path to JSON file containing Dask configuration |
| `-zv` | Zarr version — `2` or `3` |

The `dask_config.json` configures a dask LocalCluster:

```json
{
    "config_kwargs": {
        "temporary_directory": "/path/to/tmp/",
        "local_directory": "/path/to/tmp/"
    },
    "cluster_kwargs": {
        "n_workers": 12,
        "threads_per_worker": 1,
        "memory_limit": "2GB"
    }
}
```

* In the example above, a dask LocalCluster with 12 single threaded workers, each with 2 GB of available memory, is used to transform a large collection of NetCDF files into a single Zarr store.

* We also rechunk the original NetCDF data prior in the process of writing to Zarr, such that the new chunks are comprised of 2160 values along the `x`-dimension and 1803 values along the `y`-dimension. 

* Users are strongly recommended to implement `send_to_zarr` workflows using a job scheduler, such as SLURM or PBS, to either run the LocalCluster on a single compute node or to use an existing the SLURMCluster or PBSCluster (dask job queue).

!!! warning
    Users should set `threads_per_worker: 1` in their Dask configuration when reading NetCDF4 datasets with `send_to_zarr` or `update_zarr` because HDF5 serializes threaded access within a process, meaning it does not scale well with multiple threads per worker.

---

## How do I send multiple NetCDF files to an Icechunk repository in parallel?

* To create a new Icechunk repository using a large number of NetCDF files, we can use [dask](https://www.dask.org) with the `send_to_icechunk` command by passing a dask configuration JSON file:

```bash
ods send_to_icechunk -f /path/to/files*.nc -c credentials.json -b bucket_name -p prefix \
                     -gf /path/to/domain_cfg.nc -uc '{"lon":"lon_new", "lat":"lat_new"}' \
                     -cs '{"x":2160, "y":1803}' -dc dask_config.json -br "main" -cm "New big commit message..."
```

| Flag | Description |
|------|-------------|
| `-f` | Path to the local NetCDF file |
| `-c` | Path to the credentials JSON file |
| `-b` | Bucket name in the object store |
| `-p` | Object prefix (path within the bucket) |
| `-gf` | Path to model grid file containing domain variables |
| `-uc` | Coordinates dimension variables to update given as a JSON string '{current_coord : new_coord}' |
| `-cs` | Chunk strategy used to rechunk model data |
| `-dc` | Path to JSON file containing Dask configuration |
| `-zv` | Zarr version — `2` or `3` |

The `dask_config.json` configures a dask LocalCluster:

```json
{
    "config_kwargs": {
        "temporary_directory": "/path/to/tmp/",
        "local_directory": "/path/to/tmp/"
    },
    "cluster_kwargs": {
        "n_workers": 12,
        "threads_per_worker": 1,
        "memory_limit": "2GB"
    }
}
```

* In the example above, a dask LocalCluster with 12 single threaded workers, each with 2 GB of available memory, is used to transform a large collection of NetCDF files into a single Zarr store.

* We also rechunk the original NetCDF data prior in the process of writing to Zarr, such that the new chunks are comprised of 2160 values along the `x`-dimension and 1803 values along the `y`-dimension. 

* Finally, the `-uc` flag is used to update the coordinates of the Dataset using a single model domain NetCDF file whose path is given by the `-gf` flag. The JSON string maps coordinates in the original Dataset to those coordinate in the model domain reference Dataset it will be replaced by.

---

## How do I append new data to an existing Zarr store?

* To update an existing Zarr store in an S3-compatible object store, we can use the `update_zarr` command:

```bash
ods update_zarr -f /path/to/file.nc -c credentials.json -b bucket_name -p prefix \
                -v "thetao-con" -ad time_counter -zv 3
```

| Flag | Description |
|------|-------------|
| `-f` | Path to the local NetCDF file |
| `-c` | Path to the credentials JSON file |
| `-b` | Bucket name in the object store |
| `-p` | Object prefix (path within the bucket) |
| `-v` | Name of the variable(s) to write/update to the Zarr store |
| `-ad` | Name of the dimension along which to appennd data |
| `-zv` | Zarr version — `2` or `3` |

* In the example above, we will replace and/or append new values of variable `thetao_con` stored at the local filepath to the `/bucket_name/prefix/var` Zarr v3 store provided it already exists in the object store.

**Note:** compatability checks must be passed before local data will be appended to an existing store, these include chunk size & dimension compatability.

---

## How do I append new data to an existing Icechunk repository?

* To update an existing Icechunk repository in an S3-compatible object store, we can use the `update_icechunk` command:

```bash
ods update_icechunk -f /path/to/file.nc -c credentials.json -b bucket_name -p prefix \
                    -v "thetao_con" -ad "time_counter" -br "main" -cm "Update commmit message..." \
```

| Flag | Description |
|------|-------------|
| `-f` | Path to the local NetCDF file |
| `-c` | Path to the credentials JSON file |
| `-b` | Bucket name in the object store |
| `-p` | Object prefix (path within the bucket) |
| `-v` | Name of the variable(s) to write/update to the Icechunk repository |
| `-ad` | Name of the dimension along which to appennd data |
| `-br` | Icechunk branch to commit to |
| `-cm` | Commit message recorded with this transaction |

* In the example above, we will replace and/or append new values of variable `thetao_con` stored at the local filepath to the `/bucket_name/prefix/var` Icechunk repository provided it already exists in the object store.

**Note:** compatability checks must be passed before local data will be appended to an existing store, these include chunk size & dimension compatability.

---

## How do I update an existing Zarr store with multiple files in parallel?

* To update an existing Zarr store in an object store using a large number of files, we can use [dask](https://www.dask.org) via the `update_zarr` command as we showed above with `send_to_zarr`:

```bash
ods update_zarr -f filepaths -c credentials.json -b bucket_name -p prefix \
                -gf filepath_domain -uc '{"lat":"lat_new", "lon":"lon_new"}' \
                -cs '{"x":500, "y":500, "depthw":25}' -ad time \
                -dc dask_config.json -zv 3
```

| Flag | Description |
|------|-------------|
| `-f` | Path to the local NetCDF file |
| `-c` | Path to the credentials JSON file |
| `-b` | Bucket name in the object store |
| `-p` | Object prefix (path within the bucket) |
| `-cs` | Chunk strategy used to rechunk model data |
| `-ad` | Name of the dimension along which to appennd data |
| `-dc` | Path to JSON file containing Dask configuration |
| `-zv` | Zarr version — `2` or `3` |

* In the example above, we rechunk the original NetCDF data prior in the process of writing to Zarr, such that the new chunks are comprised of 500 values along the `x`-dimension, 500 values along the `y`-dimension, and 25 values along the `depthw` dimension. 

---

## How do I update an existing Icechunk repository with multiple files in parallel?

* To update an existing Icechunk repository with a large collection of files, we can use the `update_icechunk` command:

```bash
ods update_icechunk -f filepaths -c credentials.json -b bucket_name -p prefix \
                    -cs '{"x":500, "y":500, "depthw":25}' -ad time \
                    -dc dask_config.json -br "main" -cm "Update commit message..."
```

| Flag | Description |
|------|-------------|
| `-f` | Path to the local NetCDF file |
| `-c` | Path to the credentials JSON file |
| `-b` | Bucket name in the object store |
| `-p` | Object prefix (path within the bucket) |
| `-cs` | Chunk strategy used to rechunk model data |
| `-ad` | Name of the dimension along which to appennd data |
| `-dc` | Path to JSON file containing Dask configuration |
| `-br` | Icechunk branch to commit to |
| `-cm` | Commit message recorded with this transaction |

* In the example above, we rechunk the original NetCDF data prior in the process of writing to Icechunk, such that the new chunks are comprised of 500 values along the `x`-dimension, 500 values along the `y`-dimension, and 25 values along the `depthw` dimension. 

---

## How do I list objects in my bucket?

* To list all objects contained within a bucket, we can use the `list` command:

```bash
ods list -c credentials.json -b bucket_name
```

| Flag | Description |
|------|-------------|
| `-c` | Path to the credentials JSON file |
| `-b` | Bucket name in the object store |

---

## Next Steps

* [Examples](publish_examples.md) — End-to-end examples of publishing datasets with OceanDataStore
* [CLI Reference](cli_reference.md) — complete reference to the available flags when using the OceanDataStore CLI