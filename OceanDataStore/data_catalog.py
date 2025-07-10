"""
data_catalog.py

Description:
This module defines the OceanDataCatalog() class which is a
container for the NOC STAC and a basic API for accessing data
using pystac, Zarr and Icechunk.

Authors:
    - Ollie Tooth
"""
from typing import Optional, Sequence, Tuple

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
                 catalog_name: str = "noc-model-stac",
                 catalog_url: str = None
                 ):
        # Define the URL to the NOC STAC root catalog:
        self._stac_url = catalog_url or f"https://raw.githubusercontent.com/NOC-MSM/OceanDataStore/dev/catalogs/{catalog_name}/catalog.json"
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
        return [item.id for item in self.Items] if self.Items else []


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


    def _filter_items(self, items, platform: Optional[str], variable: Optional[str]):
        """
        Filter Items based on specified platform and variable.
        """
        if platform:
            items = [item for item in items if platform in item.properties.get('platform', '')]
        if variable:
            items = [item for item in items if variable in item.properties.get('variables', [])]
        return items


    def search(self,
               collection: Optional[str] = None,
               variable: Optional[str] = None,
               platform: Optional[str] = None) -> None:
        """
        Search the NOC STAC Catalog for Items matching the specified criteria.

        Parameters
        ----------
        collection : str, optional
            Collection name to search for. Default is None,
            which searches the entire root Catalog.
        variable : str, optional
            Variable name to search for. Default is None,
            which retrieves all Items.
        platform : str, optional
            Platform name to search for. Default is None,
            which retrieves Items from all platforms.
        """
        if collection:
            collections = {col.id: col for col in self.Catalog.get_all_collections()}
            if collection not in collections:
                raise ValueError(f"Collection '{collection}' not found. Available: {list(collections)}")
            self.Collection = self.Catalog.get_child(collection)
            items = list(self.Collection.get_items(recursive=True))
        else:
            scope = self.Collection if self.Collection else self.Catalog
            items = list(scope.get_items(recursive=True))

        self.Items = self._filter_items(items, platform, variable)
        self.item_summary()


    def open_dataset(self,
                     id: str,
                     variables: Optional[Sequence[str]] = None,
                     start_datetime: Optional[str] = None,
                     end_datetime: Optional[str] = None,
                     bbox: Optional[Tuple[float, float, float, float]] = None,
                     branch: str = "main",
                     asset_key: Optional[str] = None) -> xr.Dataset:
        """
        Open a dataset from a STAC Item asset using
        xarray and Icechunk.

        Parameters
        ----------
        id : str
            Item ID to open asset.
        variables : Sequence[str], optional
            Variable or list of variables to be parsed from the dataset.
            All variables are included by default.
        start_datetime : str, optional
            Start datetime used to subset the dataset. Should be a string
            in ISO format (e.g., "1976-01-01T00:00:00Z"). The Item
            start_datetime is used by default.
        end_datetime : str, optional
            End datetime used to subset the dataset. Should be a string
            in ISO format (e.g., "2024-12-31T00:00:00Z"). The Item
            end_datetime is used by default.
        bbox : Tuple[float, float, float, float], optional
            Spatial bounding box used to subset the dataset. Should be a list of four floats
            representing the bounding box in the format: (min_lon, min_lat, max_lon, max_lat).
            The Item bbox is used by default.
        branch : str, optional
            Branch of the Icechunk repository to use. The "main" branch is used by default.
        asset_key : str, optional
            Key of the asset to open. The key is inferred from the Item ID by default.

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
        # Collect Item Asset:
        try:
            item = next(self.Catalog.get_items(id, recursive=True))
        except StopIteration:
            raise ValueError(f"Item ID '{id}' not found in the STAC catalog.")

        asset_key = asset_key or item.id.split('/')[-1]
        asset = item.assets.get(asset_key)
        if asset is None:
            raise ValueError(f"Asset key '{asset_key}' not found in Item ID '{id}'.")

        fields = asset.extra_fields
        required_fields = ['bucket', 'prefix', 'anonymous', 'endpoint_url']
        for field in required_fields:
            if field not in fields:
                raise ValueError(f"Missing asset field '{field}' in item '{id}'.")

        # Define S3 Object Store containing asset:
        storage = icechunk.s3_storage(
            bucket=fields['bucket'],
            prefix=fields['prefix'],
            anonymous=fields['anonymous'],
            endpoint_url=fields['endpoint_url'],
            force_path_style=True
        )

        # Open Icechunk repository & read-only session on specified branch:
        repo = icechunk.Repository.open(storage=storage)
        store = repo.readonly_session(branch=branch).store
        ds = xr.open_zarr(store, consolidated=False)

        # Selecting variables:
        if variables:
            try:
                ds = ds[list(variables)]
            except KeyError:
                raise KeyError(f"Variable(s) {variables} not found in dataset.")

        # Spatio-temporal subsetting:
        if bbox:
            lon = ds.nav_lon.load()
            lat = ds.nav_lat.load()
            ds = ds.where((lon >= bbox[0]) & (lon <= bbox[2]) &
                          (lat >= bbox[1]) & (lat <= bbox[3]), drop=True)

        if start_datetime or end_datetime:
            ds = ds.sel(time_counter=slice(start_datetime, end_datetime))

        return ds
