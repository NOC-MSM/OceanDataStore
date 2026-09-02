# What's New

## v0.2.0

!!! tip "Latest release"

### New Features

- **`send_to_zarr`** — Write local NetCDF files to Zarr v2/v3 stores in S3-compatible object storage, with optional Dask parallelism for large file collections.
- **`update_zarr`** — Append or replace data in existing Zarr stores with compatibility checks (chunk size, dimension compatibility).
- **`send_to_icechunk`** — Write local NetCDF files to new Icechunk repositories with transactional commit support.
- **`update_icechunk`** — Update existing Icechunk repositories with new data and commit tracking.
- **`list`** — List objects in a cloud object store bucket.
- **`OceanDataCatalog`** — Python API for searching the NOC STAC catalog and opening ARCO datasets as lazy `xarray.Dataset` objects with spatial and temporal subsetting.
- **Domain file support** (`--grid-filepath`) — Include model domain variables (e.g., longitude, latitude, grid metrics) in published stores.
- **Dask LocalCluster integration** — Parallel publishing of large simulations via a JSON-configurable LocalCluster.
- **Per-variable publishing** (`--variables`) — Select specific variables from multi-variable NetCDF files.
- **Chunk strategy control** (`--chunk-strategy`) — Override default chunk dimensions via a JSON configuration string.
- **NOC STAC catalog** — Four STAC collections published: `noc-npd-era5`, `noc-npd-jra55`, `noc-rapid-evolution`, `nsidc`.
