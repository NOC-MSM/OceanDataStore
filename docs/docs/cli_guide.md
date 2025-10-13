# OceanDataStore CLI :material-cloud-upload:

!!! abstract "Summary"

    **This is the User Guide for the OceanDataStore Command Line Interface (CLI) to write and update ocean data in cloud object storage.**

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

!!! info "A Brief Introduction to Zarr"
    Zarr is an open source, flexible and efficient storage format designed for chunked, compressed, N-dimensional arrays. At its simplest, Zarr can be considered a cloud-native alternative to netCDF files since it consists of binary data files (chunks) accompanied by external metadata files.

    One important difference between archival file formats (e.g., netCDF) and Zarr is that there is no single Zarr file. Instead, a Zarr store (typically given the suffix .zarr - although this is not a requirement) is a directory containing chunks of data stored in compressed binary files and JSON metadata files containing the array configuration and compression used.

    Zarr works especially well in combination with cloud storage, such as the JASMIN object store, given that users can access data concurrently from multiple threads or processes using Python or a number of other programming languages.

    [Click here](https://zarr-specs.readthedocs.io/en/latest/specs.html) for more information on the Zarr specification.

To create a new Zarr store in an object store from the contents of a local netCDF file, we can use the `send_to_zarr` command:

```bash
ods send_to_zarr -f /path/to/file.nc -c credentials.json -b bucket_name -p prefix -zv 3
```

The arguments used are:

* `-f`: Path to the netCDF file containing the variables.
* `-c`: Path to the JSON file containing the object store credentials.
* `-b`: Bucket name in the object store where the variables will be stored.
* `-zv`: Zarr version used to create the zarr store. Options are 2 (v2) or 3 (v3).

In the above example, the variable(s) will be stored in a single Zarr v3 store at the `<bucket_name>/<prefix>` path.

### Icechunk Repositories

!!! info "A Brief Introduction to Icechunk"
    Icechunk is an open-source, cloud-native transactional tensor storage engine designed for N-dimensional data in cloud object storage. At its simplest, Icechunk can be considered a "transactional storage engine for Zarr", meaning that Icechunk manages all of the I/O for reading, writing and updating metadata and chunk data & keeps track of changes (referred to as transactions) to the store in the form of snapshots. 

    In place of Zarr store, users create an Icechunk repository, which functions as both a self-contained Zarr store and a database of the snapshots resulting from transactions (e.g., updating values or writing new values in the store). 

    This allows Icechunk repositories to support data version control, since users can time-travel to previous snapshots of a repository.

    [Click here](https://icechunk.io/en/latest/overview/) for an overview of Icechunk.

To create a new icechunk repository in an object store from a variable `var` contained in a local netCDF file, we can use the `send_to_icechunk` command:

```bash
ods send_to_icechunk -f /path/to/file.nc -c credentials.json -b bucket_name -p prefix -v var -br "main" -cm "New commit message..."
```

The arguments used are:

* `-f`: Path to the netCDF file containing the variables.
* `-c`: Path to the JSON file containing the object store credentials.
* `-b`: Bucket name in the object store where the variables will be stored.
* `-v`: Variable within the netCDF file to send to the object store.
* `-br`: Branch of Icechunk repository to commit changes to.
* `-cm`: Commit message to be recorded when committing changes to Icechunk repository.

Note, that the `send_to_icechunk` command requires two additional arguments, `-br` and `-cm`, which define the branch on which to perform the transaction and the commit message to record.

## Sending Lots of Files to Stores

To create a new Zarr store in an object store using a large number of files, we can use [dask](https://www.dask.org) with the `send_to_zarr` command by passing a dask configuration JSON file:

```bash
ods send_to_zarr -f /path/to/files*.nc -c credentials.json -b bucket_name -p prefix \
                 -gf /path/to/domain_cfg.nc -uc '{"lon":"lon_new", "lat":"lat_new"}' \
                 -cs '{"x":2160, "y":1803}' -dc dask_config.json -zv 3
```

Similarly, we can create a new Icechunk repository in an object store using a large number of files:

```bash
ods send_to_icechunk -f /path/to/files*.nc -c credentials.json -b bucket_name -p prefix \
                     -gf /path/to/domain_cfg.nc -uc '{"lon":"lon_new", "lat":"lat_new"}' \
                     -cs '{"x":2160, "y":1803}' -dc dask_config.json -br "main" -cm "New big commit message..."
```

The arguments used are:
* `-f`: Paths to the multiple netCDF files containing the variables.
* `-c`: Path to the JSON file containing the object store credentials.
* `-b`: Bucket name in the object store where the variables will be stored.
* `-p`: Prefix used to define path to object (see above).
* `-gf`: Path to model grid file containing domain variables.
* `-uc`: Coordinates dimension variables to update given as a JSON string '{current_coord : new_coord}'.
* `-cs`: Chunk strategy used to rechunk model data.
* `-dc`: Path to JSON file containing Dask configuration.
* `-zv`: Zarr version used to create the zarr store. Options are 2 (v2) or 3 (v3).
* `-br`: Branch of Icechunk repository to commit changes to.
* `-cm`: Commit message to be recorded when committing changes to Icechunk repository.

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

To update an existing Zarr store in an object store, we can use the `update_zarr` command:

```bash
ods update_zarr -f /path/to/file.nc -c credentials.json -b bucket_name -p prefix -v var -zv 3
```

This command will replace and/or append the values of variable `var` stored at the local filepath to the `/bucket_name/prefix/var` store provided it already exists in the object store.

Similarly, to update an existing Icechunk repository, we can use the `update_icechunk` command:

```bash
ods update_icechunk -f /path/to/file.nc -c credentials.json -b bucket_name -p prefix -v var -br "main" -cm "Update commmit message..."
```

**Note:** compatability checks must be passed before local data will be appended to an existing store, these include chunk size & dimension compatability.

### Updating Existing Stores With Lots of Files

To update an existing Zarr store in an object store using a large number of files, we can use [dask](https://www.dask.org) via the `update_zarr` command as we showed above with `send_to_zarr`:

```bash
ods update_zarr -f filepaths -c credentials.json -b bucket_name -p prefix \
                -gf filepath_domain -uc '{"lat":"lat_new", "lon":"lon_new"}' \
                -cs '{"x":500, "y":500, "depthw":25}' -ad time \
                -dc dask_config.json -zv 3
```

Similarly, to update an existing Icechunk repository with a large collection of files, we can use the `update_icechunk` command:

```bash
ods update_icechunk -f filepaths -c credentials.json -b bucket_name -p prefix \
                    -gf filepath_domain -uc '{"lat":"lat_new", "lon":"lon_new"}' \
                    -cs '{"x":500, "y":500, "depthw":25}' -ad time \
                    -dc dask_config.json -br "main" -cm "Update commit message..."
```

where `-ad` is the dimension along which to append chunk data.

## Reference

For a complete reference to the available flags when using the **OceanDataStore CLI**, see the [Reference] page.

## Examples

For further examples of how to implement the commands in **OceanDataStore** in your own workflows, see the bash scripts in the `examples` directory.

[Reference]: cli_reference.md
