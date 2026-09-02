# Overview :material-cloud-outline:


## **A Cloud Data Platform for Advancing Ocean Science**

---

## What is OceanDataStore?

Ocean datasets are often distributed as collections of thousands of NetCDF files stored on High Performance Computer (HPC) systems or remotely accessible archives. Accessing these datasets requires substantial data transfers, file management, and bespoke post-processing workflows on the part of the user.

**OceanDataStore** adopts a cloud-native approach where ocean data are stored in **Analysis-Ready, Cloud-Optimised ([ARCO](https://doi.org/10.1109/MCSE.2021.3059437))** formats which are described and accessed through a searchable **OceanDataCatalog**. This enables users to:

* Work with ocean data on any machine from latptops to HPC clusters.
* Access only the variables, time periods, and spatial domains needed for analysis.
* Open datasets directly as familiar `xarray.Dataset` or grid-aware `NEMODataTree` objects without downloading complete archives.
* Build scalable, reproducible workflows for ocean science using the scientific Python ecosystem (e.g., xarray, dask, etc).

---

## Who is OceanDataStore for?

OceanDataStore serves two complementary user groups:

=== "Data Producers"

    **You have ocean model outputs or observational data and want to publish them in a cloud-native format.**

    The [**OceanDataStore Command Line Interface**](publish_userguide.md) converts collections of local NetCDF files into Zarr stores or Icechunk repositories in S3-compatible object storage — with a single command and optional Dask parallelism for large-scale simulations.

    → [Publish User Guide](publish_userguide.md) · [How-To Guide](publish_howto.md) · [Examples](publish_examples.md)

=== "Data Consumers"

    **You want to discover, access and analyse cloud-native ocean datasets.**

    The [**OceanDataCatalog**](catalog_userguide.md) Python API lets you search our STAC catalog interactively, filter by data collection, variable or standard name, and open datasets as lazy `xarray.Dataset` objects with spatial and temporal subsetting or open directly as grid-aware data structures such as `NEMODataTree`.

    → [Analyse User Guide](catalog_userguide.md) · [How-To Guide](catalog_howto.md) · [Browse Catalog](catalog.md)

---

## Why use OceanDataStore?

### Analysis-Ready Cloud Optimised Data
OceanDataStore enables users to transform any NetCDF data archive directly into [**Zarr v2/v3**](https://zarr.readthedocs.io/) stores and [**Icechunk**](https://icechunk.io/) repositories — transactional, version-controlled tensor storage - in cloud object storage from the command line or a Python script. With logging, verification and optional dask parallelisation, OceanDataStore eliminates the need to build complex workflows for every dataset.

### STAC-Based Discovery
OceanDataStore published datasets are described through a Spatio-Temporal Asset Catalog [**STAC**](https://stacspec.org/en), making them discoverable both through our interactive [Dataset Catalog](catalog.md) browser and our `OceanDataCatalog` API.

### Domain-Aware Scientific Data Structures
OceanDataStore is more than a data provider; ocean science informs the design of our Analysis-Ready Cloud-Optimised datacubes. For example, users can access NEMO ocean model outputs in the form of a consolidated `NEMODataTree` data structure, enabling reproducible grid-aware computation directly from the cloud.

---

## Ecosystem

OceanDataStore is built on and integrates with the wider scientific Python ecosystem:

| Package | Role |
|---|---|
| [xarray](https://xarray.dev) | Labelled N-dimensional arrays; primary data access interface |
| [zarr](https://zarr.readthedocs.io) | Chunked, compressed cloud-native array storage |
| [icechunk](https://icechunk.io) | Transactional, version-controlled tensor storage |
| [dask](https://www.dask.org) | Parallel computing for large-scale data publishing |
| [pystac](https://pystac.readthedocs.io) | STAC catalog construction and querying |
| [nemo_cookbook](https://noc-msm.github.io/nemo_cookbook/) | Grid-aware data structures and diagnostics for NEMO model outputs |

---

## Funding

**OceanDataStore** is developed at the [**National Oceanography Centre (NOC)**](https://noc.ac.uk) and is supported by:

* [**AtlantiS**](https://atlantis.ac.uk) — Atlantic Climate and Environment Strategic Science
* [**EPOC**](https://epoc-eu.org) — Explaining & Predicting the Ocean Conveyor
* [**ARIA PROMOTE**](https://aria.org.uk/opportunity-spaces/scoping-our-planet/forecasting-tipping-points/) — Progressing earth system Modelling for Tipping Point Early warning systems
