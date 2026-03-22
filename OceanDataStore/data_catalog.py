"""
data_catalog.py

Description:
This module defines the OceanDataCatalog() class which is a
container for the NOC STAC and a basic API for accessing data
using pystac, Zarr and Icechunk.

Authors:
    - Ollie Tooth
"""
from typing import Optional

import os
import pystac
import icechunk
import xarray as xr

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


    def summary(self) -> str:
        """
        Summary description of the root Catalog or a selected Collection.
        """
        return (self.Collection or self.Catalog).describe()


    def item_summary(self) -> None:
        """
        Summary description of the Items returned from the most recent search.
        """
        if not self.Items:
            raise ValueError("No Items returned in most recent query. Use 'search()' to query Catalog.")

        for item in self.Items:
            print(f"""
            * Item ID: {item.id}
              Title: {item.properties.get('title', 'No title available')}
              Description: {item.properties.get('description', 'No description available')}
              Platform: {item.properties.get('platform', 'No platform available')}
              Start Date: {item.properties.get('start_datetime', 'No start date available')}
              End Date: {item.properties.get('end_datetime', 'No end date available')}
            """)


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
            self.item_summary()


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


    def _open_icechunk_store(
            self,
            fields: dict,
            branch: str,
            ) -> xr.Dataset:
        """
        Open STAC Item Icechunk store asset as xarray Dataset.

        Parameters
        ----------
        fields : dict
            Dictionary of arguments to s3_storage() defining Icechunk
            S3 storage instance.
        branch : str
            Branch of the Icechunk repository to read.

        Returns
        -------
        xarray.Dataset
            Dataset read from Item asset.
        """
        # Define S3 Object Store containing asset:
        storage = icechunk.s3_storage(
            bucket=fields['bucket'],
            prefix=fields['prefix'],
            region="us-east-1",
            anonymous=fields['anonymous'],
            endpoint_url=fields['endpoint_url'],
            force_path_style=True
        )

        # Open Item asset Icechunk repository on specified branch:
        repo = icechunk.Repository.open(storage=storage)
        store = repo.readonly_session(branch=branch).store
        ds = xr.open_zarr(store, consolidated=False)

        return ds


    def _open_zarr_store(
            self,
            fields: dict,
            ) -> xr.Dataset:
        """
        Open STAC Item Zarr store asset as xarray Dataset.

        Parameters
        ----------
        fields : dict
            Dictionary of arguments to open_zarr() defining URL
            and version of Zarr store.

        Returns
        -------
        xarray.Dataset
            Dataset read from Item asset.
        """
        # Open Item asset Zarr store via URL:
        url = f"{fields['endpoint_url']}/{fields['bucket']}/{fields['prefix']}"
        ds = xr.open_zarr(url, zarr_format=int(fields['zarr_format']), consolidated=True)

        return ds


    def open_dataset(self,
                     id: str,
                     variable_names: Optional[list[str]] = None,
                     start_datetime: Optional[str] = None,
                     end_datetime: Optional[str] = None,
                     bbox: Optional[tuple[float, float, float, float]] = None,
                     branch: str = "main",
                     asset_key: Optional[str] = None) -> xr.Dataset:
        """
        Open STAC Item asset as an xarray Dataset.

        Parameters
        ----------
        id : str
            Item ID to open asset.
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
        bbox : tuple[float, float, float, float], optional
            Spatial bounding box used to subset the dataset. Should be a list of four floats
            representing the bounding box in the format: (min_lon, min_lat, max_lon, max_lat).
            Default is to use the Item bbox.
        branch : str, optional
            Branch of the Icechunk repository to use. Default is to use the "main" branch.
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
        # -- Validate inputs -- #
        if not isinstance(id, str):
            raise TypeError("'id' must be a string.")
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
        if bbox is not None and (len(bbox) != 4 or not all(isinstance(coord, float) for coord in bbox)):
            raise TypeError("'bbox' must be a tuple of floats in the form (lon_min, lon_max, lat_min, lat_max).")

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
            ds = self._open_icechunk_store(fields=fields, branch=branch)

        # Open Zarr store as xarray Dataset:
        elif asset.to_dict()['type'] == 'application/vnd.zarr':
            required_fields = ['bucket', 'prefix', 'endpoint_url', 'zarr_format']
            for field in required_fields:
                if field not in fields:
                    raise ValueError(f"Missing asset field '{field}' in item '{id}'.")
            ds = self._open_zarr_store(fields=fields)

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
            lon = ds.nav_lon.load()
            lat = ds.nav_lat.load()
            ds = ds.where((lon >= bbox[0]) & (lon <= bbox[2]) &
                          (lat >= bbox[1]) & (lat <= bbox[3]), drop=True)

        if start_datetime or end_datetime:
            ds = ds.sel(time_counter=slice(start_datetime, end_datetime))

        return ds
