"""
oceandatacatalog.py

Description:
This module defines the OceanDataCatalog() class which is a
container for the NOC STAC and a basic API for accessing data
using pystac, Zarr and Icechunk.

Authors:
    - Ollie Tooth
"""
import os
from typing import Optional

import icechunk
import numpy as np
import pystac
import xarray as xr

# -- NOC brand CSS -- #
_NOC_CSS = """
<style>
  .ods-card {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-size: 13px;
    border: 1px solid #0087c1;
    border-radius: 6px;
    overflow: hidden;
    max-width: 950px;
    margin: 6px 0;
    box-shadow: 0 1px 4px rgba(0,63,112,0.12);
  }
  .ods-header {
    background: #003f70;
    color: #ffffff;
    padding: 8px 14px;
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.3px;
  }
  .ods-badge {
    background: #0087c1;
    color: #ffffff;
    border-radius: 12px;
    padding: 1px 9px;
    font-size: 11px;
    font-weight: 500;
    white-space: nowrap;
  }
  .ods-badge-neutral {
    background: #5a9cbf;
    color: #ffffff;
    border-radius: 12px;
    padding: 1px 9px;
    font-size: 11px;
    font-weight: 500;
    white-space: nowrap;
  }
  .ods-body {
    background: #eef6fb;
    padding: 10px 14px;
  }
  .ods-stats {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 8px;
  }
  .ods-stat {
    background: #ffffff;
    border: 1px solid #b3d7ea;
    border-radius: 5px;
    padding: 4px 10px;
    font-size: 12px;
    color: #003f70;
  }
  .ods-stat span {
    font-weight: 600;
  }
  .ods-url {
    font-size: 12px;
    font-weight: 500;
    color: #555;
    word-break: break-all;
  }
  .ods-url a { color: #0087c1; text-decoration: none; }
  .ods-url a:hover { text-decoration: underline; }
  .ods-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    margin-top: 2px;
  }
  .ods-table thead tr {
    background: #003f70;
    color: #ffffff;
  }
  .ods-table thead th {
    padding: 6px 10px;
    text-align: left;
    font-weight: 600;
    white-space: nowrap;
  }
  .ods-table tbody tr:nth-child(even) { background: #d6ecf5; }
  .ods-table tbody tr:nth-child(odd)  { background: #ffffff; }
  .ods-table tbody tr:hover { background: #b3d7ea; }
  .ods-table td {
    padding: 5px 10px;
    vertical-align: top;
    text-align: left;
    border-bottom: 1px solid #cce4f0;
  }
  .ods-id {
    font-family: monospace;
    font-size: 11px;
    color: #003f70;
    white-space: nowrap;
  }
  details.ods-details > summary {
    cursor: pointer;
    color: #0087c1;
    font-size: 11px;
    list-style: none;
    user-select: none;
  }
  details.ods-details > summary::-webkit-details-marker { display: none; }
  details.ods-details > summary::before { content: "▶ "; font-size: 9px; }
  details.ods-details[open] > summary::before { content: "▼ "; font-size: 9px; }
  details.ods-details .ods-detail-body {
    margin-top: 4px;
    color: #333;
    font-size: 11px;
    line-height: 1.5;
  }
  .ods-section-title {
    font-weight: 600;
    color: #003f70;
    margin-bottom: 6px;
    font-size: 12px;
  }
  .ods-code {
    background: #ffffff;
    color: #003f70;
    font-family: monospace;
    font-size: 12px;
    padding: 8px 12px;
    border-radius: 4px;
    border: 1px solid #cce4f0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-top: 4px;
  }
  .ods-copy-btn {
    background: #0087c1;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    cursor: pointer;
    white-space: nowrap;
    flex-shrink: 0;
  }
  .ods-copy-btn:hover { background: #006fa0; }
  .ods-none { color: #999; font-style: italic; }
</style>
"""

# -- Utility Functions -- #
def apply_bbox(ds: xr.Dataset,
               bbox: tuple
               ) -> xr.Dataset:
    """
    Apply a geographical bounding box to subset an xarray Dataset.

    Parameters
    ----------
    ds : xr.Dataset
        Input xarray Dataset.
    bbox : tuple
        Geographical bounding box in the format (min_lon, max_lon, min_lat, max_lat).

    Returns
    -------
    xr.Dataset
        Geographically subsetted xarray Dataset.
    """
    # -- Validate Inputs -- #
    if not isinstance(ds, xr.Dataset):
        raise ValueError("'ds' must be an xarray Dataset.")
    if not (isinstance(bbox, tuple) and len(bbox) == 4):
        raise ValueError("'bbox' must be a tuple of the form (min_lon, max_lon, min_lat, max_lat).")
    
    # -- Identify geographical coordinate names & dimensions -- #
    # Default lat/lon coord names:
    lon_name, lat_name = "nav_lon", "nav_lat"
    # Update lat/lon coord names via standard_name attributes:
    for coord in ds.coords:
        if ds[coord].attrs.get('standard_name', '').lower() == 'longitude':
            lon_name = coord
        if ds[coord].attrs.get('standard_name', '').lower() == 'latitude':
            lat_name = coord

    # -- Apply Bounding Box -- #
    if (ds[lon_name].ndim > 1) and (ds[lat_name].ndim > 1):
        # -- Case 1: 2D lat/lon coordinates -- #
        # Identify lat/lon coordinate dimensions:
        if ds[lon_name].dims != ds[lat_name].dims:
            raise ValueError("Longitude and latitude coordinates must have the same dimensions.")
        else:  
            y_name, x_name = ds[lon_name].dims

        # Define bbox mask:
        mask = (
            (ds[lon_name] >= bbox[0])
            & (ds[lon_name] <= bbox[2])
            & (ds[lat_name] >= bbox[1])
            & (ds[lat_name] <= bbox[3])
            )

        # Find rows/columns containing at least one valid grid point:
        rows = mask.any(dim=x_name)
        cols = mask.any(dim=y_name)
        y_idx = np.where(rows.compute())[0]
        x_idx = np.where(cols.compute())[0]

        if len(y_idx) == 0 or len(x_idx) == 0:
            raise ValueError("No grid points found inside bbox")

        # Subset dataset to bounding box:
        ds_subset = (ds
                     .where(mask, drop=False)
                     .isel({y_name: slice(y_idx.min(), y_idx.max() + 1),
                            x_name: slice(x_idx.min(), x_idx.max() + 1),
                           })
                    )
    else:
        # -- Case 2: 1D lat/lon coordinates -- #
        ds_subset = ds.sel({lon_name: slice(bbox[0], bbox[1]), 
                            lat_name: slice(bbox[2], bbox[3])
                            })

    return ds_subset


def apply_time_bounds(ds: xr.Dataset,
                      start_datetime: str | None = None,
                      end_datetime: str | None = None
                      ) -> xr.Dataset:
    """
    Apply temporal subsetting to an xarray Dataset.

    Parameters
    ----------
    ds : xr.Dataset
        Input xarray Dataset.
    start_datetime : str, optional
        Start datetime in ISO format (e.g., 'YYYY-MM-DDTHH:MM:SS').
    end_datetime : str, optional
        End datetime in ISO format (e.g., 'YYYY-MM-DDTHH:MM:SS').

    Returns
    -------
    xr.Dataset
        Temporally subsetted xarray Dataset.
    """
    # -- Validate Inputs -- #
    if not isinstance(ds, xr.Dataset):
        raise ValueError("'ds' must be an xarray Dataset.")
    if start_datetime is not None:
        if not isinstance(start_datetime, str):
            raise ValueError("'start_datetime' must be a string in ISO format (e.g., 'YYYY-MM-DDTHH:MM:SS').")
    if end_datetime is not None:
        if not isinstance(end_datetime, str):
            raise ValueError("'end_datetime' must be a string in ISO format (e.g., 'YYYY-MM-DDTHH:MM:SS').")

    # -- Identify time dimension -- #
    for coord in ds.dims:
        if 'time' in coord.lower():
            time_name = coord
            break

    # -- Apply temporal subsetting -- #
    ds_subset = ds.sel({time_name: slice(start_datetime, end_datetime)})

    return ds_subset


# -- Define CatalogSummary() class -- #
class CatalogSummary:
    """
    Container for OceanDataCatalog summary.

    Parameters
    ----------
    num_collections : int
        The number of collections in the catalog.
    num_items : int
        The number of items in the catalog.
    other_info : dict
        Any other relevant summary information about the catalog.
    """
    def __init__(self,
                 display_text: str | None = None,
                 display_html: str | None = None,
                 ):
        self.display_text = display_text
        self.display_html = display_html

    def __repr__(self):
        """
        Plain text representation of the CatalogSummary.
        """
        return self.display_text

    def _repr_html_(self):
        """
        HTML representation of the CatalogSummary.
        """
        return self.display_html

# -- Define OceanDataCatalog() class -- #
class OceanDataCatalog:
    """
    A class to interact with the National Oceanography Centre (NOC)
    Spatio-Temporal Access Catalogs (STAC).

    The catalog provides metadata and access to oceanographic
    datasets stored in cloud object storage. Users can search the
    catalog, inspect available Items, and open datasets as familiar
    xarray data structures.

    Parameters
    ----------
    catalog_name : str, optional
        Name of the NOC STAC catalog to use.
    catalog_url : str, optional
        Path or URL to the root STAC catalog. If not provided,
        a default path to the NOC STAC catalog is used.

    Attributes
    ----------
    catalog : pystac.Catalog
        The root NOC STAC catalog.
    collection : pystac.Collection or None
        The current STAC Collection being viewed.
    items : list of pystac.Item
        The list of STAC Items returned from the most recent query.
    """
    def __init__(self,
                 catalog_name: str = "noc-stac",
                 catalog_url: str = None
                 ):
        # Define the URL to the NOC STAC root catalog:
        self._stac_url = catalog_url or f"https://noc-msm-o.s3-ext.jc.rl.ac.uk/oceandatastore/{catalog_name}/catalog.json"
        # Store the root catalog as a class attribute:
        self.Catalog = pystac.read_file(self._stac_url)

        # Define the Collection and Items attributes:
        self.Collection = None
        self.Items = None
        # Cache the catalog name for display:
        self._catalog_name = catalog_name

    def __repr__(self) -> str:
        """
        Plain text representation of the OceanDataCatalog.
        """
        n_collections = len(self.available_collections)
        col_name = self.Collection.id if self.Collection else "—"
        n_items = len(self.Items) if self.Items is not None else "—"
        return (
            f"OceanDataCatalog\n"
            f"  Catalog:     {self._catalog_name}\n"
            f"  URL:         {self._stac_url}\n"
            f"  Collections: {n_collections} available\n"
            f"  Collection:  {col_name}\n"
            f"  Search:      {n_items} items"
        )


    def _repr_html_(self) -> str:
        """
        HTML representation of the OceanDataCatalog.
        """
        n_collections = len(self.available_collections)
        col_name = self.Collection.id if self.Collection else "<span class='ods-none'>none selected</span>"
        n_items = (
            f"{len(self.Items)} items"
            if self.Items is not None
            else "<span class='ods-none'>no search yet</span>"
        )
        return (
            f"{_NOC_CSS}"
            f"<div class='ods-card'>"
            f"  <div class='ods-header'>"
            f"    OceanDataCatalog"
            f"    <span class='ods-badge'>{self._catalog_name}</span>"
            f"  </div>"
            f"  <div class='ods-body'>"
            f"    <div class='ods-stats'>"
            f"      <div class='ods-stat'>Collections&nbsp;<span>{n_collections}</span></div>"
            f"      <div class='ods-stat'>Active collection&nbsp;<span>{col_name}</span></div>"
            f"      <div class='ods-stat'>Last search&nbsp;<span>{n_items}</span></div>"
            f"    </div>"
            f"    <div class='ods-url'>URL <a href='{self._stac_url}' target='_blank'>{self._stac_url}</a></div>"
            f"  </div>"
            f"</div>"
        )


    @property
    def available_collections(self) -> list[str]:
        """
        List available collection IDs in the NOC STAC catalog.
        """
        return [col.id for col in self.Catalog.get_all_collections()]


    @property
    def available_items(self) -> list[str]:
        """
        List available Item IDs in the current Collection or the root Catalog.
        """
        if self.Items is not None:
            # Return all Item IDs from the most recent search:
            return [item.id for item in self.Items]
        else:
            # Return first 25 Item IDs from the current Collection or root Catalog:
            scope = self.Collection if self.Collection else self.Catalog
            return [next(scope.get_items(recursive=True), None).id for _ in range(25)]


    def summary(self) -> CatalogSummary:
        """
        Summary of the most recent OceanDataCatalog search.

        * In Jupyter / Marimo environments a styled HTML table is displayed.
        * In plain Python / CLI environments a formatted text table is printed instead.
        """
        # -- Validate STAC Items -- #
        if not self.Items:
            raise ValueError("No Items returned in most recent query. Use 'search()' to query Catalog.")

        n = len(self.Items)

        # ----- HTML Output ----- #
        rows_html = ""
        for item in self.Items:
            title   = item.properties.get("title", "")
            platform = item.properties.get("platform", "<span class='ods-none'>—</span>")
            start   = item.properties.get("start_datetime", "<span class='ods-none'>—</span>")
            end     = item.properties.get("end_datetime",   "<span class='ods-none'>—</span>")
            variables = item.properties.get("variables", [])
            if variables:
                var_list = "<br>".join(variables)
                vars_cell = (
                    f"<details class='ods-details'>"
                    f"<summary>{len(variables)} variable{'s' if len(variables) != 1 else ''}</summary>"
                    f"<div class='ods-detail-body'>{var_list}</div>"
                    f"</details>"
                )
            else:
                vars_cell = "<span class='ods-none'>—</span>"

            title_cell = title if title else "<span class='ods-none'>—</span>"
            rows_html += (
                f"<tr>"
                f"<td><span class='ods-id'>{item.id}</span></td>"
                f"<td>{title_cell}</td>"
                f"<td>{platform}</td>"
                f"<td>{start}</td>"
                f"<td>{end}</td>"
                f"<td>{vars_cell}</td>"
                f"</tr>"
            )

        col_badge = (
            f"<span class='ods-badge-neutral'>{self.Collection.id}</span>"
            if self.Collection else ""
        )
        html = (
            f"{_NOC_CSS}"
            f"<div class='ods-card'>"
            f"  <div class='ods-header'>"
            f"    Search Results"
            f"    <span class='ods-badge'>{n} Item{'s' if n != 1 else ''} found</span>"
            f"    {col_badge}"
            f"  </div>"
            f"  <div class='ods-body'>"
            f"    <table class='ods-table'>"
            f"      <thead><tr>"
            f"        <th>Item ID</th><th>Title</th><th>Platform</th>"
            f"        <th>Start Date</th><th>End Date</th><th>Variables</th>"
            f"      </tr></thead>"
            f"      <tbody>{rows_html}</tbody>"
            f"    </table>"
            f"  </div>"
            f"</div>"
        )

        # ----- Plain-Text Output ----- #
        col_w = [46, 28, 10, 12, 12, 30]
        headers = ["Item ID", "Title", "Platform", "Start Date", "End Date", "Variables"]
        sep = "+" + "+".join("-" * (w + 2) for w in col_w) + "+"
        header_row = "| " + " | ".join(h.ljust(col_w[i]) for i, h in enumerate(headers)) + " |"
        text_lines = [f"Search Results — {n} Item{'s' if n != 1 else ''} found", sep, header_row, sep]
        for item in self.Items:
            variables = item.properties.get("variables", [])
            row = [
                item.id[:col_w[0]],
                item.properties.get("title", "")[:col_w[1]],
                item.properties.get("platform", "")[:col_w[2]],
                item.properties.get("start_datetime", "")[:col_w[3]],
                item.properties.get("end_datetime", "")[:col_w[4]],
                (", ".join(variables))[:col_w[5]],
            ]
            text_lines.append("| " + " | ".join(v.ljust(col_w[i]) for i, v in enumerate(row)) + " |")
        text_lines.append(sep)
        text = "\n".join(text_lines)

        return CatalogSummary(display_text=text, display_html=html)


    def collection_summary(self) -> CatalogSummary:
        """
        Display a summary table of all Collections in the OceanDataCatalog:

        * In Jupyter / Marimo environments a styled HTML table is displayed.
        * In plain Python / CLI environments a formatted text table is printed instead.
        """
        collections = list(self.Catalog.get_all_collections())
        n = len(collections)

        def _extent_dates(col):
            try:
                ext = col.extent.temporal.intervals
                start = ext[0][0].strftime("%Y-%m-%d") if ext[0][0] else "—"
                end   = ext[0][1].strftime("%Y-%m-%d") if ext[0][1] else "present"
            except Exception:
                start, end = "—", "—"
            return start, end

        # ----- HTML Output ----- #
        rows_html = ""
        for col in collections:
            start, end = _extent_dates(col)
            desc = col.description or ""
            desc_cell = (
                f"<details class='ods-details'>"
                f"<summary>Summary</summary>"
                f"<div class='ods-detail-body'>{desc.replace('**', '')}</div>"
                f"</details>"
                if desc else "<span class='ods-none'>—</span>"
            )
            active = " <span class='ods-badge' style='font-size:10px'>active</span>" if (
                self.Collection and col.id == self.Collection.id
            ) else ""
            col_title_cell = col.title if col.title else "<span class='ods-none'>—</span>"
            rows_html += (
                f"<tr>"
                f"<td><span class='ods-id'>{col.id}</span>{active}</td>"
                f"<td>{col_title_cell}</td>"
                f"<td>{desc_cell}</td>"
                f"<td>{start}</td>"
                f"<td>{end}</td>"
                f"</tr>"
            )

        html = (
            f"{_NOC_CSS}"
            f"<div class='ods-card'>"
            f"  <div class='ods-header'>"
            f"    Collections"
            f"    <span class='ods-badge'>{n} available</span>"
            f"  </div>"
            f"  <div class='ods-body'>"
            f"    <table class='ods-table'>"
            f"      <thead><tr>"
            f"        <th>Collection ID</th><th>Title</th><th>Description</th>"
            f"        <th>From</th><th>To</th>"
            f"      </tr></thead>"
            f"      <tbody>{rows_html}</tbody>"
            f"    </table>"
            f"  </div>"
            f"</div>"
        )

        # ----- Plain-Text Output ----- #
        col_w = [30, 42, 12, 12]
        headers = ["Collection ID", "Title", "From", "To"]
        sep = "+" + "+".join("-" * (w + 2) for w in col_w) + "+"
        header_row = "| " + " | ".join(h.ljust(col_w[i]) for i, h in enumerate(headers)) + " |"
        text_lines = [f"Collections — {n} available", sep, header_row, sep]
        for col in collections:
            start, end = _extent_dates(col)
            row = [
                col.id[:col_w[0]],
                (col.title or "")[:col_w[1]],
                start[:col_w[2]],
                end[:col_w[3]],
            ]
            text_lines.append("| " + " | ".join(v.ljust(col_w[i]) for i, v in enumerate(row)) + " |")
        text_lines.append(sep)
        text = "\n".join(text_lines)

        return CatalogSummary(display_text=text, display_html=html)


    def item_summary(self, id: str) -> CatalogSummary:
        """
        Display detailed metadata for a single OceanDataStore Item.

        Searches the current Items list first; if the Item is not found
        there it is fetched directly from the Catalog URL.
        
        * In Jupyter / Marimo environments a styled HTML card is displayed with collapsible
        property and asset sections.
        * In plain Python / CLI environments a formatted text summary is printed instead.

        Parameters
        ----------
        id : str
            Item ID to display metadata for.

        Raises
        ------
        TypeError
            If *id* is not a string.
        ValueError
            If the Item ID is not found in the Catalog.
        """
        if not isinstance(id, str):
            raise TypeError("'id' must be a string.")

        # Collect STAC Item properties metadata:
        item = None
        if self.Items:
            for it in self.Items:
                if it.id == id:
                    item = it
                    break
        if item is None:
            try:
                item = self._open_item(id=id)
            except Exception:
                raise ValueError(f"Item '{id}' not found in Catalog.")

        props    = item.properties
        title    = props.get("title", "")
        desc_raw = props.get("description", "")
        desc     = desc_raw.split("OceanDataCatalog Access")[0].strip() if desc_raw else ""
        platform = props.get("platform", "")
        start    = props.get("start_datetime", "")
        end      = props.get("end_datetime", "")
        bbox     = item.bbox
        bbox_str = (
            f"{bbox[0]:.2f}, {bbox[1]:.2f}, {bbox[2]:.2f}, {bbox[3]:.2f}"
            if bbox else "—"
        )

        # ---- HTML Output (Jupyter) ---- #
        coll_badge = f"<span class='ods-badge-neutral'>{item.collection_id}</span>" if item.collection_id else ""

        core_stats = (
            f"<div class='ods-stats'>"
            f"  <div class='ods-stat'>Platform&nbsp;<span>{platform or '—'}</span></div>"
            f"  <div class='ods-stat'>Start&nbsp;<span>{start or '—'}</span></div>"
            f"  <div class='ods-stat'>End&nbsp;<span>{end or '—'}</span></div>"
            f"  <div class='ods-stat'>BBox&nbsp;<span>({bbox_str})</span></div>"
            f"</div>"
        )

        none_span = "<span class='ods-none'>—</span>"
        if title or desc:
            title_val = title if title else none_span
            desc_val  = desc  if desc  else none_span
            title_row = (
                f"<table class='ods-table' style='margin-bottom:8px'>"
                f"  <thead><tr><th>Title</th><th>Description</th></tr></thead>"
                f"  <tbody><tr><td>{title_val}</td><td>{desc_val.replace('**', '')}</td></tr></tbody>"
                f"</table>"
            )
        else:
            title_row = ""

        # Properties:
        _shown = {"title", "description", "platform", "start_datetime", "end_datetime", "datetime"}
        prop_rows = ""
        for key, val in props.items():
            if key in _shown:
                continue
            if isinstance(val, list):
                items_html = "<br>".join(str(v) for v in val)
                val_cell = (
                    f"<details class='ods-details'>"
                    f"<summary>{len(val)} item{'s' if len(val) != 1 else ''}</summary>"
                    f"<div class='ods-detail-body'>{items_html}</div>"
                    f"</details>"
                )
            elif isinstance(val, dict):
                dict_html = "<br>".join(f"<b>{k}</b>: {v}" for k, v in val.items())
                val_cell = (
                    f"<details class='ods-details'>"
                    f"<summary>{len(val)} field{'s' if len(val) != 1 else ''}</summary>"
                    f"<div class='ods-detail-body'>{dict_html}</div>"
                    f"</details>"
                )
            else:
                val_cell = str(val) if val is not None else none_span
            prop_rows += f"<tr><td class='ods-id'>{key}</td><td>{val_cell}</td></tr>"

        props_section = ""
        if prop_rows:
            props_section = (
                f"<div class='ods-section-title' style='margin-top:10px'>Properties</div>"
                f"<table class='ods-table'>"
                f"  <thead><tr><th>Property</th><th>Value</th></tr></thead>"
                f"  <tbody>{prop_rows}</tbody>"
                f"</table>"
            )

        asset_rows = ""
        for asset_key, asset in item.assets.items():
            af = asset.extra_fields
            media_type = asset.media_type or ""
            endpoint   = af.get("endpoint_url", "")
            bucket     = af.get("bucket", "")
            prefix     = af.get("prefix", "")
            asset_rows += (
                f"<tr>"
                f"<td class='ods-id'>{asset_key}</td>"
                f"<td>{media_type}</td>"
                f"<td>{endpoint}</td>"
                f"<td>{bucket}</td>"
                f"<td class='ods-id'>{prefix}</td>"
                f"</tr>"
            )

        assets_section = ""
        if asset_rows:
            assets_section = (
                f"<div class='ods-section-title' style='margin-top:10px'>Assets</div>"
                f"<table class='ods-table'>"
                f"  <thead><tr>"
                f"    <th>Key</th><th>Media Type</th><th>Endpoint</th><th>Bucket</th><th>Prefix</th>"
                f"  </tr></thead>"
                f"  <tbody>{asset_rows}</tbody>"
                f"</table>"
            )

        access_str = f"catalog.open_dataset(id='{id}')"
        _copy_js = (
            "(function(b){"
            "var t=document.createElement('textarea');"
            "t.value=b.dataset.copy;"
            "document.body.appendChild(t);"
            "t.select();"
            "document.execCommand('copy');"
            "document.body.removeChild(t);"
            "b.textContent='Copied!';"
            "setTimeout(function(){b.textContent='Copy'},1500)"
            "})(this)"
        )
        access_section = (
            f"<div class='ods-section-title' style='margin-top:10px'>Access</div>"
            f"<div class='ods-code'>"
            f"  <code>{access_str}</code>"
            f"  <button class='ods-copy-btn' data-copy=\"{access_str}\" onclick=\"{_copy_js}\">Copy</button>"
            f"</div>"
        )

        html = (
            f"{_NOC_CSS}"
            f"<div class='ods-card'>"
            f"  <div class='ods-header'>"
            f"    {id}"
            f"    {coll_badge}"
            f"  </div>"
            f"  <div class='ods-body'>"
            f"    {core_stats}"
            f"    {title_row}"
            f"    {access_section}"
            f"    {props_section}"
            f"    {assets_section}"
            f"  </div>"
            f"</div>"
        )

        # ---- Plain-Text Output ---- #
        _shown_text = {"title", "description", "platform", "start_datetime", "end_datetime", "datetime"}
        text_lines = [
            f"Item: {id}",
            f"  Title:    {title or '—'}",
            f"  Platform: {platform or '—'}",
            f"  Start:    {start or '—'}",
            f"  End:      {end or '—'}",
            f"  BBox:     {bbox_str}",
            "",
            "  Properties:",
        ]
        for key, val in props.items():
            if key in _shown_text:
                continue
            if isinstance(val, list):
                preview = ", ".join(str(v) for v in val[:5])
                suffix  = ", ..." if len(val) > 5 else ""
                text_lines.append(f"    {key}: [{preview}{suffix}]")
            else:
                text_lines.append(f"    {key}: {val}")
        if item.assets:
            text_lines.append("")
            text_lines.append("  Assets:")
            for asset_key, asset in item.assets.items():
                af  = asset.extra_fields
                loc = f"{af.get('endpoint_url', '')}/{af.get('bucket', '')}/{af.get('prefix', '')}"
                text_lines.append(f"    {asset_key}: {asset.media_type or ''} — {loc}")
        text_lines += ["", f"  Access: {access_str}"]
        text = "\n".join(text_lines)

        return CatalogSummary(display_text=text, display_html=html)


    def _filter_items(self,
                      items: list[pystac.Item],
                      platform: Optional[str] = None,
                      variable_name: Optional[str] = None,
                      standard_name: Optional[str] = None,
                      item_name: Optional[str] = None
                      ):
        """
        Filter Items based on specified platform and variable.

        Parameters
        ----------
        items : list[pystac.Item]
            List of STAC Items to filter.
        platform : str, optional
            Platform name to filter Items by.
        variable_name : str, optional
            Variable name to filter Items by.
        standard_name : str, optional
            Standard variable name to filter Items by.
        item_name : str, optional
            Substring to filter Item IDs by.
        """
        if platform:
            items = [item for item in items if platform in item.properties.get('platform', '')]
        if variable_name:
            items = [item for item in items if any(variable_name in var for var in item.properties.get('variables', []))]
        if standard_name:
            items = [item for item in items if any(standard_name in var for var in item.properties.get('variable_standard_names', []))]
        if item_name:
            items = [item for item in items if item_name in item.id]

        return items


    def search(self,
               collection: Optional[str] = None,
               platform: Optional[str] = None,
               variable_name: Optional[str] = None,
               standard_name: Optional[str] = None,
               item_name: Optional[str] = None
               ) -> None:
        """
        Search the NOC STAC Catalog for Items matching the specified criteria.

        When both a platform and a variable / standard name are provided,
        the search returns all Items which match both criteria.

        Parameters
        ----------
        collection : str, optional
            Collection name to search for. Default is None,
            which searches the entire root Catalog.
        platform : str, optional
            Platform name to search for. Default is None,
            which retrieves Items from all platforms.
        variable_name : str, optional
            Variable name to search for. Default is None,
            which retrieves all Items.
        standard_name : str, optional
            Standard variable name to search for. Default is None,
            which retrieves all Items.
        item_name : str, optional
            Substring to filter Item IDs by. Default is None,
            which retrieves all Items.

        Raises
        ------
        ValueError
            If the specified collection is not found in the Catalog.
        ValueError
            If both variable_name and standard_name are specified.
        TypeError
            If any of the input parameters are of incorrect type.
        """
        if not isinstance(collection, (type(None), str)):
            raise TypeError("'collection' must be a string or None.")
        if not isinstance(platform, (type(None), str)):
            raise TypeError("'platform' must be a string or None.")
        if not isinstance(variable_name, (type(None), str)):
            raise TypeError("'variable_name' must be a string or None.")
        if not isinstance(standard_name, (type(None), str)):
            raise TypeError("'standard_name' must be a string or None.")
        if not isinstance(item_name, (type(None), str)):
            raise TypeError("'item_name' must be a string or None.")

        if collection:
            collections = {col.id: col for col in self.Catalog.get_all_collections()}
            if collection not in collections:
                raise ValueError(f"Collection '{collection}' not found. Available: {list(collections)}")
            self.Collection = self.Catalog.get_child(collection)
            items = list(self.Collection.get_items(recursive=True))
        else:
            scope = self.Collection if self.Collection else self.Catalog
            items = list(scope.get_items(recursive=True))

        if (variable_name is not None) and (standard_name is not None):
            raise ValueError("Only one of 'variable_name' or 'standard_name' can be specified.")
        else:
            self.Items = self._filter_items(items=items,
                                            platform=platform,
                                            variable_name=variable_name,
                                            standard_name=standard_name,
                                            item_name=item_name
                                            )
            return self.summary()


    def _open_item(
            self,
            id: str,
        ) -> pystac.Item:
        """
        Open a STAC Item directly from URL using Item ID.

        Parameters
        ----------
        id : str
            Item ID to open directly from URL.
        
        Returns
        -------
        pystac.Item
            STAC Item object.
        """
        # Define base URL to the root catalog:
        base_url = os.path.dirname(self._stac_url)

        # Construct URL to the Item JSON file:
        # Assumes Item IDs use path-like representation.
        id_list = [f"{id_n}/" for id_n in id.split("/")]
        id_prefix = "".join(id_list[:4])
        item_url = f"{base_url}/{id_prefix}{id}/{id}.json"

        # Open the Item from the constructed URL:
        item = pystac.Item.from_file(item_url)

        return item


    def _open_icechunk_repo(
            self,
            fields: dict,
            ) -> icechunk.Repository:
        """
        Open STAC Item asset as an Icechunk Repository.

        Parameters
        ----------
        fields : dict
            Dictionary of arguments defining Icechunk S3 storage instance.

        Returns
        -------
        icechunk.Repository
            Icechunk Repository object for the Item asset.
        """
        # Define S3 storage configuration:
        storage = icechunk.s3_storage(
            bucket=fields['bucket'],
            prefix=fields['prefix'],
            region="us-east-1",
            anonymous=fields['anonymous'],
            endpoint_url=fields['endpoint_url'],
            force_path_style=True
        )

        # Open Icechunk Repository from S3 storage:
        repo = icechunk.Repository.open(storage=storage)
        return repo


    def _open_icechunk_store(
            self,
            fields: dict,
            branch: str,
            group: str | None = None
            ) -> xr.Dataset:
        """
        Open STAC Item asset Icechunk store as xarray Dataset.

        Parameters
        ----------
        fields : dict
            Dictionary of arguments to s3_storage() defining Icechunk
            S3 storage instance.
        branch : str
            Branch of the Icechunk repository to read.
        group : str, optional
            Group within the Icechunk repository to read. Default is None,
            which reads from the root of the repository.

        Returns
        -------
        xarray.Dataset
            Dataset read from Item asset.
        """
        # Open Zarr store from Icechunk repository:
        repo = self._open_icechunk_repo(fields)
        store = repo.readonly_session(branch=branch).store
        ds = xr.open_zarr(store, consolidated=False, group=group)

        return ds


    def _open_zarr_store(
            self,
            fields: dict,
            consolidated: bool = True,
            group: str | None = None
            ) -> xr.Dataset:
        """
        Open STAC Item Zarr store asset as xarray Dataset.

        Parameters
        ----------
        fields : dict
            Dictionary of arguments to open_zarr() defining URL
            and version of Zarr store.
        consolidated : bool, optional
            Whether to open Zarr store using consolidated metadata capability.
            Default is True, meaning that consolidated metadata is expected.
        group : str, optional
            Group within the Zarr store to read. Default is None,
            which reads from the root of the store.

        Returns
        -------
        xarray.Dataset
            Dataset read from Item asset.
        """
        # Open Item asset Zarr store via URL:
        url = f"{fields['endpoint_url']}/{fields['bucket']}/{fields['prefix']}"
        ds = xr.open_zarr(url, zarr_format=int(fields['zarr_format']), consolidated=consolidated, group=group)

        return ds


    def open_repo(self,
                  id: str,
                  asset_key: Optional[str] = None
                  ) -> icechunk.Repository:
        """
        Open STAC Item asset as an Icechunk Repository.

        Parameters
        ----------
        id : str
            Item ID to open asset.
        asset_key : str, optional
            Key of the asset to open. Default is to infer the key from the Item ID.

        Returns
        -------
        icechunk.Repository
            Icechunk Repository for STAC Item asset.

        Raises
        ------
        ValueError
            If the Item ID or asset key is not found in the catalog.
        ValueError
            If the asset key is not found in the Item ID.
        """
        # -- Validate Inputs -- #
        if not isinstance(id, str):
            raise TypeError("'id' must be a string.")

        # -- Collect Item Asset -- #
        try:
            item = self._open_item(id=id)
        except Exception:
            raise RuntimeError(f"Item ID '{id}' not found in Catalog.")

        # Infer asset key from Item ID if not provided:
        if asset_key is None:
            asset_key = list(item.assets.keys())[0]
        asset = item.assets.get(asset_key)
        if asset is None:
            raise ValueError(f"Asset key '{asset_key}' not found in Item ID '{id}'.")

        fields = asset.extra_fields

        # -- Open Icechunk Repository -- #
        if asset.to_dict()['type'] == "application/vnd.zarr+icechunk":
            required_fields = ['bucket', 'prefix', 'anonymous', 'endpoint_url']
            for field in required_fields:
                if field not in fields:
                    raise ValueError(f"Missing asset field '{field}' in item '{id}'.")
            repo = self._open_icechunk_repo(fields=fields)
        else:
            raise ValueError(f"Item ID '{id}' asset is not an Icechunk repository.")

        return repo


    def open_dataset(self,
                     id: str,
                     group: Optional[str] = None,
                     variable_names: Optional[list[str]] = None,
                     start_datetime: Optional[str] = None,
                     end_datetime: Optional[str] = None,
                     bbox: Optional[tuple[float | int, float | int, float | int, float | int]] = None,
                     branch: str = "main",
                     consolidated: bool = True,
                     asset_key: Optional[str] = None
                    ) -> xr.Dataset:
        """
        Open STAC Item asset as an xarray Dataset.

        Parameters
        ----------
        id : str
            Item ID to open asset.
        group : str, optional
            Group within the Zarr or Icechunk repository to read. Default is None,
            which reads from the root of the repository.
        variable_names : list[str], optional
            List of variable names to be parsed from the dataset.
            Default is to return all variables.
        start_datetime : str, optional
            Start datetime used to subset the dataset. Should be a string
            in ISO format (e.g., "1976-01-01T00:00:00Z"). Default is to use
            the Item start_datetime.
        end_datetime : str, optional
            End datetime used to subset the dataset. Should be a string
            in ISO format (e.g., "2024-12-31T00:00:00Z"). Default is to use
            the Item end_datetime.
        bbox : tuple[float | int, float | int, float | int, float | int], optional
            Spatial bounding box used to subset the dataset. Should be a list of four floats
            representing the bounding box in the format: (min_lon, min_lat, max_lon, max_lat).
            Default is to use the Item bbox.
        branch : str, optional
            Branch of the Icechunk repository to use. Default is to use the "main" branch.
        consolidated : bool, optional
            Whether to open Zarr stores using consolidated metadata. Default is True.
        asset_key : str, optional
            Key of the asset to open. Default is to infer the key from the Item ID.

        Returns
        -------
        xarray.Dataset
            Dataset read from Item asset.

        Raises
        ------
        ValueError
            If the Item ID or asset key is not found in the catalog.
        ValueError
            If the asset key is not found in the Item ID.
        KeyError
            If the specified variable(s) are not found in the dataset.
        """
        # -- Validate Inputs -- #
        if not isinstance(id, str):
            raise TypeError("'id' must be a string.")
        if group is not None and not isinstance(group, str):
            raise TypeError("'group' must be a string or None.")
        if not isinstance(variable_names, (type(None), list)):
            raise TypeError("'variable_names' must be a list of strings.")
        if variable_names is not None and not all([isinstance(var, str) for var in variable_names]):
            raise TypeError("'variable_names' must be a list of strings.")
        if not isinstance(start_datetime, (type(None), str)):
            raise TypeError("'start_datetime' must be a string or None.")
        if not isinstance(end_datetime, (type(None), str)):
            raise TypeError("'end_datetime' must be a string or None.")
        if not isinstance(bbox, (type(None), tuple)):
            raise TypeError("'bbox' must be a tuple or None.")
        if bbox is not None and (len(bbox) != 4 or not all(isinstance(coord, (float, int)) for coord in bbox)):
            raise TypeError("'bbox' must be a tuple of the form (min_lon, min_lat, max_lon, max_lat) with float or int values.")
        if not isinstance(branch, str):
            raise TypeError("'branch' must be a string.")
        if not isinstance(consolidated, bool):
            raise TypeError("'consolidated' must be a boolean.")

        # -- Collect Item Asset -- #
        try:
            item = self._open_item(id=id)
        except Exception:
            raise RuntimeError(f"Item ID '{id}' not found in Catalog.")

        # Infer asset key from Item ID if not provided:
        if asset_key is None:
            asset_key = list(item.assets.keys())[0]
        asset = item.assets.get(asset_key)
        if asset is None:
            raise ValueError(f"Asset key '{asset_key}' not found in Item ID '{id}'.")

        fields = asset.extra_fields

        # Open Icechunk Repository as xarray Dataset:
        if asset.to_dict()['type'] == "application/vnd.zarr+icechunk":
            required_fields = ['bucket', 'prefix', 'anonymous', 'endpoint_url']
            for field in required_fields:
                if field not in fields:
                    raise ValueError(f"Missing asset field '{field}' in item '{id}'.")
            ds = self._open_icechunk_store(fields=fields, branch=branch, group=group)

        # Open Zarr store as xarray Dataset:
        elif asset.to_dict()['type'] == 'application/vnd.zarr':
            required_fields = ['bucket', 'prefix', 'endpoint_url', 'zarr_format']
            for field in required_fields:
                if field not in fields:
                    raise ValueError(f"Missing asset field '{field}' in item '{id}'.")
            ds = self._open_zarr_store(fields=fields, group=group)

        else:
            raise ValueError(f"Unsupported media type {asset.to_dict()['type']} for Item asset.")

        # Selecting variables:
        if variable_names is not None:
            try:
                ds = ds[variable_names]
            except KeyError:
                raise KeyError("One or more variables not found in dataset.")

        # Spatio-temporal subsetting:
        if bbox:
            ds = apply_bbox(ds=ds, bbox=bbox)

        if start_datetime or end_datetime:
            ds = apply_time_bounds(ds=ds, start_datetime=start_datetime, end_datetime=end_datetime)

        return ds
