# How-To Guide — Analyse :material-cog:

Here, we describe some of the most common OceanDataCatalog analysis operations in a concise how-to guide (inspired by the excellent documentation of [Icechunk](https://icechunk.io/en/latest/howto/)).

For more detailed documentation on the OceanDataCatalog API, users should visit the API [Reference].

[Reference]: catalog_reference.md

---

## How do I create an OceanDataCatalog instance?

* To create a new instance of the **OceanDataCatalog** from the `"odc-stac"` (default catalog):

```python
from OceanDataStore import OceanDataCatalog

catalog = OceanDataCatalog(catalog_name="odc-stac")
```

---

## How do I open a Dataset from its Item ID?

* To open an Item as an `xarray.Dataset`, we pass its path-like ID to the `open_dataset()` method as follows:

```python
ds = catalog.open_dataset(id="woa23/woa23_1991_2020_monthly_climatology")
```

* In the example above, we open the World Ocean Atlas 2023 monthly climatology (1991-2020) as a lazy `xarray.Dataset` meaning data is only loaded into memory when diagnostics are explicitly computed.

---

## How do I subset a Dataset by time-range?

* To open a subset of the 5-day mean outputs from the 1/12-degree NOC Near-Present Day ocean sea-ice hindcast between 2004-2008, we can pass `start_datetime` and `end_datetime` parameters to the `open_dataset()` method as follows: 

```python
ds = catalog.open_dataset(
    id="noc-npd-era5/npd-eorca12-era5v1/r1i1c1f1/T5d",
    start_datetime="2004-01",
    end_datetime="2008-12",
)
```

---

## How do I subset a Dataset by spatial bounding box?

* To open a subset of the 5-day mean outputs from the 1/12-degree NOC Near-Present Day ocean sea-ice hindcast using a spatial bounding box, we can pass the `bbox` parameter to the `open_dataset()` method as follows: 

```python
ds = catalog.open_dataset(
    id="noc-npd-era5/npd-eorca12-era5v1/r1i1c1f1/T5d",
    bbox=(-65, 45, 10, 65),
)
```

* where `bbox` is a tuple of the form: `(lon_min, lat_min, lon_max, lat_max)`.

---

## How do I open a subset of variables from a Dataset?

* To open only the sea surface temperature (`tos_con`) and salinity (`sos_abs`) variables from the 1/12-degree NOC Near-Present Day ocean sea-ice hindcast, we can pass a list of variable names to the `variable_names` parameter of the `open_dataset()` method as follows:

```python
ds = catalog.open_dataset(
    id="noc-npd-era5/npd-eorca12-era5v1/r1i1c1f1/T5d",
    variable_names=["tos_con", "sos_abs"],
)
```

---

## How do I create a NEMODataTree from individual Datasets?

* To create a new `NEMODataTree` from a collection 1-degree NOC Near-Present-Day ocean sea-ice hindcast `xarray.Datasets` accessed using `open_dataset()`, we can use the `NEMODataTree.from_datasets()` constructor from [NEMO Cookbook](https://noc-msm.github.io/nemo_cookbook/) as follows:

```python
from nemo_cookbook import NEMODataTree

# Open NEMO model domain and gridT datasets:
ds_domain = catalog.open_dataset(id='noc-npd-jra55/npd-eorca1-jra55v1/r1i1c1f1/domain_cfg')
ds_gridT  = catalog.open_dataset(id='noc-npd-jra55/npd-eorca1-jra55v1/r1i1c1f1/T1y')

# Create a new grid-aware NEMODataTree:
datasets = {"parent": {"domain": ds_domain, "gridT": ds_gridT}}
nemo = NEMODataTree.from_datasets(datasets=datasets, iperio=True, nftype="F", read_mask=True)
```

---

## How do I create a NEMODataTree directly from an Icechunk repository?

* To create a new `NEMODataTree` directly from the 1/12-degree NOC Near-Present-Day ocean sea-ice hindcast Icechunk repository in the OceanDataCatalog, we can use the `NEMODataTree.from_icechunk()` constructor from [NEMO Cookbook](https://noc-msm.github.io/nemo_cookbook/) as follows:

```python
from nemo_cookbook import NEMODataTree

# Open Icechunk repository:
repo = catalog.open_dataset(id="noc-npd-era5/npd-eorca12-era5v1/r1i1c1f1/eorca12-era5v1-5d")

# Create a new grid-aware NEMODataTree:
nemo = NEMODataTree.from_icechunk(repo=repo, branch="main", iperio=True, nftype="T")
```

See the [NEMO Cookbook documentation](https://noc-msm.github.io/nemo_cookbook/) for the full range of grid-aware diagnostics available through `NEMODataTree` and `NEMODataArray`.
