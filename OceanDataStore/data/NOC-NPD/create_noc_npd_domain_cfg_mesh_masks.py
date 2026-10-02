"""
create_npd_domain_cfg_mesh_masks.py

Description:
Script to create combined domain_cfg & mesh_mask files for
eORCA1, eORCA025 & eORCA12 ERA5v1 NPD configurations.

Created By:
Ollie Tooth (oliver.tooth@noc.ac.uk)
"""
# -- Imports -- #
import numpy as np
import xarray as xr
from nemo_cookbook import NEMODataTree

# ======= eORCA1 ERA5v1 Combined domain_cfg & mesh_mask ======= #
print("In Progress: Creating eORCA1 ERA5v1 combined domain_cfg & mesh_mask file.")
# -- Define domain, mesh_mask and subbasins files -- #
filepath_domain_cfg="/dssgfs01/scratch/npd/simulations/Domains/eORCA1/domain_cfg.nc"
filepath_mesh_mask="/dssgfs01/scratch/npd/simulations/Domains/eORCA1/mesh_mask.nc"
filepath_subbasins="/dssgfs01/scratch/npd/simulations/Domains/eORCA1/subbasins_CMIP6.nc"

ds_domcfg = xr.open_dataset(filepath_domain_cfg).squeeze().drop_vars(['nav_lev', 'nav_lon', 'nav_lat', 'time_counter']).rename({'z': 'nav_lev'})
ds_meshmask = xr.open_dataset(filepath_mesh_mask).squeeze().drop_vars(['time_counter', 'nav_lev', 'nav_lon', 'nav_lat'])
ds_subbasins = xr.open_dataset(filepath_subbasins).squeeze()

# -- Construct NEMODataTree -- #
datasets = {'parent' : {'domain': ds_domcfg}}
nemo = NEMODataTree.from_datasets(datasets=datasets)

# -- Update / Add domain variables -- #
ds_meshmask['tmask'].data = nemo['gridT']['tmask'].drop_vars(['gphit', 'glamt']).rename({'k': 'nav_lev', 'j': 'y', 'i': 'x'}).values
ds_meshmask['umask'].data = nemo['gridU']['umask'].drop_vars(['gphiu', 'glamu']).rename({'k': 'nav_lev', 'j': 'y', 'i': 'x'}).values
ds_meshmask['vmask'].data = nemo['gridV']['vmask'].drop_vars(['gphiv', 'glamv']).rename({'k': 'nav_lev', 'j': 'y', 'i': 'x'}).values
ds_meshmask['fmask'].data = nemo['gridF']['fmask'].drop_vars(['gphif', 'glamf']).rename({'k': 'nav_lev', 'j': 'y', 'i': 'x'}).values
ds_meshmask['wmask'] = nemo['gridW']['wmask'].drop_vars(['gphiw', 'glamw']).rename({'k': 'nav_lev', 'j': 'y', 'i': 'x'}).astype('bool')

ds_meshmask['tmaskutil'].data = ds_meshmask['tmaskutil'].astype('bool').values
ds_meshmask['umaskutil'].data = ds_meshmask['umaskutil'].astype('bool').values
ds_meshmask['vmaskutil'].data = ds_meshmask['vmaskutil'].astype('bool').values
ds_meshmask['fmaskutil'] = ds_meshmask['fmask'].isel(nav_lev=0)
ds_meshmask['wmaskutil'] = ds_meshmask['wmask'].isel(nav_lev=0)

ds_meshmask['bathy_metry'] = ds_domcfg['bathy_metry']
ds_meshmask['top_level'] = ds_domcfg['top_level']
ds_meshmask['bottom_level'] = ds_domcfg['bottom_level']
ds_meshmask['mask_opensea'] = ds_domcfg['mask_opensea']

ds_meshmask['atlmsk'] = ds_subbasins['atlmsk']
ds_meshmask['indmsk'] = ds_subbasins['indmsk']
ds_meshmask['pacmsk'] = ds_subbasins['pacmsk']
ds_meshmask['socmsk'] = ds_subbasins['socmsk']

ds_meshmask = (ds_meshmask
                .assign_coords({'nav_lev': np.arange(ds_meshmask['nav_lev'].size),
                                'y': np.arange(ds_meshmask['y'].size),
                                'x': np.arange(ds_meshmask['x'].size)
                                })
                )

# -- Update encoding & write to .nc file -- #
ds_meshmask.encoding['unlimited_dims'] = None
ds_meshmask.to_netcdf("/dssgfs01/scratch/npd/simulations/Domains/eORCA1/eORCA1_ERA5v1_domain_cfg_mesh_mask.nc")
print("Completed: Created eORCA1 ERA5v1 combined domain_cfg & mesh_mask file.")

# ======= eORCA025 ERA5v1 Combined domain_cfg & mesh_mask ======= #
print("In Progress: Creating eORCA025 ERA5v1 combined domain_cfg & mesh_mask file.")
# -- Define domain, mesh_mask and subbasins files -- #
filepath_domain_cfg="/dssgfs01/scratch/npd/simulations/Domains/eORCA025/domain_cfg.nc"
filepath_mesh_mask="/dssgfs01/scratch/npd/simulations/Domains/eORCA025/mesh_mask.nc"
filepath_subbasins="/dssgfs01/scratch/npd/simulations/Domains/eORCA025/subbasins.nc"

ds_domcfg = xr.open_dataset(filepath_domain_cfg).squeeze().drop_vars(['nav_lev', 'nav_lon', 'nav_lat', 'time_counter']).rename({'z': 'nav_lev'})
ds_meshmask = xr.open_dataset(filepath_mesh_mask).squeeze().drop_vars(['time_counter', 'nav_lev', 'nav_lon', 'nav_lat'])
ds_subbasins = xr.open_dataset(filepath_subbasins).squeeze()

# -- Construct NEMODataTree -- #
datasets = {'parent' : {'domain': ds_domcfg}}
nemo = NEMODataTree.from_datasets(datasets=datasets)

# -- Update / Add domain variables -- #
ds_meshmask['tmask'].data = nemo['gridT']['tmask'].drop_vars(['gphit', 'glamt']).rename({'k': 'nav_lev', 'j': 'y', 'i': 'x'}).values
ds_meshmask['umask'].data = nemo['gridU']['umask'].drop_vars(['gphiu', 'glamu']).rename({'k': 'nav_lev', 'j': 'y', 'i': 'x'}).values
ds_meshmask['vmask'].data = nemo['gridV']['vmask'].drop_vars(['gphiv', 'glamv']).rename({'k': 'nav_lev', 'j': 'y', 'i': 'x'}).values
ds_meshmask['fmask'].data = nemo['gridF']['fmask'].drop_vars(['gphif', 'glamf']).rename({'k': 'nav_lev', 'j': 'y', 'i': 'x'}).values
ds_meshmask['wmask'] = nemo['gridW']['wmask'].drop_vars(['gphiw', 'glamw']).rename({'k': 'nav_lev', 'j': 'y', 'i': 'x'}).astype('bool')

ds_meshmask['tmaskutil'].data = ds_meshmask['tmaskutil'].astype('bool').values
ds_meshmask['umaskutil'].data = ds_meshmask['umaskutil'].astype('bool').values
ds_meshmask['vmaskutil'].data = ds_meshmask['vmaskutil'].astype('bool').values
ds_meshmask['fmaskutil'] = ds_meshmask['fmask'].isel(nav_lev=0)
ds_meshmask['wmaskutil'] = ds_meshmask['wmask'].isel(nav_lev=0)

ds_meshmask['bathy_metry'] = ds_domcfg['e3t_0'].squeeze().sum(dim='nav_lev').where(ds_meshmask['tmaskutil'])
ds_meshmask['top_level'] = ds_domcfg['top_level']
ds_meshmask['bottom_level'] = ds_domcfg['bottom_level']
ds_meshmask['mask_opensea'] = ds_domcfg['mask_opensea']

ds_meshmask['atlmsk'] = ds_subbasins['atlmsk']
ds_meshmask['indmsk'] = ds_subbasins['indmsk']
ds_meshmask['pacmsk'] = ds_subbasins['pacmsk']
ds_meshmask['socmsk'] = ds_subbasins['socmsk']

ds_meshmask = (ds_meshmask
                .drop_vars(['time_counter'])
                .assign_coords({'nav_lev': np.arange(ds_meshmask['nav_lev'].size),
                                'y': np.arange(ds_meshmask['y'].size),
                                'x': np.arange(ds_meshmask['x'].size)
                                })
                )

# -- Update encoding & write to .nc file -- #
ds_meshmask.encoding['unlimited_dims'] = None
ds_meshmask.to_netcdf("/dssgfs01/scratch/npd/simulations/Domains/eORCA025/eORCA025_ERA5v1_domain_cfg_mesh_mask.nc")
print("Completed: Created eORCA025 ERA5v1 combined domain_cfg & mesh_mask file.")


# ======= eORCA12 ERA5v1 Combined domain_cfg & mesh_mask ======= #
print("In Progress: Creating eORCA12 ERA5v1 combined domain_cfg & mesh_mask file.")

# -- Open existing domain_cfg file -- #
ds_domain = xr.open_dataset("/dssgfs01/scratch/npd/simulations/Domains/eORCA12/eORCA12_ERA5v1_domain_cfg_mesh_mask_v0.nc").squeeze()

ds_domain['tmaskutil'] = ds_domain['tmask'].isel(nav_lev=0)
ds_domain['umaskutil'] = ds_domain['umask'].isel(nav_lev=0)
ds_domain['vmaskutil'] = ds_domain['vmask'].isel(nav_lev=0)
ds_domain['fmaskutil'] = ds_domain['fmask'].isel(nav_lev=0)
ds_domain['wmaskutil'] = ds_domain['wmask'].isel(nav_lev=0)

ds_domain = (ds_domain
                .assign_coords({'nav_lev': np.arange(ds_domain['nav_lev'].size),
                                'y': np.arange(ds_domain['y'].size),
                                'x': np.arange(ds_domain['x'].size)
                                })
                )

# -- Update encoding & write to .nc file -- #
ds_domain.encoding['unlimited_dims'] = None
ds_domain.to_netcdf("/dssgfs01/scratch/npd/simulations/Domains/eORCA12/eORCA12_ERA5v1_domain_cfg_mesh_mask.nc")
print("Completed: Created eORCA12 ERA5v1 combined domain_cfg & mesh_mask file.")
