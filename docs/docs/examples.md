# Examples — Analyse :material-cloud-download:

!!! abstract "Summary"

    Two worked Jupyter Notebook examples demonstrating the **OceanDataCatalog**
    API for ocean model outputs and observational datasets. Each notebook opens
    cloud-hosted ARCO datasets as lazy `xarray.Dataset` objects with spatial and
    temporal subsetting.

---

## OceanDataCatalog + Model Outputs

**Notebook:** `OceanDataCatalog_example.ipynb`

Demonstrates use of the `OceanDataCatalog` API to search the `noc-stac` catalog,
discover NOC Near-Present Day ocean model outputs, and open variables from the
eORCA1 ERA-5 simulation as a lazy `xarray.Dataset` with subsetting by variable
name, time range, and bounding box.

---

## OceanDataCatalog + Observational Datasets

**Notebook:** `OceanDataCatalog_obs_example.ipynb`

Demonstrates use of the `OceanDataCatalog` API to discover and access
observational datasets — including sea ice products — stored in the NOC STAC
catalog.

---

## Next Steps

* [How-To Guide](catalog_howto.md) — task-oriented reference for all `OceanDataCatalog` operations
* [NEMO Cookbook](https://noc-msm.github.io/nemo_cookbook/) — grid-aware diagnostics using `NEMODataTree`
