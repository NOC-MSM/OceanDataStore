<p align="left">
    <img src="./docs/docs/assets/icons/noc_logo_black.png" alt="National Oceanography Centre logo" width="190" height="65">
    &nbsp;&nbsp;
    <img src="./docs/docs/assets/icons/OceanDataStore_logo.png" alt="OceanDataStore logo" width="150" height="100">
</p>

# **OceanDataStore**

[![Xarray](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydata/xarray/refs/heads/main/doc/badge.json)](https://xarray.dev)
[![Powered by Pixi](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/prefix-dev/pixi/main/assets/badge/v0.json)](https://pixi.sh)
[![Tests](https://github.com/NOC-MSM/OceanDataStore/actions/workflows/ci_tests.yml/badge.svg?branch=dev)](https://github.com/NOC-MSM/OceanDataStore/actions/workflows/ci_tests.yml?query=branch%3Adev)
[![Docs](https://github.com/NOC-MSM/OceanDataStore/actions/workflows/ci_docs.yml/badge.svg?branch=dev)](https://github.com/NOC-MSM/OceanDataStore/actions/workflows/ci_docs.yml?query=branch%3Adev)

**OceanDataStore** is an open-source Python library for creating, publishing, discovering, and accessing cloud-native ocean datasets.

**OceanDataStore** enables ocean modelling and observational communities to work with Analysis-Ready, Cloud-Optimised (**ARCO**) datasets stored in object storage, including a:

* Command Line Interface (**CLI**) to convert traditional ocean datasets into scalable cloud formats such as Zarr stores and Icechunk repositories.

* Intuitive **OceanDataCatalog** API to discover and access datasets using Spatio-Temporal Asset Catalog (**STAC**) metadata.


## **Why OceanDataStore?**

Traditional ocean datasets are often distributed as collections of thousands of NetCDF files stored on HPC systems or remote archives. Accessing these datasets can require substantial data transfers, complex file management, and bespoke workflows.

**OceanDataStore** adopts a cloud-native approach where datasets are stored in **ARCO** formats and described through a searchable **STAC** catalogue.

This enables users to:

* Access only the variables, time periods, and spatial domains required for analysis.
* Open datasets directly as `xarray.Dataset` objects without downloading complete archives.
* Work seamlessly with the scientific Python ecosystem, including xarray, dask, and zarr.
* Build scalable, reproducible workflows for ocean science.

## **Key Features**

🌊 **Discover and access ocean datasets with OceanDataCatalog**
* Search STAC catalogs for available ocean model and observational datasets.
* Explore dataset metadata and available variables.
* Open cloud-hosted datasets directly as lazy `xarray.Dataset` objects.

☁️ **Create and publish ARCO ocean datasets**
* Convert collections of NetCDF files into cloud-native Zarr datasets.
* Write directly to S3-compatible object storage.
* Use Dask for parallel processing of large simulations and observational products.

🔄 **Support reproducible ocean data workflows**
* Integrate ocean model output and observations through a common access interface.
* Develop scalable model validation workflows.
* Facilitate FAIR data practices for ocean science.


## **Installation**
We recommend downloading and installing **OceanDataStore** into a new virtual environment via GitHub.

After activating a new virtual environment, pip install **OceanDataStore** from GitHub:
```{bash}
pip install oceandatastore
```

Alternatively, users can install **OceanDataStore** (including the latest commits) via GitHub:

```{bash}
pip install git+https://github.com/NOC-MSM/OceanDataStore.git
```

### **Quick Start**

**1. Create and Publish an ARCO Dataset**

**OceanDataStore** provides command-line tools for converting collections of NetCDF files into Zarr datasets stored in S3-compatible object storage.

For example, a large ocean model simulation can be converted into a cloud-native dataset using:

```bash
ods send_to_zarr \
    -f /path/to/files*.nc \
    -c credentials.json \
    -b my_bucket \
    -p my_ocean_model \
    -cs '{"x": 2160, "y": 1803}' \
    -dc dask_config.json \
    -zv 3
```

More complete publishing workflows and examples are available in the `examples` directory and documentation.


**2. Discover and Access Ocean Datasets**

**OceanDataCatalog** provides a Python interface for searching, exploring, and opening datasets described by **STAC** metadata.

```python
from oceandatastore import OceanDataCatalog

# Connect to the NOC STAC catalog:
catalog = OceanDataCatalog(catalog_name="noc-stac")

# Search the catalog:
catalog.search(
    collection="noc-npd-era5"
)

# Open a dataset directly as an xarray.Dataset:
ds = catalog.open_dataset(
    id="noc-npd-era5/npd-eorca1-era5v1/r1i1c1f1/gn/T1m",
    variable_names=["tos_con"],
    start_datetime="2004-01",
    end_datetime="2008-12",
)
```

Since datasets are opened lazily using xarray and dask, analyses can scale from a laptop to HPC and cloud environments.



## **Scientific Use Cases**

**OceanDataStore** supports a broad range of ocean science workflows, including:

**Ocean Model Validation**
* Compare ocean simulations against observational products using a common data access pattern.

* Build reproducible evaluation workflows across multiple models and experiments.

**Cloud-Native Model Archives**
* Publish large-scale ocean simulations as FAIR, discoverable datasets without sharing raw file archives.

**Ocean Observations**
* Access observational products alongside model output through a single catalog interface.


### **Documentation**
Documentation, examples, and API references are available [**here**](https://noc-msm.github.io/OceanDataStore/)


## **Contributing**
**OceanDataStore** is under active development and we welcome feedback and contributions from the ocean modelling, observational, and wider marine data communities.


## **Funding**
The ongoing development of OceanDataStore is funded by the following projects: 

- **AtlantiS**: [Atlantic Climate and Environment Strategic Science](https://atlantis.ac.uk)

## **Contact**

Ollie Tooth (oliver.tooth@noc.ac.uk)