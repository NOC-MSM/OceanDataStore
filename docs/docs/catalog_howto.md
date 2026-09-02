# How-To Guide — Discover :material-cloud-download:

Here, we describe some of the most common OceanDataCatalog discovery operations in a concise how-to guide (inspired by the excellent documentation of [Icechunk](https://icechunk.io/en/latest/howto/)).

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

## How do I see what Collections are available?

* To return a list of all STAC Collections in the root catalog, we can use the `available_collections` property:

```python
catalog.available_collections
```

---

## How do I search for a Collection?

* To search the **OceanDataCatalog** for the EN4.2.2 ocean analysis collection, we can use the `search()` method:

```python
catalog.search(collection='en4.2.2')
```

After performing each `search()`, our `catalog` instance stores the results, meaning we can view all available Items from our search using the `available_items` property: 

```python
catalog.available_items

```

---

## How do I search for only observational data?

* To search for only Items containing ocean observation data, we can perform the following `search()`:

```python
catalog.search(dataset_type="observation")
```

* Items are restricted to either `dataset_type="model"` or `dataset_type="observation"`.

---

## How do I search for only climatologies?

* To search for only Items containing climatologies, we can perform the following `search()`:

```python
catalog.search(product_type="climatology")
```

---

## How do I search for an Item by variable standard name?

* To search for all Items (datasets) including a variable with the standard name `'sea_surface_temperature'` in the `'noc-npd-era5'` collection, we can perform the following `search()`:

```python
catalog.search(collection='noc-npd-era5', standard_name='sea_surface_temperature')
```

---

## How do I search for a Item by ID?

* To search for all Items containing the substring `"domain"` in their path-like ID, we can perform the following `search()`:

```python
catalog.search(item_name="domain")
```

---

## How do I open a Dataset from its Item ID?

* To open an Item as an `xarray.Dataset`, we pass its path-like ID to the `open_dataset()` method as follows:

```python
ds = catalog.open_dataset(id="woa23/woa23_1991_2020_monthly_climatology")
```

* In the example above, we open the World Ocean Atlas 2023 monthly climatology (1991-2020) as a lazy `xarray.Dataset` meaning data is only loaded into memory when diagnostics are explicitly computed.

---

## **Summary**

* We can search for Items in the **OceanDataCatalog** by passing any of the following parameters to the `search()` method:

| Parameter | Description |
|---|---|
| `collection` | Collection name (e.g., `"noc-npd-era5"`) |
| `dataset_type` | `"model"`, `"observation"`, or `"reanalysis"` |
| `product_type` | `"climatology"`, `"timeseries"`, or `"ancillary"` |
| `variable_name` | Variable name in the asset (e.g., `"tos_con"`) |
| `standard_name` | CF standard name (e.g., `"sea_surface_salinity"`) |
| `item_name` | Substring to match against Item IDs |

