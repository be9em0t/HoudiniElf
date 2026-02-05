# download raster map
# at predefined zoom level
# use projection EPSG 3857


# sub_raster_download.py
import os
import requests
import mercantile
import rasterio
from rasterio.merge import merge
from rasterio.io import MemoryFile
from rasterio.transform import from_bounds
from pyproj import Transformer
from qgis.core import QgsProject
from qgis.PyQt.QtWidgets import QInputDialog, QMessageBox, QProgressDialog, QApplication
from qgis.PyQt.QtCore import Qt
from qgis.utils import iface
import time
import imp
import configparser

# read config file
iniFile = os.path.dirname( imp.find_module('b9PyQGIS')[1] ) + "/" + 'b9QGISdata.ini'
config = configparser.ConfigParser()
config.read(iniFile)
rasterZoom = config['common']['raster-zoom']
API_KEY = config['orbis2']['orbis-key']

## write config file
# config['common']['raster-zoom'] = rasterZoomNew
# with open(iniFile, 'w') as configfile:
#     config.write(configfile)

def download_tile(tile, timeout=30, max_retries=3, backoff_factor=1.5):
    """Download a single tile with retries and exponential backoff.

    Returns bytes of the tile PNG on success or raises the last exception on failure.
    """
    url = TILE_SERVER_URL.format(z=tile.z, x=tile.x, y=tile.y, key=API_KEY)
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            if attempt >= max_retries:
                raise
            sleep_time = backoff_factor * (2 ** (attempt - 1))
            print(f"Download attempt {attempt} failed for tile {tile}: {e}; retrying in {sleep_time:.1f}s")
            time.sleep(sleep_time)


# API key (hardcoded as requested)
TILE_SERVER_URL = "https://api.tomtom.com/maps/orbis/map-display/tile/{z}/{x}/{y}.png?apiVersion=1&key={key}"

 


def fGetOrbisRaster(extent_layer):
    """Download Orbis raster tiles for the bounding extent of `extent_layer`.

    extent_layer: a `QgsVectorLayer` providing an extent (in its own CRS).

    Returns the path to the merged GeoTIFF, or None if cancelled/failed.
    """
    # compute WGS84 bounds from the provided layer extent
    from qgis.core import QgsCoordinateTransform, QgsCoordinateReferenceSystem, QgsPointXY

    if extent_layer is None:
        raise ValueError("extent_layer must be a QgsVectorLayer")

    project = QgsProject.instance()
    src_crs = extent_layer.crs()
    dest_crs = QgsCoordinateReferenceSystem("EPSG:4326")
    xform = QgsCoordinateTransform(src_crs, dest_crs, project)
    rect = extent_layer.extent()
    p_min = xform.transform(QgsPointXY(rect.xMinimum(), rect.yMinimum()))
    p_max = xform.transform(QgsPointXY(rect.xMaximum(), rect.yMaximum()))
    west = min(p_min.x(), p_max.x())
    east = max(p_min.x(), p_max.x())
    south = min(p_min.y(), p_max.y())
    north = max(p_min.y(), p_max.y())
    bounds_local = (west, south, east, north)

    # Ask user for zoom level via a dropdown
    parent = iface.mainWindow()
    zoom_options = [str(z) for z in range(0, 23)]
    # use rasterZoom from config as the default index when possible
    try:
        default_index = int(rasterZoom)
    except Exception:
        default_index = 12
    # clamp to allowed zoom range
    if default_index < 0 or default_index > 22:
        default_index = 12
    zoom_str, ok = QInputDialog.getItem(parent, 'Select zoom', 'Zoom level (0-22):', zoom_options, default_index, False)
    if not ok:
        print('User cancelled zoom selection; exiting.')
        return None

    zoom = int(zoom_str)

    # Validate zoom
    if not (0 <= zoom <= 22):
        raise ValueError("zoom must be between 0 and 22")

    # Find tiles intersecting the bounding box
    tiles = list(mercantile.tiles(bounds_local[0], bounds_local[1], bounds_local[2], bounds_local[3], zoom))
    tile_count = len(tiles)

    # Ask for confirmation if more than 4 tiles
    if tile_count > 4:
        resp = QMessageBox.question(parent, 'Confirm download', f'This will download {tile_count} tiles. Continue?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if resp != QMessageBox.Yes:
            print('User declined to download tiles; exiting.')
            return None

    print(f"Selected {tile_count} tiles at zoom level {zoom}.")

    # Save chosen zoom back to config if it changed (blueprint preserved)
    try:
        if str(zoom) != rasterZoom:
            config['common']['raster-zoom'] = str(zoom)
            with open(iniFile, 'w') as configfile:
                config.write(configfile)
            # update module-level rasterZoom so subsequent calls see the change
            try:
                globals()['rasterZoom'] = str(zoom)
            except Exception:
                pass
    except Exception as e:
        print(f"Failed to write zoom to config: {e}")

    # Prepare transformer from WGS84 to Web Mercator
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

    # Download tiles and create rasterio datasets in memory
    datasets = []
    memfiles = []  # keep memoryfiles alive while datasets are in use

    # Progress dialog for QGIS UI so user sees download progress
    progress = QProgressDialog("Downloading tiles...", "Cancel", 0, tile_count, parent)
    progress.setWindowTitle("Downloading tiles")
    progress.setWindowModality(Qt.WindowModal)
    progress.setMinimumDuration(0)
    progress.setValue(0)

    for idx, tile in enumerate(tiles, start=1):
        if progress.wasCanceled():
            print("User cancelled downloads via progress dialog; exiting.")
            break

        try:
            tile_bytes = download_tile(tile)
        except Exception as e:
            print(f"Failed to download tile {tile}: {e}")
            # advance progress and continue
            progress.setValue(idx)
            QApplication.processEvents()
            continue

        # Get tile bounds in lon/lat
        west, south, east, north = mercantile.bounds(tile)
        # Convert to Web Mercator meters
        xmin, ymin = transformer.transform(west, south)
        xmax, ymax = transformer.transform(east, north)

        # Open the PNG bytes to read array and metadata
        in_mem = MemoryFile(tile_bytes)
        with in_mem.open() as src:
            data = src.read()
            height = src.height
            width = src.width
            count = src.count
            dtype = src.dtypes[0]

        # Build GeoTIFF metadata for this tile in EPSG:3857
        meta = {
            "driver": "GTiff",
            "height": height,
            "width": width,
            "count": count,
            "dtype": dtype,
            "crs": "EPSG:3857",
            "transform": from_bounds(xmin, ymin, xmax, ymax, width=width, height=height),
        }

        out_mem = MemoryFile()
        out_ds = out_mem.open(**meta)
        out_ds.write(data)

        # keep references so they don't get GC'd
        memfiles.append(out_mem)
        datasets.append(out_ds)

        # update progress dialog
        progress.setValue(idx)
        QApplication.processEvents()

    if not datasets:
        print("No tiles downloaded; nothing to merge.")
        return None
    else:
        # Merge tiles into a single raster
        mosaic, out_transform = merge(datasets)

        # Determine output directory from QGIS project, fallback to cwd
        project = QgsProject.instance()
        project_file_path = project.fileName()
        if project_file_path:
            directory_path = os.path.dirname(project_file_path)
        else:
            directory_path = os.getcwd()
        output_file = os.path.join(directory_path, f"orbis_zoom{zoom}.tif")

        # Save the merged raster to a GeoTIFF file
        out_meta = datasets[0].meta.copy()
        out_meta.update({
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": out_transform,
            "driver": "GTiff",
            "crs": "EPSG:3857",
        })

        with rasterio.open(output_file, "w", **out_meta) as dest:
            dest.write(mosaic)

        print(f"Merged tiles saved to {output_file}.")

        # Close datasets and memoryfiles
        for ds in datasets:
            try:
                ds.close()
            except Exception:
                pass
        for mf in memfiles:
            try:
                mf.close()
            except Exception:
                pass

        return output_file
