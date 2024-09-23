# msm-os Package

A library designed to streamline the transfer, update, and deletion of Zarr files within object store environments.

## Installation

To install this package, clone the repository first:

```bash
git clone git@github.com:NOC-OI/msm-os.git
cd msm-os
```

Then, install it with:

```bash
pip install -e .
```

## Usage

### Sending Files

To send a file to an object store, use the following command:

```bash
msm_os send -f eORCA025_1y_grid_T_1976-1976.nc -c credentials.json -b eorca025
```

The flags used are:
- `-f`: Path to the NetCDF file containing the variables.
- `-c`: Path to the JSON file containing the object store credentials.
- `-b`: Bucket name in the object store where the variables will be stored.

In the example, without a `-p` (or `--prefix`), the variables will be stored in `eorca025/T1y/<var>.zarr`. If a `--prefix` is provided, the variables will be stored in `eorca025/<prefix>/<var>.zarr`.

### Updating or Replacing Files

To update the values of an existing variable in an object store, use:

```bash
msm_os update -f eORCA025_1y_grid_T_1976-1976.nc -c credentials.json -b eorca025 -v e3t
```

This command will locate the region with the same timestamp as `eORCA025_1y_grid_T_1976-1976.nc` and overwrite the values of `e3t` in the object store.

An additional flag is used:
- `-v`: The name of the variable to update.

## Flags

### Mandatory Flags

| Long version | Short Version | Description |
|---|---|---|
| action | | Specify the action: `send` to send a file or `update` to update an existing object. |
| `--filepaths` | `-f` | Paths to the files to send or update. |
| `--credentials` | `-c` | Path to the JSON file containing the credentials for the object store. |
| `--bucket` | `-b` | Bucket name. |

### Optional Flags

| Flag | Short Version | Description |
|---|---|---|
| `--prefix` | `-p` | Object prefix. |
| `--append_dim` | `-a` | Append dimension (default=`time_counter`). |
| `--variables` | `-v` | Variables to send. If not provided, all variables will be sent. If set to `compact`, the variables will not be sent to separate Zarr files. |
| `--reproject` | `-r` | Whether to reproject data. If not provided, the data is not reprojected. If present, reproject the data from tri-polar grid to PlateCarree.
| `--chunk-strategy` | `-cs` | Chunk strategy in the output data. If provided, the output data will be chunked according to the specified strategy. If not provided, it will use the `auto` mode. The format is a JSON string, e.g., '{"time_counter": 1, "x": 100, "y": 100}'.
| `--skip-integrity-check` | `-si` | Whether to skip data integrity check. If not provided, the integrity checks will be applied to the data in order to check if the uploaded data is OK.

## Credentials File

The credentials file should contain the following information:

```json
{
    "secret": "your_secret",
    "token": "your_token",
    "endpoint_url": "https://noc-msm-o.s3-ext.jc.rl.ac.uk"
}
```

## Steps During Data Send/Update

Whenever new data is sent or updated in the object store, the code goes through several steps:


### Reproject Data

Some oceanographic models, such as NEMO, output data in different projections (e.g., tripolar grid). For certain uses, it may be beneficial to reproject the data to a regular grid like PlateCarree. If you choose to reproject your data, both the original and reprojected data will be retained in the output file.

### Chunk Strategy

If a chunk strategy is specified, the output data will be chunked accordingly. If no strategy is specified, the data will be chunked using the `auto` option from the `xarray.to_zarr` function.

### Check Data Integrity

Every time new data is appended to an existing Zarr file, it is possible to perform some integrity checks to verify if the metadata and data match the expected format.

1. Metadata check: Each new NetCDF file sent to the object store will have its metadata checked, including the number and names of variables and coordinates. If there are discrepancies, a specific error is raised.

2. Data check: The checksum of the data in the NetCDF file is compared with the data in the Zarr file after upload. If they differ, an error is raised.

If any errors are detected during these checks, the data is rolled back to the previous version. This rollback is performed directly in the Zarr file by updating the metadata to exclude the new data. The system will retry the upload twice more; if it fails again, a message is logged.

The integrity check may take a while and slow down to upload process. Because of that, if you want to skip this check, you can add set the `skip_integrity_check` to false when you are sending a file to the object store.