# Getting Started

## Installation

We recommend installing the latest release of **OceanDataStore** into a dedicated Python virtual environment.

=== "pip (latest release)"

    ```bash
    pip install oceandatastore
    ```

=== "pip (latest commits)"

    ```bash
    pip install git+https://github.com/NOC-MSM/OceanDataStore.git
    ```

??? tip "Setting up a virtual environment"

    Using venv:

    ```sh
    python3 -m venv env_ods
    source env_ods/bin/activate
    ```

    Using conda / miniconda / mamba:

    ```sh
    conda create -n env_ods python=3.13
    conda activate env_ods
    ```

---

## Usage

### :material-cloud-upload: Publish Data — CLI

Write and update data to S3-compatible object stores (e.g. [**JASMIN Object Store**](https://help.jasmin.ac.uk/docs/short-term-project-storage/using-the-jasmin-object-store/)):

| Command | Description |
|---|---|
| `send_to_zarr` | Send local NetCDF file(s) to a new Zarr store |
| `update_zarr` | Append local NetCDF file(s) to an existing Zarr store |
| `send_to_icechunk` | Send local NetCDF file(s) to a new Icechunk repository |
| `update_icechunk` | Append local NetCDF file(s) to an existing Icechunk repository |
| `list` | List objects in a cloud object store bucket |

→ [Publish User Guide](publish_userguide.md) · [How-To Guide](publish_howto.md) · [Examples](publish_examples.md)

---

### :material-cloud-download: Analyse — OceanDataCatalog

Search and access [ARCO](https://doi.org/10.1109/MCSE.2021.3059437) ocean datacubes as familar [xarray](https://docs.xarray.dev/en/stable/) Datasets or Icechunk repositories:

- Discover ocean model and observational data via a [STAC](https://stacspec.org/en) catalog.
- Filter by collection, variable name, or data type.
- Subset data by spatial bounding box and/or time range.

→ [Analyse User Guide](catalog_userguide.md) · [How-To Guide](catalog_howto.md) · [Browse Catalog](catalog.md)

---

## Next Steps...

| I want to… | Go to… |
|---|---|
| Publish ocean model outputs | [Publish → User Guide](publish_userguide.md) |
| Publish large simulations in parallel | [Publish → How-To Guide](publish_howto.md) |
| Browse publicly available ocean data | [Explore → Dataset Catalog](catalog.md) |
| Discover ocean data by variable | [Analyse → User Guide](catalog_userguide.md) |
| Access ocean data stored in the cloud using Python | [Analyse → How-To Guide](catalog_howto.md) |
| Explore end-to-end examples | [Publish Examples](publish_examples.md) · [Analyse Examples](examples.md) |
