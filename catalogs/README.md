## OceanDataStore Spatio-Temporal Access Catalogs (STAC)

### Creating the NOC Ocean Modelling STAC:
To create a new local copy of the NOC Ocean Modelling Spatio-Temporal Access Catalog, run the `create_noc_stac.py` script in a Python virtual environment:

```python
python3 create_noc_stac.py
```

This will create a new directory `noc-model-stac` inside the `catalogs/` directory storing a STAC containing NOC Near-Present Day & RAPID-Evolution model datasets. Further datasets will be added to the `noc-model-stac` in the future.

---

### Uploading a STAC to the JASMIN Object Store:

To upload a new or updated STAC to the `noc-msm` JASMIN Cloud Object Store tenancy, use a applicable CLI, such as `s3cmd` or `MinIO`.

Note, this will require permission to write to the `oceandatastore` bucket within the `noc-msm` tenancy.

For example, to upload an updated `noc-model-stac`:

```bash
mc cp --recursive /path/to/my/OceanDataStore/catalogs/noc-model-stac/ jasmin-os/oceandatastore/noc-model-stac/
```

This will make the updated STAC publicly accessible via read-only access at the following URL:

https://noc-msm-o.s3-ext.jc.rl.ac.uk/oceandatastore/noc-model-stac/catalog.json