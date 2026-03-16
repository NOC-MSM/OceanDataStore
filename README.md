# OceanDataStore

<p align="left">
    <img src="./docs/docs/assets/icons/noc_logo_black.png" alt="Logo" width="210" height="75">
    &nbsp
    &nbsp
    <img src="./docs/docs/assets/icons/OceanDataStore_logo.png" alt="Logo" width="170" height="110">
</p>

*A library designed to streamline writing, updating & accessing ocean model and observational data stored in cloud object storage.*

## Installation

We recommend downloading and installing **OceanDataStore** into a new virtual environment via GitHub.

After activating a new virtual environment, pip install **OceanDataStore** from GitHub:
```{bash}
pip install git+https://github.com/NOC-MSM/OceanDataStore.git
```

**Note:** we strongly recommend installing **OceanDataStore** into a new virtual environment using either ``venv`` or ``conda / mamba``.

## Documentation

To learn more about OceanDataStore, click [**here**](https://noc-msm.github.io/OceanDataStore/) to explore the documentation.

## Examples

For examples of how to implement the commands in **OceanDataStore CLI** in your own workflows, see the bash scripts in the `examples` directory.

## OceanDataStore CLI Arguments

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
| `--variables` | `-v` | Variables to send (default=`None`). If `None`, all variables will be sent. |
| `--variable-stores` | `-vs` | Flag to send variables to independent stores. |
| `--chunk-strategy` | `-cs` | Chunk strategy as a JSON string (default=`None`). E.g., '{\"time_counter\": 1, \"x\": 100, \"y\": 100}' |
| `--dask-configuration` | `-dc` | Path to the JSON file defining the Dask Local Cluster configuration (default=`None`). |
| `--grid-filepath` | `-gf` | File path to model grid file containing domain information (default=`None`). |
| `--update-coords` | `-uc` | Coordinate dimensions to update as a JSON string (default=`None`). E.g., '{\"nav_lon\": \"glamt\", \"nav_lat\": \"gphit\"}' |
| `--attributes` | `-at` | Attributes to add to the dataset as a JSON string. E.g., '{\"title\": \"my_dataset\"}' |
| `--zarr-version` | `-zv` | Zarr version used to create the zarr store (default=`3`). Options are `2` (v2) or `3` (v3). |

---
