# OceanDataStore CLI

!!! abstract "Summary"

    **This is the user guide for the OceanDataStore Command Line Interface (CLI) to write and update ocean data in cloud object storage.**

---

## Creating a Credentials File

To get started using **OceanDataStore CLI**, users need to create a ``credentials.json`` file containing the following information:

```json
{
    "token": "my_token",
    "secret": "my_secret",
    "endpoint_url": "https://my.object.store"
}
```

where `token` is your access key ID, `secret` is your secret access key and `endpoint_url` is the optional endpoint URL to use for the object store backend.

## Sending Individual Files

### Zarr Stores

To create a new zarr store in an object store from a variable contained in a local netCDF file, we can use the `send_to_zarr` command:

```bash
ods send_to_zarr -f /path/to/file.nc -c credentials.json -b bucket_name -p prefix -v var
```

The arguments used are:

* `-f`: Path to the netCDF file containing the variables.
* `-c`: Path to the JSON file containing the object store credentials.
* `-b`: Bucket name in the object store where the variables will be stored.
* `-v`: Variable within the netCDF file to send to the object store.

In the above example, the variable(s) will be stored in a single zarr store at the `<bucket_name>/<prefix>` path. We can instead create an individual zarr store for each variable at `<bucket_name>/<prefix>/<var>` by using the `-vs` (`--variable-stores`) flag.

### Icechunk Repositories

To create a new icechunk repository in an object store from a local netCDF file, we can use the `send_to_icechunk` command:

```bash
ods send_to_icechunk -f /path/to/file.nc -c credentials.json -b bucket_name -v var
```

The arguments used are:

* `-f`: Path to the netCDF file containing the variables.
* `-c`: Path to the JSON file containing the object store credentials.
* `-b`: Bucket name in the object store where the variables will be stored.
* `-v`: Variable within the netCDF file to send to the object store.

## Sending Lots of Files

### Zarr Stores

To create a new zarr store in an object store using a large number of files, we can use [dask](https://www.dask.org) with the `send_to_zarr` command by passing a dask configuration JSON file:

```bash
ods send_to_zarr -f filepaths -c credentials.json -b bucket_name -p prefix \
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

Users are strongly recommended to implement `send_to_zarr` workflows using a job scheduler, such as SLURM or PBS, to either run the LocalCluster on a single compute node or to use an existing the SLURMCluster or PBSCluster (dask job queue).

**Note:** the netCDF4 library does not support multi-threaded access to datasets, so users should ensure that ``threads_per_worker : 1`` in their dask configuration JSON file to avoid raising CancelledError exceptions when using ``send_to_zarr`` or `update_zarr`.

### Updating Existing Stores

To update an existing zarr store in an object store, we can use the `update_zarr` command:

```bash
ods update_zarr -f /path/to/file.nc -c credentials.json -b bucket_name -p prefix -v var
```

This command will replace and/or append the values of variable `var` stored at the local filepath to the `/bucket_name/prefix/var` store provided it already exists in the object store.

**Note:** compatability checks must be passed before local data will be appended to an existing store, these include chunk size & dimension compatability.

### Updating Existing Stores With Lots of Files

To update an existing zarr store in an object store using a large number of files, we can use [dask](https://www.dask.org) via the `update_zarr` command analogously to `send_to_zarr`:

```bash
ods update_zarr -f filepaths -c credentials.json -b bucket_name -p prefix \
                -gf filepath_domain -uc '{"lat":"lat_new", "lon":"lon_new"}' \
                -cs '{"x":500, "y":500, "depthw":25}' -ad time \
                -dc dask_config.json
```

## Examples

For further examples of how to implement the commands in **OceanDataStore** in your own workflows, see the bash scripts in the `examples` directory.
