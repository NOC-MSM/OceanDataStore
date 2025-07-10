# OceanDataStore CLI

### Mandatory Arguments

| Long version | Short Version | Description |
|---|---|---|
| action | | Specify the action: `send_to_zarr`, `send_to_icechunk`, `update_zarr`, `update_icechunk` or `list`. |
| `--filepaths` | `-f` | Paths to the files to send or update. |
| `--credentials` | `-c` | Path to the JSON file containing the credentials for the object store. |
| `--bucket` | `-b` | Bucket name. |

### Optional Arguments

| Flag | Short Version | Description |
|---|---|---|
| `--prefix` | `-p` | Object prefix (default=`None`). |
| `--append-dim` | `-ad` | Append dimension (default=`time_counter`). |
| `--variables` | `-v` | Variables to send (default=`None`). Default `None` will send all variables. |
| `--variable-stores` | `-vs` | Flag to send variables to independent stores. |
| `--chunk-strategy` | `-cs` | Chunk strategy as a JSON string (default=`None`). E.g., '{\"time_counter\": 1, \"x\": 100, \"y\": 100}' |
| `--dask-configuration` | `-dc` | Path to the JSON file defining the Dask Local Cluster configuration (default=`None`). |
| `--grid-filepath` | `-gf` | File path to model grid file containing domain information (default=`None`). |
| `--update-coords` | `-uc` | Coordinate dimensions to update as a JSON string (default=`None`). E.g., '{\"nav_lon\": \"glamt\", \"nav_lat\": \"gphit\"}' |
| `--attributes` | `-at` | Attributes to add to the dataset as a JSON string. E.g., '{\"title\": \"my_dataset\"}' |
| `--zarr-version` | `-zv` | Zarr version used to create the zarr store (default=`3`). Options are `2` (v2) or `3` (v3). |
| `--branch` | `-br` | Branch of Icechunk repository to commit changes to (default=`main`). |
| `--commit_message` | `-cm` | Commit message to be recorded when committing changes to Icechunk repository. (default=`"Add new data to my Icechunk repository"`). |
| `--variable-commits` | `-vc` | Flag to send variables to Icechunk repository using independent commits. |
| `--icechunk-configuration` | `-ic` | Path to the JSON file defining the Icechunk storage and repository configurations (default=`None`). |

---