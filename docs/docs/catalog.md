---
hide:
  - navigation
  - toc
---

# OceanDataCatalog :material-cloud-download:

This is the interactive OceanDataCatalog STAC browser to search our publicly available Analysis-Ready Cloud Optimsed (ARCO) ocean datasets.

To get started accessing and analysing cloud-hosted ocean datasets, including building grid-aware workflows with [**NEMO Cookbook**](https://noc-msm.github.io/nemo_cookbook/)...

→ [User Guide](catalog_userguide.md) · [How-To Guide](catalog_howto.md) ·

[here]: catalog_userguide.md

<div class="ods-stac-bar">
  <span class="ods-stac-bar__text">
    Interactive STAC catalog powered by
    <a href="https://radiantearth.github.io/stac-browser" target="_blank" rel="noopener">Radiant Earth STAC Browser</a>
    &mdash; <a href="catalog_guide.md">OceanDataCatalog API guide</a>
  </span>
  <a class="ods-stac-bar__btn"
     href="https://radiantearth.github.io/stac-browser/#/external/noc-msm-o.s3-ext.jc.rl.ac.uk/oceandatastore/noc-stac/catalog.json"
     target="_blank" rel="noopener">
    Open in new tab ↗
  </a>
</div>

<div class="ods-stac-wrapper">
  <div class="ods-stac-loading" id="stac-loading">
    <span class="ods-stac-spinner"></span>Loading catalog&hellip;
  </div>
  <iframe
    class="ods-stac-frame"
    src="https://radiantearth.github.io/stac-browser/#/external/noc-msm-o.s3-ext.jc.rl.ac.uk/oceandatastore/noc-stac/catalog.json"
    loading="lazy"
    title="NOC STAC Browser"
    onload="document.getElementById('stac-loading').style.display='none'">
  </iframe>
</div>
