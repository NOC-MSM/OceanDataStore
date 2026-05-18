import marimo

__generated_with = "0.23.6"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # OceanDataCatalog | NOC Near-Present Day

    ## About

    This Notebook demonstrates how to use the **OceanDataCatalog** API to explore the [Near-Present-Day](https://noc-msm.github.io/NOC_Near_Present_Day/) global ocean sea-ice simulations developed by the National Oceanography Centre as part of the Atlantic Climate and Environment Strategic Science ([AtlantiS](https://noc.ac.uk/projects/atlantis)) programme.
    """)
    return


@app.cell
def _():
    from OceanDataStore import OceanDataCatalog

    return (OceanDataCatalog,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    * Create an instance of the **OceanDataCatalog** class to access the National Oceanography Centre ocean model Spatio-Temporal Access Catalog (`noc-model-stac`):
    """)
    return


@app.cell
def _(OceanDataCatalog):
    catalog = OceanDataCatalog(catalog_name="noc-stac")

    catalog
    return (catalog,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    * Let's use the `available_collections` property to return the names (**IDs**) of all available dataset collections in the `noc-model-stac`:
    """)
    return


@app.cell
def _(catalog):
    catalog.available_collections
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    * Let's use the `.search()` method to search the Near-Present Day ERA-5 collection for all ocean model outputs including the sea surface temperature (SST) standard variable name:
    """)
    return


@app.cell
def _(catalog):
    catalog.search(collection='noc-npd-era5', standard_name='sea_surface_temperature')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    * Now that we have performed a `search` operation on our catalog, we can also use the `available_items` property to return the names (**IDs**) of the available STAC Items resulting from our search.
    """)
    return


@app.cell
def _(catalog):
    catalog.available_items
    return


@app.cell
def _(catalog):
    catalog.item_summary(id="noc-npd-era5/npd-eorca1-era5v1/r1i1c1f1/gn/T1y")
    return


@app.cell
def _(catalog):
    catalog.open_dataset(id='noc-npd-era5/npd-eorca1-era5v1/r1i1c1f1/gn/T1y')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    * Now, let's take a closer look at the first Item in our search results. This corresponds to the annual-mean T-grid variables output by the 1-degree NPD eORCA1 ERA5v1 simulation.

    * By looking in `properties/variable_standard_names`, we can see that 'sea_surface_temperature' is the 59th variable in this dataset and is named `tos_con`.
    """)
    return


@app.cell
def _(catalog):
    catalog.Items[0]
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    * Next, let's open a subset (1980-1990) of the annual-mean SST data as an `xarray.Dataset` by using the `.open_dataset()` method and specifying start and end date strings.

    * Here, we use the `.id` attribute of our first *Item*, but we could have also copied the `id` string from above.
    """)
    return


@app.cell
def _(catalog):
    ds = catalog.open_dataset(id=catalog.Items[0].id,
                              start_datetime='1980-01',
                              end_datetime='1990-12',
                              )

    ds
    return (ds,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    * Finally, let's create a plot of the time-mean (1980-1990) SST for the globe:
    """)
    return


@app.cell
def _(ds):
    ds['tos_con'].mean(dim='time_counter').plot(cmap='RdBu_r')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Pre-Calculated Diagnostics

    * So far, we have seen how to access NPD ocean model variables (e.g., temperature, salinity and velocities) defined on their native NEMO model grid.

    * In addition to these variables, we can also access a range of pre-calculated diagnostics, such as the meridional overturning, heat and freshwater transports across the following trans-basin sections:

        - Overturning in the Subpolar North Atlantic Program (**OSNAP**) array
        - Rapid Climate Change-Meridional Overturning Circulation and Heatflux Array (**RAPID-MOCHA**) at 26.5°N
        - Meridional Overturning Variability Experiment (**MOVE**) array at 16°N
        - South Atlantic Meridional overturning circulation Basin-wide Array (**SAMBA**) array at 34.5°S

    * These diagnostics are calculated using the [Meridional ovErTurning ciRculation diagnostIC (METRIC)](https://github.com/oj-tooth/metric) package.

    * Next, let's see how we can access these diagnostics by searching the `OceanDataCatalog` for any *Items* with identifiers containing the key word **"tn"**, which corresponds to transects which are defined on the native NEMO model grid:
    """)
    return


@app.cell
def _(catalog):
    catalog.search(collection='noc-npd-era5', item_name='tn')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    * We can see from the list of search *Items* that `OSNAP`, `RAPID_26N`, `MOVE_16N` and `SAMBA_34_5S` diagnostics are available for all NPD model configurations.

    * Now, let's open the `RAPID_26N` file for the 1-degree NPD eORCA1 ERA5v1 simulation we explored earlier.
    """)
    return


@app.cell
def _(catalog):
    ds_rapid = catalog.open_dataset(id="noc-npd-era5/npd-eorca1-era5v1/r1i1c1f1/tn/M1m/RAPID_26N")

    ds_rapid
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Ocean Model Domain Variables

    * So far, we have seen how to access NPD ocean model variables (e.g., temperature, salinity and velocities) defined on their native NEMO model grid.

    * But often when calculating diagnostics derived from these variables, such as volume, heat and freshwater transports, we also need access to the variables describing the model domain.

    * Let's next search the `OceanDataCatalog` for any *Items* with identifiers which contain the **"domain"** key word:
    """)
    return


@app.cell
def _(catalog):
    catalog.search(collection='noc-npd-era5', item_name='domain_cfg')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    * We can see from the list of search *Items* that `domain_cfg`, `mesh_mask` and `subbasin` ancillary data are available for each NPD model configuration.

    * Next, let's open the `domain_cfg` file for the 1-degree NPD eORCA1 ERA5v1 simulation we explored earlier.
    """)
    return


@app.cell
def _(catalog):
    ds_domain_cfg = catalog.open_dataset(id="noc-npd-era5/npd-eorca1-era5v1/r1i1c1f1/gn/domain/domain_cfg")

    ds_domain_cfg
    return


if __name__ == "__main__":
    app.run()
