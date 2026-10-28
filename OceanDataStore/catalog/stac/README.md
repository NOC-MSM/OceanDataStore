## OceanDataStore Spatio-Temporal Access Catalogs (STAC)

### Creating the NOC STAC:
To create a new local copy of the NOC Spatio-Temporal Access Catalog, run the `create_noc_stac.py` script in a Python virtual environment:

```python
python3 create_noc_stac.py
```

This will create a new directory `ods-stac` inside the `catalogs/` directory storing a STAC containing NOC Near-Present Day & RAPID-Evolution model datasets. Further datasets will be added to the `ods-stac` in the future.

---

### Uploading a STAC to the JASMIN Object Store:

To upload a new or updated STAC to the `noc-msm` JASMIN Cloud Object Store tenancy, use a applicable CLI, such as `s5cmd`.

Note, this will require permission to write to the `oceandatastore` bucket within the `noc-msm` tenancy.

For example, to upload an updated `ods-stac`:

```bash
# Remove existing ods-stac:
s5cmd --endpoint-url https://noc-msm-o.s3-ext.jc.rl.ac.uk --profile noc_msm rm s3://oceandatastore/ods-stac/*

# Copy local ods-stac to OceanDataStore bucket:
s5cmd --endpoint-url https://noc-msm-o.s3-ext.jc.rl.ac.uk --profile noc_msm cp "path/to/ods-stac/*" s3://oceandatastore/ods-stac/
```

where `noc_msm` is the profile used to provide your user credentials for the `noc-msm` tenancy

This will make the updated STAC publicly accessible via read-only access at the following URL:

https://noc-msm-o.s3-ext.jc.rl.ac.uk/oceandatastore/ods-stac/catalog.json