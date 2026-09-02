# Examples — Publish :material-cloud-upload:

Here, we show a selection of worked examples drawn from the [`examples/cli/`](https://github.com/NOC-MSM/OceanDataStore/tree/main/examples/cli) directory, demonstrating the full `send → update` lifecycle for the eORCA1 ERA-5 Near-Present Day simulation.

---

## Example 1 — Send a single file to a Zarr store

**Script:** `examples/cli/example_send_script.sh`

Sends one annual-mean T-grid output file from the eORCA1 ERA-5 v1 simulation to a new Zarr store using `send_to_zarr`.

```bash
#!/bin/bash

# -- Input arguments -- #
filepath_grid=/path/to/model/domain_cfg.nc
filepath_gridT=/path/to/npd/model/data/eORCA1_ERA5_1y_grid_T_1976-1976.nc
store_credentials_json=.../jasmin_os_credentials.json
bucket=npd-eorca1-era5
prefix=T1y
append_dim=time_counter

# -- Send eORCA1 ERA-5 annual mean outputs to object store -- #
ods send_to_zarr -f "$filepath_gridT" -c "$store_credentials_json" -b "$bucket" -p $prefix \
                 -gf "$filepath_grid" -uc '{"nav_lon":"glamt", "nav_lat":"gphit"}' \
                 -ad $append_dim -vs \
                 -cs '{"x":360,"y":331,"deptht":25}'
```

---

## Example 2 — Send multiple files in parallel using Dask

**Script:** `examples/cli/example_send_with_dask_script.sh`

Sends the full eORCA1 ERA-5 v1 annual-mean T-grid time series (all years) to independent per-variable Zarr stores using a Dask LocalCluster.

```bash
#!/bin/bash

# -- Input arguments -- #
filepath_grid=/dssgfs01/scratch/npd/simulations/Domains/eORCA1/domain_cfg.nc
filepath_gridT=/dssgfs01/scratch/npd/simulations/eORCA1_ERA5_v1/eORCA1_ERA5_1y_grid_T_*.nc
store_credentials_json=..../jasmin_os_credentials.json
dask_config_json=..../dask_config.json
bucket=npd-eorca1-era5
prefix=T1y
append_dim=time_counter

# -- Send eORCA1 ERA-5 annual mean outputs to JASMIN OS -- #
ods send_to_zarr -f $filepath_gridT -c $store_credentials_json -b $bucket -p $prefix \
                 -gf $filepath_grid -uc '{"nav_lon":"glamt", "nav_lat":"gphit"}' \
                 -cs '{"x":360,"y":331,"deptht":25}' -ad $append_dim -vs \
                 -dc $dask_config_json
```

See [`examples/cli/dask_config.json`](https://github.com/NOC-MSM/OceanDataStore/tree/main/examples/cli/dask_config.json) for the Dask LocalCluster configuration used in this example.

---

## Example 3 — Update an existing store with a single file

**Script:** `examples/cli/example_update_script.sh`

Appends a new annual-mean T-grid file (year 1977) to the Zarr store created in Example 1 using `update_zarr`.

```bash
#!/bin/bash

# -- Input arguments -- #
filepath_grid=/path/to/model/domain_cfg.nc
filepath_gridT=/path/to/npd/model/data/eORCA1_ERA5_1y_grid_T_1977-1977.nc
store_credentials_json=.../jasmin_os_credentials.json
bucket=npd-eorca1-era5
prefix=T1y
append_dim=time_counter

# -- Update eORCA1 ERA-5 annual mean Zarr store -- #
ods update_zarr -f "$filepath_gridT" -c "$store_credentials_json" -b "$bucket" -p $prefix \
                -gf "$filepath_grid" -uc '{"nav_lon":"glamt", "nav_lat":"gphit"}' \
                -a $append_dim -cs '{"x":360,"y":331,"deptht":25}'
```

---

## Example 4 — Update an existing store with multiple files in parallel

**Script:** `examples/cli/example_update_with_dask_script.sh`

Updates the eORCA1 ERA-5 v1 T-grid Zarr stores with a batch of new annual-mean files using a Dask LocalCluster.

```bash
#!/bin/bash

# -- Input arguments -- #
filepath_grid=/dssgfs01/scratch/npd/simulations/Domains/eORCA1/domain_cfg.nc
filepath_gridT=/dssgfs01/scratch/npd/simulations/eORCA1_ERA5_v1/eORCA1_ERA5_1y_grid_T_*.nc
store_credentials_json=..../jasmin_os_credentials.json
dask_config_json=..../dask_config.json
bucket=npd-eorca1-era5
prefix=T1y
append_dim=time_counter

# -- Update eORCA1 ERA-5 annual mean Zarr stores in parallel -- #
ods update_zarr -f $filepath_gridT -c $store_credentials_json -b $bucket -p $prefix \
                -gf $filepath_grid -uc '{"nav_lon":"glamt", "nav_lat":"gphit"}' \
                -cs '{"x":360,"y":331,"deptht":25}' -ad $append_dim -vs \
                -dc $dask_config_json
```

---

## Next Steps

* [How-To Guide](publish_howto.md) — concise how-to-guide of the most common OceanDataStore publishing operations
* [CLI Reference](cli_reference.md) — complete reference to the available flags when using the OceanDataStore CLI
