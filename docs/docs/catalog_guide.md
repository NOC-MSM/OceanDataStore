# OceanDataCatalog API

!!! abstract "Summary"

    **This is the User Guide for the OceanDataCatalog API to explore and access ocean data stored in the JASMIN Object Store.**

---

## What is the OceanDataCatalog?

**OceanDataCatalog** is a Python API which allows users to:

* Interfaces with National Oceanography Centre Spatio-Temporal Access Catalogs ([**STAC**](https://stacspec.org/en)) to expose collections of publicly available ocean model outputs stored in the JASMIN Object Store.
* Search catalogs by collection of ocean model outputs, standard variable names or platform (type of grid on which outputs are stored).
* Subset & open Analysis-Ready Cloud Optimised ([**ARCO**](https://doi.org/10.1109/MCSE.2021.3059437)) datasets as lazy [**xarray**](https://docs.xarray.dev/en/stable/user-guide/data-structures.html) Datasets.

## What is STAC?

Spatio-Temporal Asset Catalogs (**STAC**) provides a standardized way to describe geospatial and temporal data so that it can be easily discovered & shared across many different platforms. 

A STAC catalog organises datasets as a **Collection** of **Items** — each representing a geospatial asset (e.g., a model output file or satellite image) — and describes their spatial and temporal extent through structured metadata.

STAC is intentionally simple and extensible: it builds on widely used web standards (JSON and GeoJSON) and can describe geospatial assets stored in diverse formats, including large, cloud-optimized Zarr stores & Icechunk repositories.

Behind the **OceanDataCatalog** API, STAC catalogs are used to describe publicly available ocean model outputs produced by the National Oceanography Centre.

### STAC Basics:

📁 **Catalog** — Container storing STAC **Collections** or other **Catalogs** - provides high-level metadata about its contents.

🗂️ **Collection** — Group of related **Items** that share common metadata, such as a modelling activity or model configuration.

📄 **Item** — Single spatio-temporal record within a Collection, typically representing one dataset instance (e.g., a model output file / dataset). Each **Item** includes geometry, timestamps, and links to a data **Asset**.

🧩 **Asset** — Actual data or file associated with an **Item**, such as a Zarr Store, NetCDF file, or Icechunk repository. **Assets** include URLs and media types which determines how data can be accessed.

## NOC Ocean Modelling STAC

National Oceanography Centre model outputs are organised in the `noc-model-stac` **Catalog**, which serves as the highest-level STAC object in our hierarchy.

```
Catalog: noc-model-stac
|
└── Collection: noc-npd-era5
    |
    ├── Catalog: npd-eorca1-era5v1
    |   ├── Catalog: gn
    |   └── Catalog: tn
    |
    ├── Catalog: npd-eorca025-era5v1
    |   ├── Catalog: gn
    |   └── Catalog: tn
    |
    └── Catalog: npd-eorca12-era5v1
        ├── Catalog: gn
        └── Catalog: tn

```

The `noc-model-stac` **Catalog** is comprised of STAC **Collections** which group **Items** belonging to the same modelling activity. In the example above, we have included the NOC Near-Present Day simulations produced using ERA-5 atmospheric forcing in the `noc-npd-era5` **Collection**.

The `noc-npd-era5` **Collection** is in-turn comprised of two **Catalogs** used to differentiate between ocean model outputs stored on their native global model grid `gn` and those diagnostics stored along transects of the native model grid `tn`.

Inside each of the `gn` and `tn` **Catalogs** are STAC **Items** corresponding to ocean model output datasets. These are named according to both the location on the native NEMO model grid where variables are stored and the temporal frequency at which they are output by the NEMO ocean model (see table below).

| Example     | Grid               |   Frequency   |
| ----------- | ------------------ | --------------|
| `T1y`         | **T** (scalar)   |  Annual Means |
| `U1m`         | **U** (vector)   | Monthly Means |
| `I5d`         | **I** (sea ice)  | 5-day Means   |
| `W1d`         | **W** (vector)   |  Daily-Means  |


To improve the accesibility of NOC ocean model assets, each **Item** is given a unique path-like identifier describing its relationship within the wider `noc-model-stac` **Catalog**.

For example, `noc-npd-era5/npd-eorca1-era5v1/gn/T1y` identifies the **Item** containing monthly-mean scalar variables (e.g., conservative temperature) for the eORCA1-ERA5v1 (1-degree) simulation contained in the NOC Near-Present Day ERA-5 **Collection**.

## How To...

**A Quickstart Guide to Common Operations using OceanDataCatalog**

Below, we briefly introduce some of the most common `OceanDataCatalog` operations in a concise how-to guide (inspired by the excellent documentation of [**Icechunk**](https://icechunk.io/en/latest/howto/)).

### Create a new OceanDataCatalog instance

We can assign a new instance of the **OceanDataCatalog** to the object `catalog` using:

```python
catalog = OceanDataCatalog(catalog_name="noc-model-stac")
```

Here, we use the `noc-model-stac` (default) **Catalog**.

### Explore Available Collections

We can return a list of available **Collections** contained in the root **Catalog** (`noc-model-stac`) using:

```python
catalog.available_collections
```

### Searching the OceanDataCatalog

We search for **Items** contained in the root **Catalog** using:

```python
catalog.search(collection='noc-npd-jra55', standard_name='sea_surface_salinity')
```

In the example above, we confine our search to the `noc-npd-jra55` collection before searching for any **Item** which includes a variable with the standard name `sea_surface_salinity`.

Users can search the root **Catalog** using any combination of the following parameters:

* `collection` : Activity **Collection** name (e.g., `noc-npd-era5`).

* `platform` : Platform **Catalog** name (e.g., `gn`).

* `variable_name` : Variable name contained in **Item** **Asset** (e.g., `tos_con`).

* `standard_name` : Standard variable name contained in **Item** **Asset** (e.g., `sea_surface_temperature`).

* `item_name` : Substring to filter Item IDs (e.g., `domain`).

**Important:** Once a search has been performed on the root **Catalog**, the `.Collection` and `.Items` are populated according to the results of last query performed. In the example above, the `catalog.Collection` attribute would return the `noc-npd-jra55` STAC **Collection** and the `catalog.Items` attribute would return a list of STAC **Items** meeting the specified criteria.

### Opening a dataset using the OceanDataCatalog

Once we have searched the `noc-model-stac` and found the unique identifier of the **Item** we would like to explore further, we can then open its associated **Asset** as a lazy `xarray.Dataset` using the `.open_dataset()` method:

```python
catalog.open_dataset(id="noc-npd-era5/npd-eorca1-era5v1/gn/T1m",
                     variable_names=["tos_con", "sos_abs"]
                     start_datetime='2004-01',
                     end_datetime='2008-12',
                     bbox=(-65, 45, 10, 65)
                    )
```

In the example above, we open the monthly mean sea surface temperature `tos_con` and sea surface salinity `sos_abs` variable from the eORCA1-ERA5v1 NOC Near-Present Day simulation, subsetting the data to consider only 2004-2008 and a geographical bounding box with limits (-65°E to 10°E) & (45°N to 65°N).
