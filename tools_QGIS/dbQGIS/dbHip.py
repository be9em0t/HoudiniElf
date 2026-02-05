

# Utilities, mainly for HIP export

# ToDO:

# append script folder
# from databricks import sql
import os, sys
current_script_dir = os.path.dirname(os.path.abspath(__file__))
# print("Current script's directory:", current_script_dir)
sys.path.append(os.path.dirname(current_script_dir))
import imp


import geopandas as gpd
# from unittest import result
import b9PyQGIS
imp.reload(b9PyQGIS)
from b9PyQGIS import *
from qgis.core import QgsDataSourceUri, QgsVectorLayer, QgsProject, QgsFeature, QgsField, QgsGeometry
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QComboBox, QPushButton, QLabel, QLineEdit
from qgis.PyQt.QtCore import QVariant


import sub_MovePortalTraffic
imp.reload(sub_MovePortalTraffic)
from sub_MovePortalTraffic import *

import sub_AI_Export
imp.reload(sub_AI_Export)
from sub_AI_Export import *

import sub_Add_Centroid
imp.reload(sub_Add_Centroid)
from sub_Add_Centroid import *

import sub_LandmarkXML_to_PointLayer
imp.reload(sub_LandmarkXML_to_PointLayer)
from sub_LandmarkXML_to_PointLayer import *

import sub_OSM_queries
imp.reload(sub_OSM_queries)
from sub_OSM_queries import *

import sub_MNR_SpeedProfiles
imp.reload(sub_MNR_SpeedProfiles)
from sub_MNR_SpeedProfiles import *

import sub_RasterTiles_Orbis
imp.reload(sub_RasterTiles_Orbis)
from sub_RasterTiles_Orbis import *

# from sub_Unique_Fields_Compare import run_dialog
import sub_Unique_Fields_Compare
imp.reload(sub_Unique_Fields_Compare)
from sub_Unique_Fields_Compare import *

# read config file
iniFile = os.path.dirname( imp.find_module('b9PyQGIS')[1] ) + "/" + 'b9QGISdata.ini'
config = configparser.ConfigParser()
config.read(iniFile)
dirCommonGeopack = config['directories']['dirCommonGeopack']

# Get the current project instance
project = QgsProject.instance()
# mainWindow = iface.mainWindow()


def fGetExtentPolygonCoords(extent_layer):
	root = QgsProject.instance().layerTreeRoot()

	# layerGeoInit = iface.activeLayer() # get current layer
	layerGeoInit = extent_layer # get current layer
	layerGeoId = layerGeoInit.id() # get current layer
	layerGeoBaseName = layerGeoInit.name()

	# print('Reproject layer...')
	epsgString = '4326'
	result = b9PyQGIS.fReprojectLayer(layerGeoId, epsgString)
	wgs_Layer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	wgs_Layer.setName(layerGeoBaseName + '_' + epsgString)

	extent = wgs_Layer.extent()  # Get the bounding box of the layer

	xmin = extent.xMinimum()
	xmax = extent.xMaximum()
	ymin = extent.yMinimum()
	ymax = extent.yMaximum()

	# Create the WKT for the bounding box polygon
	wkt_polygon = f"POLYGON(({xmin} {ymin}, {xmin} {ymax}, {xmax} {ymax}, {xmax} {ymin}, {xmin} {ymin}))"
	# print(wkt_polygon)

	QgsProject.instance().removeMapLayer(wgs_Layer)

	# set active layer
	iface.setActiveLayer(layerGeoInit)

	return wkt_polygon


def fSelectExtentLayerOLD(): # get the Extent Layer
	OGRLayers = []
	OGRLayerNames = []
	current_layer = iface.activeLayer()

	for layer in QgsProject.instance().mapLayers().values():
		if layer.providerType()!="wms":
			OGRLayers.append(layer)
			OGRLayerNames.append(layer.name())
	print(OGRLayers)
	print(OGRLayerNames)

	last_extentLayerName = config['mcr']['extent_mcr']
	current_layer = iface.activeLayer()

	if last_extentLayerName in OGRLayerNames:
		layer_index = OGRLayerNames.index(last_extentLayerName)
	else:
		try:
			layerName = current_layer.name()
			layer_index = OGRLayerNames.index(current_layer.name())
		except:
			layer_index = 0

	print({OGRLayers}, {OGRLayerNames}, {layer_index})
	return OGRLayers, OGRLayerNames, layer_index

def fSelectExtentLayer(): # get the Extent Layer
	OGRLayers = []
	OGRLayerNames = []
	current_layer = iface.activeLayer()

	for layer in QgsProject.instance().mapLayers().values():
		if layer.providerType()!="wms":
			OGRLayers.append(layer)

	# Sort the OGRLayers list ignoring capitalization
	OGRLayers.sort(key=lambda layer: layer.name().lower())
	for layer in OGRLayers:
		OGRLayerNames.append(layer.name())

	# print(OGRLayers)
	# print(OGRLayerNames)

	last_extentLayerName = config['mcr']['extent_mcr']
	current_layer = iface.activeLayer()

	if last_extentLayerName in OGRLayerNames:
		layer_index = OGRLayerNames.index(last_extentLayerName)
	else:
		try:
			layerName = current_layer.name()
			layer_index = OGRLayerNames.index(current_layer.name())
		except:
			layer_index = 0

	return OGRLayers, OGRLayerNames, layer_index


def fGetLocationOffsetXY(selected_location):

		# location = config['locations']['selected']
		coords = config['locations'][selected_location].split(",")
		offsetXm = float(coords[0])
		offsetYm = float(coords[1])
		try:
			UTM_zone = str(coords[2])
		except:
			UTM_zone = 'unknown'

		# # ------
		# print ("Selected location name is {}\n".format(selected_location))
		# print ("offsetX = {}\noffsetY = {}\n".format(offsetXm, offsetYm))

		return offsetXm, offsetYm, UTM_zone

def fListPythonModules():
	import pkg_resources

	installed_packages = pkg_resources.working_set
	# print(installed_packages)
	installed_packages_list = sorted(["%s==%s" % (i.key, i.version) for i in installed_packages])
	for package in installed_packages_list:
		print(package)

def fListQGISProcessing():
	from qgis.core import QgsApplication
	for alg in QgsApplication.processingRegistry().algorithms():
		print(f"{alg.id()} — {alg.displayName()}")

def fGetLayerFields():
	global layerGeoId
	global layerGeoBaseName
	layer = iface.activeLayer()
	layerGeoId = layer.id()
	layerGeoBaseName = layer.name()
	print(layerGeoBaseName)

	# Get layer fields (columns)
	listFields = layer.fields().names()
	print (listFields)

	# Put query on the clipboard
	strFields = ', '.join(listFields)
	clipboard = QgsApplication.clipboard()
	clipboard.setText(strFields)

	# message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	# print(message + "\n======= clipboard! =======")
	# qtMsgBox(message)
	return listFields

def fSelectLayerField():
	layer = iface.activeLayer()
	# Get all field names
	field_names = [field.name() for field in layer.fields()]
	print (f"Field names:\n{field_names}")
	
	# Use QInputDialog to create a list box for selection
	selected_field, ok = QInputDialog.getItem(
			None,                              # No parent widget
			"Select Field",                    # Dialog title
			"Choose a field from the layer:",  # Dialog message
			field_names,                       # List of fields to show
			0,                                 # Default index (first item)
			False                              # Don't allow user to edit text
	)

	# Check if the user selected a field
	if ok and selected_field:
			print(f"You selected: {selected_field}")
			# Put query on the clipboard
			clipboard = QgsApplication.clipboard()
			clipboard.setText(selected_field)
			return selected_field

def fGetFieldUniqueVals():
	layer = iface.activeLayer()
	layerName = layer.name()

	selected_field = fSelectLayerField()

	# fields = fieldList[0]
	result = b9PyQGIS.fListUniqueVals(layer,selected_field)
	total_number = result.get("TOTAL_VALUES")
	unique_vals = result.get("UNIQUE_VALUES")
	result_string = f"\nResult for field \"{selected_field}\" of layer \"{layerName}\":\nNumber of variants: {total_number}\nUnique Values:\n{unique_vals}\n"

	print (result_string)

def fKeepUniqueByField():
	#select a field, compare rows and leave only the first one in case of duplicate values
	layer = iface.activeLayer()
	print (layer.name())

	# Load the existing layer by name
	layer_name = layer.name()  # Replace with your layer's name
	layer = QgsProject.instance().mapLayersByName(layer_name)[0]

	# Collect the data into a list of features
	features = [feature for feature in layer.getFeatures()]

	# Convert the features to GeoDataFrame
	# This assumes the layer's CRS is well-known and compatible with GeoPandas
	gdf = gpd.GeoDataFrame.from_features(features)

	# Set the CRS to match the layer’s CRS
	gdf.set_crs(layer.crs().authid(), inplace=True)

	selected_field = fSelectLayerField()

	# Assuming 'gdf' is your GeoDataFrame and 'id' is the column name
	gdf_unique = gdf.drop_duplicates(subset=selected_field, keep='first')

	# print(gdf.head(10))
	# print(gdf.columns)

	# Convert the GeoDataFrame 'gdf_unique' to a new QGIS layer
	new_layer = gdf_to_qgs_layer(gdf_unique, layer_name='No Duplicates')
	# Add the new layer to the QGIS project
	QgsProject.instance().addMapLayer(new_layer)

# Function to convert a GeoDataFrame to a QGIS vector layer
def gdf_to_qgs_layer(gdf, layer_name='New Geopandas Layer'):
		# Determine the geometry type from the GeoDataFrame
		geom_type = gdf.geom_type.iloc[0].lower()
		qgs_geom_type = "Point" if "point" in geom_type else "LineString" if "line" in geom_type else "Polygon"
		
		# Create an empty memory layer
		layer = QgsVectorLayer(f"{qgs_geom_type}?crs={gdf.crs.to_wkt()}", layer_name, "memory")
		provider = layer.dataProvider()
		
		# Add fields to the layer based on GeoDataFrame columns
		fields = []
		for col in gdf.columns:
				if col != 'geometry':
						dtype = QVariant.String if gdf[col].dtype == object else QVariant.Double
						fields.append(QgsField(col, dtype))
		provider.addAttributes(fields)
		layer.updateFields()
		
		# Add features to the layer
		for _, row in gdf.iterrows():
				feature = QgsFeature()
				attrs = [row[col] for col in gdf.columns if col != 'geometry']
				feature.setAttributes(attrs)
				feature.setGeometry(QgsGeometry.fromWkt(row['geometry'].wkt))
				provider.addFeature(feature)


		layer.updateExtents()
		return layer

	# # Read the Shapefile
	# gdf = gpd.read_file('your_shapefile.shp')
	# gdf = gpd.read_file('your_layer.geojson')

	# # Drop duplicate rows based on the 'id' field, keeping only the first occurrence
	# gdf_unique = gdf.drop_duplicates(subset='id', keep='first')

	# # Save the resulting GeoDataFrame to a new Shapefile
	# gdf_unique.to_file('unique_shapefile.shp')

def fDuplicateLayerAsNew():
	original_layer = iface.activeLayer()
	duplicated_layer_name = f"{original_layer.name()}_Copy"
	layer = fDuplicateLayer(original_layer, duplicated_layer_name)

def fDuplicateLayerAsNewInMemory():
	original_layer = iface.activeLayer()
	duplicated_layer_name = f"{original_layer.name()}_Copy"
	layer = fDuplicateLayerinMemory(original_layer, duplicated_layer_name)

def fMarkTempLayers():
	# # Rename layer
	# layer_name = layer.name()
	# new_layer_name = layer_name + "_POSTGRES"
	# layer.setName(new_layer_name)

	# List to store layer paths and provider types
	layers_list = []
	for layer in project.mapLayers().values():
		layer_path = build_layer_path(layer)
		layer_type = layer.providerType()
		# print(f"{layer_type} layer at: {layer_path}")
		layers_list.append((layer_path, layer_type))

	# Sort the list by provider type
	# layers_list.sort(key=lambda x: x[1])
	# layers_list.sort()
	layers_list.sort(key=lambda x: (x[0].lower(), x[1].lower()))

	# Print only the layers with provider types "memory" or "postgres"
	for layer_path, layer_type in layers_list:
		if layer_type in ["memory", "postgres"]:
			print(f"{layer_type} layer at:\n{layer_path}")


# Function to build the path for a layer
def build_layer_path(layer):
	# Find the layer tree node for the layer
	layer_tree_node = project.layerTreeRoot().findLayer(layer.id())

	# Initialize path with the layer's name
	path = [layer.name()]

	# Traverse up the tree to build the full path
	parent = layer_tree_node.parent()
	while parent:
		path.insert(0, parent.name())
		parent = parent.parent()

	return "/".join(path)


def fDropEmptyLayerFields():
	layerGeo = iface.activeLayer() 
	layerGeoId = layerGeo.id() 
	layerGeoBaseName = layerGeo.name()
	listFields = fGetLayerFields()
	listFieldsKeep = ['fid', 'feat_id']
	listFieldsDrop = []

	coffeeMug = """ 
				)  (
			 (   ) )
				) ( (
	 mrf_______)_
	 .-'---------|  
	( C|/\/\/\/\/|
	 '-./\/\/\/\/|
		 '_________'
			'-------'
	"""
	print ("\ninitiate Drop (-:\nMight take some time...\n{}".format(coffeeMug))
		
	for field in listFields:
		if field not in listFieldsKeep:
			values = QgsVectorLayerUtils.getValues(layerGeo, field)[0]
			v = list(filter(None, values))
			count = len(v)
			print("Field {} contains {} values".format(field, count))
			if count == 0:
				listFieldsDrop.append(field)

	if len(listFieldsDrop)==0:
		print("\nAll colums have content\n")
	
	else:
		print(listFieldsDrop)
		# drop unnecessary Vertex fields to save space
		print('Dropping empty fields...')
		# dropFields = ['vertex_index','vertex_part','vertex_part_index','distance','angle','mx','my']
		result = b9PyQGIS.fDropFields(layerGeoId, listFieldsDrop)
		newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
		newLayer.setName(layerGeoBaseName + '_Retain')
		# QgsProject.instance().removeMapLayer(layerGeoId)
		layerGeoId = newLayer.id()

# === HD Map ===
def fGetHDLayer(extent_layer):
	import mercantile
	from vt2geojson.tools import vt_bytes_to_geojson
	import geopandas as gpd
	import requests
	# print("Select layer new variant")

	# Assuming 'config' has already read your .ini file
	# Extract items from the [hdmap] section
	if 'hdmap' in config:
		hdmap_dict = dict(config.items('hdmap'))
		keys = list(hdmap_dict.keys())  # keys to show in the dropdown
	else:
		hdmap_dict = {}
		keys = []

	elem = config['hdmap_options']['selected']
	index = keys.index(elem) if elem in keys else 0
	selected_key, ok = QInputDialog.getItem(mainWindow, "HD layers", "Select HD Layer:", keys, index, False)
	if ok and selected_key:
			HDlayerID = hdmap_dict[selected_key]
			print(f"You selected HD layer: {selected_key} → LayerID: {HDlayerID}")
			config['hdmap_options']['selected'] = selected_key
			# with open(iniFile, 'w') as configfile:
			# 	config.write(configfile)
	else:
		print(f"HD layer selection: Cancelled")
		return "cancel"

	layerGeo = extent_layer
	wkt_polygon = fGetExtentPolygonCoords(layerGeo)
	coordinates_str = wkt_polygon.replace("POLYGON((", "").replace("))", "")
	coordinate_pairs = coordinates_str.split(", ")
	min_list = [float(num) for num in coordinate_pairs[0].split()]
	max_list = [float(num) for num in coordinate_pairs[2].split()]

	zoom = config['hip']['zoom_level']
	text, ok = QInputDialog.getText(None, 'Download Vector Tiles', 'Zoom level:', text=zoom)
	if not ok:
		print('Download cancelled')
		return
	else:
		print(f'You entered: {text}')

		hd_name = selected_key
		serverURL = f"https://hapt-tile.prod.adas.tomtomgroup.com/orbis-layer" #official
		baseURL = f"{serverURL}/{HDlayerID}"

		config['hdmap_options']['zoom_level'] = text
		with open(iniFile, 'w') as configfile:
			config.write(configfile)

		print(f"Base URL: {baseURL}")
		zoom = int(text)
		tiles = list(mercantile.tiles(min_list[0], min_list[1], max_list[0], max_list[1], zoom))

		for index, tile in enumerate(tiles):
			if index == 0:
				url = f"{baseURL}/{tile.z}/{tile.x}/{tile.y}/"
				print(url)
				r = requests.get(url)
				assert r.status_code == 200, r.content
				vt_content = r.content

				features = vt_bytes_to_geojson(vt_content, tile.x, tile.y, tile.z)
				combined_gdf = gpd.GeoDataFrame.from_features(features)

			if index > 0:
				url = f"{baseURL}/{tile.z}/{tile.x}/{tile.y}/"
				print(url)
				r = requests.get(url)
				assert r.status_code == 200, r.content
				vt_content = r.content

				features = vt_bytes_to_geojson(vt_content, tile.x, tile.y, tile.z)
				gdf = gpd.GeoDataFrame.from_features(features)
				combined_gdf = pd.concat([combined_gdf, gdf], ignore_index=True)

		project = QgsProject.instance()
		project_file_path = project.fileName()
		directory_path = os.path.dirname(project_file_path)
		filename = f"{directory_path}/{hd_name}_zoom{zoom}.geojson"
		combined_gdf.to_file(filename, driver='GeoJSON')
	print('Wrote out geojson:\n{}\n== Done =='.format(filename))

	## In the end make sure all stored HD layers match the server
	import requests

	url = 'https://hapt-tile.prod.adas.tomtomgroup.com/orbis-layer'
	headers = {
		'accept': 'application/json'
	}

	response = requests.get(url, headers=headers)

	# Check if the request was successful
	if response.status_code == 200:
		responceHDlayers = response.json()  # Convert the response to JSON
		print(keys)
		values = list(hdmap_dict.values())
		print(values)
		print(hdmap_dict)
		print(responceHDlayers)

		# Convert response values to strings
		responceHDlayers_str = [str(v) for v in responceHDlayers]

		all_ini_match = all(value in responceHDlayers_str for value in hdmap_dict.values())
		print("All stored values match server:", all_ini_match)

		if all_ini_match==False:
			mismatches = {k: v for k, v in hdmap_dict.items() if v not in responceHDlayers_str}
			print("Mismatches:", mismatches)

		# Convert ini values to strings
		hdmap_dict_values = [str(v) for v in hdmap_dict.values()]

		# Check if all valid_values are present in the dict
		all_server_present = all(v in hdmap_dict_values for v in responceHDlayers_str)
		print("All server values are stored in the .ini:", all_server_present)

		if all_server_present==False:
			# Find any extras in valid_values that aren't in the dict
			extra_values = [v for v in responceHDlayers_str if v not in hdmap_dict_values]
			print("Valid values missing from dict:", extra_values)

	else:
		print(f"Request failed with status code: {response.status_code}")

# === HD Map end , Hillshade start ===

def fGetHillshade(extent_layer, selected_location):
	from PIL import Image
	import mercantile
	from mercantile import bounds
	import requests

	layerGeo = extent_layer
	wkt_polygon = fGetExtentPolygonCoords(layerGeo)
	# print(wkt_polygon)
	
	coordinates_str = wkt_polygon.replace("POLYGON((", "").replace("))", "")
	coordinate_pairs = coordinates_str.split(", ")
	min_list = [float(num) for num in coordinate_pairs[0].split()]
	max_list = [float(num) for num in coordinate_pairs[2].split()]
	# print("layerGeo {} has extent min: {} \nmax: {}".format(layerGeo.name(), min_list, max_list))

	zoom = config['hip']['zoom_level_hillshade']
	text, ok = QInputDialog.getText(None, 'Download Hillshade Tiles', 'Zoom level (0-13):', text=zoom)
	if not ok:
		print('Download cancelled')
		return
	else:
		# print(f'You entered: {text}')

		config['hip']['zoom_level_hillshade'] = text
		with open(iniFile, 'w') as configfile:
			config.write(configfile)

		serverURL = 'https://api.tomtom.com/map/1/tile/hill/main' 
		api_key = config['hip']['api_key_hip']


		zoom = int(text)
		tiles = list(mercantile.tiles(min_list[0], min_list[1], max_list[0], max_list[1], zoom))
		# print (f"Tiles: {tiles}")

		project = QgsProject.instance()
		project_file_path = project.fileName()
		directory_path = os.path.dirname(project_file_path)
		base_filename = f"{directory_path}/{layerGeo.name()}_hillshade.png"

		# Initialize variables for the bounding box
		min_lon, min_lat = float('inf'), float('inf')
		max_lon, max_lat = float('-inf'), float('-inf')

		# Download tiles and open them as images
		tile_images = []
		for tile in tiles:
			url = f"{serverURL}/{tile.z}/{tile.x}/{tile.y}.png?key={api_key}"
			response = requests.get(url)
			response.raise_for_status()
			
			# Save tile image to memory
			img = Image.open(requests.get(url, stream=True).raw)
			tile_images.append((tile, img))

			bbox = bounds(tile)  # Get the bounding box for each tile
			min_lon = min(min_lon, bbox.west)
			min_lat = min(min_lat, bbox.south)
			max_lon = max(max_lon, bbox.east)
			max_lat = max(max_lat, bbox.north)

		# # Print the bounding rectangle
		# print(f"Bounding Rectangle (Lon/Lat):")
		# print(f"  Min Lon: {min_lon}, Min Lat: {min_lat}")
		# print(f"  Max Lon: {max_lon}, Max Lat: {max_lat}")

		# Define the polygon as a WKT string based on the bounding rectangle
		tiles_polygon_wkt = f"POLYGON(({min_lon} {min_lat}, {min_lon} {max_lat}, {max_lon} {max_lat}, {max_lon} {min_lat}, {min_lon} {min_lat}))"

		# Create a vector layer
		layername = f"{layerGeo.name()}_Hillshade_Bounding_Rectangle"
		polygon_layer = QgsVectorLayer('Polygon?crs=EPSG:4326', layername, 'memory')
		provider = polygon_layer.dataProvider()

		# Add fields to the layer
		provider.addAttributes([QgsField('id', QVariant.Int)])
		polygon_layer.updateFields()

		# Create a feature with the bounding polygon
		feature = QgsFeature()
		feature.setGeometry(QgsGeometry.fromWkt(tiles_polygon_wkt))
		feature.setAttributes([1])  # Set 'id' to 1
		provider.addFeature(feature)
		polygon_layer.updateExtents()

		# Add the layer to the QGIS project
		QgsProject.instance().addMapLayer(polygon_layer)
		print("Bounding Rectangle Polygon Layer added to QGIS.")

		# Determine the final stitched image dimensions
		tile_size = 514  # Tile size (514x514 pixels)
		overlap = 1      # 1-pixel overlap
		min_x = min(tile.x for tile, _ in tile_images)
		max_x = max(tile.x for tile, _ in tile_images)
		min_y = min(tile.y for tile, _ in tile_images)
		max_y = max(tile.y for tile, _ in tile_images)

		width = ((max_x - min_x + 1) * (tile_size - overlap))
		height = ((max_y - min_y + 1) * (tile_size - overlap))

		# Create a blank image to stitch the tiles
		stitched_image = Image.new("RGBA", (width, height))

		# for tile, img in tile_images:
		for index, (tile, img) in enumerate(tile_images):
			# if index == 0:
				x_offset = (tile.x - min_x) * (tile_size - overlap)
				y_offset = (tile.y - min_y) * (tile_size - overlap)
				stitched_image.paste(img, (x_offset, y_offset))

		# Save the final stitched image
		stitched_image.save(base_filename)
		print(f"Stitched image saved as {base_filename}")

		fExportPolygons2Hip(selected_location)

# === end hillshade ===

def fOverture(extent_layer):
	layerGeo = extent_layer
	wkt_polygon = fGetExtentPolygonCoords(layerGeo)
	coordinates_str = wkt_polygon.replace("POLYGON((", "").replace("))", "")
	coordinate_pairs = coordinates_str.split(", ")
	coordinate_minmax = coordinate_pairs[0] + "    " + coordinate_pairs[2]
	coordinate_minmax = coordinate_minmax.strip()
	coordinate_bbox = re.sub(r'\s+', ',', coordinate_minmax)

	# Input item from drop down list
	options=["address","bathymetry","building","building_part","division","division_area","division_boundary","place","segment","connector","infrastructure","land","land_cover","land_use","water"] #alternatively, vlayer.dataProvider().fields().names()
	type, ok = QInputDialog.getItem(parent, "Select:", "Geometry types", options, 2, False)
	outfile = f"overture_{type}"
	overtureCommand = f"""overturemaps download --bbox={coordinate_bbox} -f geojson --type={type} --output={outfile}.geojson"""

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(overtureCommand)

	message = """The query is on the clipboard.
Paste and run it in Terminal.
Then import the JSON as a vector layer to QGIS.
You need Overture Command Prompt Tool
(https://docs.overturemaps.org/getting-data/overturemaps-py/)"""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fSeparateOceanWater():
	layer = iface.activeLayer()
	layer_type = b9PyQGIS.fGetVectorLayerType(layer)
	# print(layer_type)
	if layer_type == 'polygon':
		strExpression = ' "maritime_water" = true '
		result = b9PyQGIS.fExtractByExpression(layer, strExpression)
		# result = b9PyQGIS.fExtractVerts(layerGeo.id())
		newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
		newLayer.setName(layerGeoBaseName + '_WaterMaritime')

		strExpression = ' "land_mass" = true '
		result = b9PyQGIS.fExtractByExpression(layer, strExpression)
		# result = b9PyQGIS.fExtractVerts(layerGeo.id())
		newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
		newLayer.setName(layerGeoBaseName + '_Landmass')

		strExpression = ' "geometry_type" is not null '
		result = b9PyQGIS.fExtractByExpression(layer, strExpression)
		# result = b9PyQGIS.fExtractVerts(layerGeo.id())
		newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
		newLayer.setName(layerGeoBaseName + '_GeometryInWater')

		# QgsProject.instance().removeMapLayer(layerGeo.id())
		# layerGeo = newLayer

def fHoleRings():
	layer = iface.activeLayer()
	layerGeoBaseName = layer.name()
	layer_type = b9PyQGIS.fGetVectorLayerType(layer)
	# print(layer_type)
	if layer_type == 'polygon':
		strFieldName = 'HoleRings'
		strFormula = ' num_interior_rings(  $geometry )'
		iFieldType = 1
		iFieldLength = 0
		iFieldPrecision = 0
		result = b9PyQGIS.fFieldCalc(layer, strFieldName, strFormula, iFieldType, iFieldLength, iFieldPrecision)
		# result = b9PyQGIS.fExtractVerts(layerGeo.id())
		newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
		newLayer.setName(layerGeoBaseName + '_HoleRings')
		# QgsProject.instance().removeMapLayer(layerGeo.id())
		# layerGeo = newLayer
		return newLayer

def fCurvatureOrbisAvg():
	layer = iface.activeLayer()
	layerGeoBaseName = layer.name()
	layer_type = b9PyQGIS.fGetVectorLayerType(layer)
	# print(layer_type)
	if layer_type == 'line':
		strFieldName = 'CurvatureAvg'
		strFormula = 'array_sum(\narray_foreach(\n\tstring_to_array( "curvature_linear" , \';\'),\n\t\tto_int(\n\t\t\tsubstr(@element, strpos(@element, \'#\') + 1)\n\t\t)\n\t)\n)/array_length(\n\tarray_foreach(\n\t\tstring_to_array( "curvature_linear" , \';\'),\n\t\tto_int(\n\t\t\tsubstr(@element, strpos(@element, \'#\') + 1)\n\t\t)\n\t)\n)\n'
		iFieldType = 0
		iFieldLength = 0
		iFieldPrecision = 2
		result = b9PyQGIS.fFieldCalc(layer, strFieldName, strFormula, iFieldType, iFieldLength, iFieldPrecision)
		# result = b9PyQGIS.fExtractVerts(layerGeo.id())
		newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
		newLayer.setName(layerGeoBaseName + '_CurvatureAvg')
		# QgsProject.instance().removeMapLayer(layerGeo.id())
		# layerGeo = newLayer

def fGradientOrbisAvg():
	layer = iface.activeLayer()
	layerGeoBaseName = layer.name()
	layer_type = b9PyQGIS.fGetVectorLayerType(layer)
	# print(layer_type)
	if layer_type == 'line':
		strFieldName = 'GradientAvg'
		strFormula = 'array_sum(\n array_foreach(\n array_filter(\n string_to_array( "gradient_linear" , \';\'),\n strpos(@element, \'#\') >= 0 -- Ensure `#` exists\n ),\n if( @element IS NOT NULL AND strpos(@element, \'#\') >= 0 AND regexp_match(@element, \'#-?[0-9]+$\'),\n coalesce(to_int(substr(@element, strpos(@element, \'#\') + 1)), substr(@element, strpos(@element, \'#\') + 1)),\n 0\n )\n )\n) / array_length(\n array_foreach(\n array_filter(\n string_to_array( "gradient_linear" , \';\'),\n strpos(@element, \'#\') >= 0 -- Ensure `#` exists\n ),\n if( @element IS NOT NULL AND strpos(@element, \'#\') >= 0 AND regexp_match(@element, \'#-?[0-9]+$\'),\n coalesce(to_int(substr(@element, strpos(@element, \'#\') + 1)), substr(@element, strpos(@element, \'#\') + 1)),\n 0\n )\n )\n)\n'
		iFieldType = 0
		iFieldLength = 0
		iFieldPrecision = 2
		result = b9PyQGIS.fFieldCalc(layer, strFieldName, strFormula, iFieldType, iFieldLength, iFieldPrecision)
		# result = b9PyQGIS.fExtractVerts(layerGeo.id())
		newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
		newLayer.setName(layerGeoBaseName + '_GradientAvg')
		# QgsProject.instance().removeMapLayer(layerGeo.id())
		# layerGeo = newLayer


def fBuildingOverlapParts():
	layer = iface.activeLayer()
	layerGeoBaseName = layer.name()
	layer_type = b9PyQGIS.fGetVectorLayerType(layer)

	source = layer.source()
	provider = layer.dataProvider().name()

	if ".gpkg" in source and provider == "ogr":
			print("The layer source is a GeoPackage!")
	else:
			print("Save the buildings layer as geopackage,\notherwise you'll die of old age waiting.")
			return

	if layer_type == 'polygon':
		strExpression = ' "part" = true'
		result = b9PyQGIS.fExtractByExpression(layer, strExpression)
		partsLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
		partsLayer.setName(layerGeoBaseName + '_temp_BuildingParts')

		predicate = [1,3,5]
		result = b9PyQGIS.fSelectByLocation(layer, partsLayer, predicate)

		# Invert the selection
		layer.invertSelection()

		result = b9PyQGIS.fExtractSelectedFeatures(layer)
		footprintsLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
		footprintsLayer.setName(layerGeoBaseName + '_temp_BuildingFootprints')

		layers = [footprintsLayer, partsLayer]
		result = b9PyQGIS.fMergeLayers(layers)
		mergedLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
		mergedLayer.setName(layerGeoBaseName + '_BuildingsWithParts')

		QgsProject.instance().removeMapLayer(footprintsLayer.id())
		QgsProject.instance().removeMapLayer(partsLayer.id())


def fAddLatLonFields():
	layer = iface.activeLayer()
	layer_type = b9PyQGIS.fGetVectorLayerType(layer)
	if layer_type == 'point':
		# Calculate LatLon field
		layerGeo = layer
		print('Calculating LatLon field...')
		strFieldName = 'LatLon'
		strFormula = "concat(y(geom_from_wkt(geom_to_wkt( $geometry, precision:=4))), ', ' ,x(geom_from_wkt(geom_to_wkt( $geometry, precision:=4))))"
		iFieldType = 2
		iFieldLength = 0
		iFieldPrecision = 0
		result = b9PyQGIS.fFieldCalc(layerGeo.id(), strFieldName, strFormula, iFieldType, iFieldLength, iFieldPrecision)
		newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
		newLayer.setName(layer.name() + '_LatLon')
		# QgsProject.instance().removeMapLayer(layerGeo.id())
		layerGeo = newLayer
		# Calculate LonLat field
		print('Calculating LonLat field...')
		strFieldName = 'LonLat'
		strFormula = "concat(x(geom_from_wkt(geom_to_wkt( $geometry, precision:=4))), ', ' ,y(geom_from_wkt(geom_to_wkt( $geometry, precision:=4))))"
		iFieldType = 2
		iFieldLength = 0
		iFieldPrecision = 0
		result = b9PyQGIS.fFieldCalc(layerGeo.id(), strFieldName, strFormula, iFieldType, iFieldLength, iFieldPrecision)
		newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
		newLayer.setName(layer.name() + '_LatLon')
		QgsProject.instance().removeMapLayer(layerGeo.id())
		layerGeo = newLayer
	else:
		qtMsgBox("Please select a point layer")


def fExportPoints2Hip(selected_location):
	offsetXm, offsetYm, UTM_zone = fGetLocationOffsetXY(selected_location)

	layerGeo = iface.activeLayer() # this is to allow only export
	layerGeoBaseName = iface.activeLayer().name()

	# convert to single parts just in case
	print('Convert to Single parts...')
	result = fMultiToSingleParts(layerGeo.id())
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_SingleParts')
	# QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer

	# add XY position in meters
	print('Adding XY position in meters...')
	result = fAddXYmeters(layerGeo.id())
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_AddXYmeters')
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer

	# add XY offset
	print('Adding XY offset...')
	result = fExpXYcoordOffset(layerGeo.id(), offsetXm, offsetYm)
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = result['OUTPUT']

	# drop unnecessary Vertex fields to save space
	print('Dropping unnecessary vertex fields...')
	dropFields = ['vertex_index','vertex_part','vertex_part_index','distance','angle','mx','my']
	result = b9PyQGIS.fDropFields(layerGeo.id(), dropFields)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_Hip')
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer


def fExportPolygons2Hip(selected_location):
	offsetXm, offsetYm, UTM_zone = fGetLocationOffsetXY(selected_location)
	layerGeo = iface.activeLayer()
	layerGeoBaseName = iface.activeLayer().name()

	# Force Right hand
	print ("Force Right Hand Rule...")
	result = b9PyQGIS.fForceRightHand(layerGeo.id())
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_RHR')
	# QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer

	try:
		# Deal with Holes
		# convert to Linestrings
		# type 0 - centroids, type 1 - nodes, type 2 - linestrings, type 3 - multilinestrings, type 4 - polygons
		print ("Converting to linestrings...")
		result = b9PyQGIS.fConvert(layerGeo.id(), 2)
		newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
		newLayer.setName(layerGeoBaseName + '_LineStrings')
		QgsProject.instance().removeMapLayer(layerGeo.id())
		layerGeo = newLayer
	except:
		print ("Fix Geometries...")
		result = b9PyQGIS.fFixGeometries(layerGeo.id())
		newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
		newLayer.setName(layerGeoBaseName + '_FixGeom')
		QgsProject.instance().removeMapLayer(layerGeo.id())
		layerGeo = newLayer
		print ("Converting to linestrings...")
		result = b9PyQGIS.fConvert(layerGeo.id(), 2)
		newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
		newLayer.setName(layerGeoBaseName + '_LineStrings')
		QgsProject.instance().removeMapLayer(layerGeo.id())
		layerGeo = newLayer

	# Convert back to Polygons
	# type 0 - centroids, type 1 - nodes, type 2 - linestrings, type 3 - multilinestrings, type 4 - polygons
	print ("Converting to polygons...")
	result = b9PyQGIS.fConvert(layerGeo.id(), 4)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_Polygons')
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer

	# Convert Polygons Multilines to SingleLines
	print('Polygons Multi to Single...')
	result = b9PyQGIS.fMultiToSingleParts(layerGeo.id())
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_SinglePolygons')
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer

	# add polyID to exploded lines
	print('Adding polyID to single polygons...')
	result = b9PyQGIS.fAddRowID(layerGeo.id(),'polyID', '@row_number', 1, 10, 3)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_Indexed')
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer

	# Convert Polygons to Lines
	print('Polygons to lines...')
	result = b9PyQGIS.fPolygons2Lines(layerGeo.id())
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_Poly2Lines')
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer

	# extract vertices
	print('Extracting vertices...')
	result = b9PyQGIS.fExtractVerts(layerGeo.id())
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_VerticesOrg')
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer


	# add XY position in meters
	print('Adding XY position in meters...')
	result = fAddXYmeters(layerGeo.id())
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_AddXYmeters')
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer

	# add XY offset
	print('Adding XY offset...')
	result = fExpXYcoordOffset(layerGeo.id(), offsetXm, offsetYm)
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = result['OUTPUT']

	# drop unnecessary Vertex fields to save space
	print('Dropping unnecessary vertex fields...')
	dropFields = ['vertex_index','vertex_part','vertex_part_index','distance','angle','mx','my']
	# dropFields = ['vertex_part','vertex_index','vertex_part_index','distance','angle','mx','my','layer','path','rowID']
	result = b9PyQGIS.fDropFields(layerGeo.id(), dropFields)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_Hip')
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer

def fExportPolygonsWithHoles2Hip(selected_location):
	# newLayer = 
	fHoleRings()
	fExportPolygons2Hip(selected_location)


def fExportLines2Hip(selected_location):
	offsetXm, offsetYm, UTM_zone = fGetLocationOffsetXY(selected_location)
	layerGeo = iface.activeLayer() # this is to allow only export
	layerGeoBaseName = iface.activeLayer().name()

	# --- line ---

	# add polyID to exploded lines
	print('Adding lineId to polylines...')
	result = b9PyQGIS.fAddRowID(layerGeo.id(),'plineID', '@row_number', 1, 10, 3)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_Indexed')
	# QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer

	# Explode lines
	print('Exploding lines...')
	result = b9PyQGIS.fExplodeLines(layerGeo.id())
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_Poly2Lines_Explode')
	QgsProject.instance().removeMapLayer(layerGeo)
	layerGeo = newLayer

	# add polyID to exploded lines
	print('Adding polyId to exploded lines...')
	result = b9PyQGIS.fAddRowID(layerGeo.id(),'polyID', '@row_number', 1, 10, 3)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_Indexed')
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer

	# extract vertices
	print('Extracting vertices...')
	result = b9PyQGIS.fExtractVerts(layerGeo.id())
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_VerticesOrg')
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer

	# add XY position in meters
	print('Adding XY position in meters...')
	result = fAddXYmeters(layerGeo.id())
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_AddXYmeters')
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer

	# add XY offset
	print('Adding XY offset...')
	result = fExpXYcoordOffset(layerGeo.id(), offsetXm, offsetYm)
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = result['OUTPUT']
	
	# drop unnecessary Vertex fields to save space
	print('Dropping unnecessary vertex fields...')
	dropFields = ['vertex_index','vertex_part','vertex_part_index','distance','angle','mx','my']
	result = b9PyQGIS.fDropFields(layerGeo.id(), dropFields)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_Hip')
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer


def fExportNetworkZ2Hip(selected_location):
	offsetXm, offsetYm, UTM_zone = fGetLocationOffsetXY(selected_location)
	layerGeo = iface.activeLayer() # this is to allow only export
	layerGeoBaseName = iface.activeLayer().name()

	# Calculate NumPoints for each multiline
	print('Calculating NumPoints...')
	strFieldName = 'NumPoints'
	strFormula = ' num_points( $geometry)\r\n'
	iFieldType = 1
	iFieldLength = 0
	iFieldPrecision = 0
	result = b9PyQGIS.fFieldCalc(layerGeo.id(), strFieldName, strFormula, iFieldType, iFieldLength, iFieldPrecision)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_NumPoints')
	# QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeo = newLayer

	# add polyID to exploded lines
	print('Adding polyID to exploded lines...')
	result = b9PyQGIS.fAddRowID(layerGeo.id(),'polyID', '@row_number', 1, 10, 3)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_Indexed')
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer
	
	# extract vertices
	print('Extracting vertices...')
	result = b9PyQGIS.fExtractVerts(layerGeo.id())
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_VerticesOrg')
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer

	# add XY position in meters
	print('Adding XY position in meters...')
	result = fAddXYmeters(layerGeo.id())
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_AddXYmeters')
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer

	# add XY offset
	print('Adding XY offset...')
	result = fExpXYcoordOffset(layerGeo.id(), offsetXm, offsetYm)
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = result['OUTPUT']
	
	# drop unnecessary Vertex fields to save space
	print('Dropping unnecessary vertex fields...')
	# dropFields = ['fid', 'feat_id', 'ada_compliant', 'feat_type', 
	# 'netw_geo_id', 'junction_id_from', 'junction_id_to', 
	# 'from_feat_type', 'from_jt_regular', 'from_jt_bifurcation', 'from_jt_railway_crossing', 
	# 'to_feat_type', 'to_jt_regular', 'to_jt_bifurcation', 'to_jt_railway_crossing', 
	# 'vertex_part','vertex_part_index','distance','angle','mx','my'] # 'vertex_index'
	dropFields = [ 'vertex_part','vertex_part_index','distance','angle','mx','my']
	results = b9PyQGIS.fDropFields(layerGeo.id(), dropFields)
	newLayer = QgsProject.instance().addMapLayer(results['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_Hip')
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer


def fHIP_Dialog(export_list, process_list, utility_list, centroidLocations, OGRLayerNames, OGRLayers):

	class MultiInputDialog(QDialog):
		def __init__(self, parent=None):
			super(MultiInputDialog, self).__init__(parent)

			self.updating = True  # Flag to prevent recursive updates
			choiceSelectedProcess = ''

			# Initialize the dropdown list and text input box
			self.dropdown1 = QComboBox(self) # export hip
			self.dropdown2 = QComboBox(self) # process
			self.dropdown3 = QComboBox(self) # utility
			self.dropdown4 = QComboBox(self) # location
			self.dropdown5 = QComboBox(self) # extent

			# Initialize labels
			label1 = QLabel("Export:")
			label2 = QLabel("Sources:")
			label3 = QLabel("Utility:")
			label4 = QLabel("\nCentroid location:")
			label5 = QLabel("Extent layer:")
			self.label6 = QLabel("\nNo selection to execute\n", self)

			# Initialize OK and Cancel buttons
			ok_button = QPushButton("OK", self)
			cancel_button = QPushButton("Cancel", self)
			
			# Connect buttons to actions
			ok_button.clicked.connect(self.accept)
			cancel_button.clicked.connect(self.reject)


			# Create layout
			layout = QVBoxLayout(self)
			layout.addWidget(label1)
			layout.addWidget(self.dropdown1)
			layout.addWidget(label2)
			layout.addWidget(self.dropdown2)
			layout.addWidget(label3)
			layout.addWidget(self.dropdown3)
			layout.addWidget(label4)
			layout.addWidget(self.dropdown4)
			layout.addWidget(label5)
			layout.addWidget(self.dropdown5)
			layout.addWidget(self.label6)
			layout.addWidget(ok_button)
			layout.addWidget(cancel_button)
			
			# Populate the dropdown list
			self.dropdown1.addItems(export_list)
			self.dropdown2.addItems(process_list)
			self.dropdown3.addItems(utility_list)
			self.dropdown4.addItems(centroidLocations)
			self.dropdown5.addItems(OGRLayerNames)
			
			self.dropdown1.currentIndexChanged.connect(self.refresh_dialog1)
			self.dropdown2.currentIndexChanged.connect(self.refresh_dialog2)
			self.dropdown3.currentIndexChanged.connect(self.refresh_dialog3)

			# Set default value for the dropdown
			lastExport = config['hip']['last_export']
			if lastExport in export_list:
					default_index = export_list.index(lastExport)
					self.dropdown1.setCurrentIndex(default_index)
			lastProcess = config['hip']['last_process']
			if lastProcess in process_list:
					default_index = process_list.index(lastProcess)
					self.dropdown2.setCurrentIndex(default_index)
			lastUtility = config['hip']['last_utility']
			if lastUtility in utility_list:
					default_index = utility_list.index(lastUtility)
					self.dropdown3.setCurrentIndex(default_index)
			lastLocation = config['hip']['last_location']
			if lastLocation in centroidLocations:
					default_index = centroidLocations.index(lastLocation)
					self.dropdown4.setCurrentIndex(default_index)
			lastExtent = config['hip']['last_extent']
			if lastExtent in OGRLayerNames:
					default_index = OGRLayerNames.index(lastExtent)
					self.dropdown5.setCurrentIndex(default_index)

		def refresh_dialog1(self):
			if self.updating==True:
				selected_option = self.dropdown1.currentText()
				self.choiceSelectedProcess = selected_option
				self.label6.setText(f"\nExecute: {selected_option}\n")
				self.updating = False
				self.dropdown2.setCurrentIndex(0)
				self.dropdown3.setCurrentIndex(0)
				self.updating = True
			else:
				return

		def refresh_dialog2(self):
			if self.updating==True:
				selected_option = self.dropdown2.currentText()
				self.choiceSelectedProcess = selected_option
				self.label6.setText(f"\nExecute: {selected_option}\n")
				self.updating = False
				self.dropdown1.setCurrentIndex(0)
				self.dropdown3.setCurrentIndex(0)
				self.updating = True
			else:
				return


		def refresh_dialog3(self):
			if self.updating==True:
				selected_option = self.dropdown3.currentText()
				self.choiceSelectedProcess = selected_option
				self.label6.setText(f"\nExecute: {selected_option}\n")
				self.updating = False
				self.dropdown1.setCurrentIndex(0)
				self.dropdown2.setCurrentIndex(0)
				self.updating = True
			else:
				return
	
		def get_selection(self):
			# Get the selected item from the dropdown list and text from QLineEdit
			choiceExport = self.dropdown1.currentText()
			choiceProcess = self.dropdown2.currentText()
			choiceUtility = self.dropdown3.currentText()
			choiceLocation = self.dropdown4.currentText()
			choiceExtentLayerName = self.dropdown5.currentText()
			# choiceSelectedProcess = self.label6.text()
			choiceExtentLayerNameIndex = self.dropdown5.currentIndex()
			choiceExtentLayer = OGRLayers[choiceExtentLayerNameIndex]
			return choiceExport, choiceProcess, choiceUtility, self.choiceSelectedProcess, choiceLocation, choiceExtentLayerName, choiceExtentLayer

	# display dialog:
	dialog = MultiInputDialog()
	result = dialog.exec_()

	# write config
	if result == QDialog.Accepted:
			choiceExport, choiceProcess, choiceUtility, choiceSelectedProcess, choiceLocation, choiceExtentLayerName, choiceExtentLayer = dialog.get_selection()
			config['hip']['last_export'] = choiceExport
			config['hip']['last_process'] = choiceProcess
			config['hip']['last_utility'] = choiceUtility
			config['hip']['last_location'] = choiceLocation
			config['hip']['last_extent'] = choiceExtentLayerName
			with open(iniFile, 'w') as configfile:
				config.write(configfile)
			return [choiceSelectedProcess, choiceLocation, choiceExtentLayerName, choiceExtentLayer]
	else:
			return 'cancel'


def fMainUI():
	OGRLayers, OGRLayerNames, extent_layer_index = fSelectExtentLayer()
	centroidLocations = config.options('locations')

	export_list = [
		'Export: -------------',
		'Export Points to Hip',
		'Export Lines to Hip',
		'Export Polygons to Hip',
		'Export Polygons with Holes',
		'---',
		'Holes - interior rings',
		'Export PDF for Illustrator'
		'Export NetworkZ to Hip',
	]

		# '- TT Delivery Waypoint Routing',
		# '- Orbis Combine POI info',
		# '- Orbis Separate Greens',
		# '- Orbis Select Tree Polygons',
		# '- OSM+MNR Building Join',
		# '- OSM Motorways',
		# '- Orbis Water Merge',
		# '- Orbis Coastline to Polygon',
	process_list=[
		'---- orbis ----',
		'Compute Z Order based on area',
		'Orbis - Compare Unique Fields (landuse)',
		'---- osm & genesis ----',
		'OSM Trees p1 (point,line,poly)',
		'OSM Trees p2 (cleanup excess fields)',
		'Load Landmark XML',
		'MNR Speed Profiles - Find Column',
		'MNR Speed Profiles - Combine PosNeg',
		'---- move portal ----',
		'Move Portal - Orbis',
		'Move Portal - Genesis Combine Time Hits',
		'Move Portal - Genesis Join Pos-Neg',
		'Move Portal - Genesis Single Hour',
		'Move Portal - External Python',
		'Move Portal - Match to MNR-network-UUID',
		'Move Portal - Origin-Destination Areas Help',
		'---- hd roads ----',
		'Get HD Layer New (geojson)',
		'----- Raster+ -----',
		'Get Orbis Raster Tiles',
		'Get Hillshade',
		'Overture'
		]

	utility_list =[
		'---- extent & project ----',
		'Get Extent Coordinates',
		'Add Centroid from Extent',
		'Get Centroid and UTM Zone',
		'Reproject to UTM Zone',
		'Convert to WGT84',
		'---- layer edit -----',
		'Keep Unique Rows by Single Field (HD Cleanup)',
		'Add EPs along MNR edges',
		'Add Chainage Points',
		'Separate ocean water',
		'Holes - interior rings',
		'Buildings - remove parts overlaps',
		'Curvature Orbis Average',
		'Gradient Orbis Average',
		'---- layer info -----',
		'List layers',
		'Mark Temporary layers',
		'Extract to smaller layers',
		'Merge Selected Layers',
		'Subtract Selected Layers',
		'Duplicate as New Layer',
		'Duplicate as New Layer In-Memory',
		'---- table fields ----',
		'Add LatLon Fields',
		'Select Layer Field',
		'List Fields of a Layer',
		'List Unique Values of a Field',
		'Drop Empty Fields of a Layer',
		'-------------',
		'List Installed Python Modules',
		'List QGIS Processing Toolboxes',
		'- Test MNR Source'
		'-------------',
	]
		# 'Keep Only Tree&Wood Fields',


	# result = fHIP_Dialog(export_list, process_list, utility_list, centroidLocations, OGRLayerNames)
	try:
		selected_process, selected_location, extent_layerName, extent_layer = fHIP_Dialog(export_list, process_list, utility_list, centroidLocations, OGRLayerNames, OGRLayers)
		print("choiceSelectedProcess: {} \nchoiceLocation: {} \nchoiceExtentLayerName: {} \nchoiceExtentLayer: {}".format(selected_process, selected_location, extent_layerName, extent_layer))
	except:
			selected_process='Exit'

	if selected_process == 'Export Points to Hip':
		fExportPoints2Hip(selected_location)
	elif selected_process == 'Export Polygons to Hip':
		fExportPolygons2Hip(selected_location)
	elif selected_process == 'Export Polygons with Holes':
		fExportPolygonsWithHoles2Hip(selected_location)
	elif selected_process == 'Export Lines to Hip':
		fExportLines2Hip(selected_location)
	elif selected_process == 'Export NetworkZ to Hip':
		fExportNetworkZ2Hip(selected_location)
	elif selected_process == 'Export PDF for Illustrator':
		import sub_AI_Export
		fExportPDFMain() #sub_AI_Export

	# imported from sub_MovePortalTraffic
	elif selected_process == 'Move Portal - Orbis':
		import sub_MovePortalTraffic
		fCombineOrbis() #sub_MovePortalTraffic
	elif selected_process == 'Move Portal - Genesis Combine Time Hits':
		import sub_MovePortalTraffic
		fJoinTimeHits() #sub_MovePortalTraffic
	elif selected_process == 'Move Portal - Genesis Join Pos-Neg':
		import sub_MovePortalTraffic
		fJoinPosNeg() #sub_MovePortalTraffic
	elif selected_process == 'Move Portal - Genesis Single Hour':
		import sub_MovePortalTraffic
		fMergeSingleHour() #sub_MovePortalTraffic
	elif selected_process == 'Move Portal - External Python':
		import sub_MovePortalTraffic
		fExternalPython() #sub_MovePortalTraffic
	elif selected_process == 'Move Portal - Match to MNR-network-UUID':
		import sub_MovePortalTraffic
		fMergeMoveToRealNetwork() #sub_MovePortalTraffic
	elif selected_process == 'Move Portal - Origin-Destination Areas Help':
		import sub_MovePortalTraffic
		fOriginDestinationAreas() #sub_MovePortalTraffic
	
	elif selected_process == 'MNR Speed Profiles - Find Column':
		fFindColumn() #sub_MNR_SpeedProfiles
	elif selected_process == 'MNR Speed Profiles - Combine PosNeg':
		fCombinePosNeg() #sub_MNR_SpeedProfiles
	
	# imported from sub_Add_Centroid
	elif selected_process == 'Load Landmark XML':
		import sub_Add_Centroid
		import sub_LandmarkXML_to_PointLayer
		fLoadLandmarkFile() #sub_LandmarkXML_to_PointLayer
	elif selected_process == 'Get Extent Coordinates':
		import sub_Add_Centroid
		fGetExtentCoords() #sub_Add_Centroid
	elif selected_process == 'Add Centroid from Extent':
		import sub_Add_Centroid
		fAddCentroid() #sub_Add_Centroid
	elif selected_process == 'Get Centroid and UTM Zone':
		import sub_Add_Centroid
		fGetUTMcentroid() #sub_Add_Centroid
	elif selected_process == 'Reproject to UTM Zone':
		import sub_Add_Centroid
		fReprojectUTM() #sub_Add_Centroid
	elif selected_process == 'Convert to WGT84':
		import sub_Add_Centroid
		fConvertToWGS84(selected_location) #sub_Add_Centroid
	elif selected_process == 'Add EPs along MNR edges':
		fEPsFromMNR()
	elif selected_process == 'Curvature Orbis Average':
		fCurvatureOrbisAvg()
	elif selected_process == 'Gradient Orbis Average':
		fGradientOrbisAvg()
	elif selected_process == 'Add Chainage Points':
		fAddChainagePoints()
	elif selected_process == 'List Installed Python Modules':
		fListPythonModules()
	elif selected_process == 'List QGIS Processing Toolboxes':
		fListQGISProcessing()
	elif selected_process == 'Add LatLon Fields':
		fAddLatLonFields()
	elif selected_process == 'List Fields of a Layer':
		fGetLayerFields()
	elif selected_process == 'Select Layer Field':
		fSelectLayerField()
	# iported from sub_Unique_Fields_Compare.py
	elif selected_process == 'Orbis - Compare Unique Fields (landuse)':
		run_dialog() #sub_MovePortalTraffic
	# iported from sub_Unique_Fields_Compare.py
	elif selected_process == 'Compute Z Order based on area':
		import sub_Z_Order
		sub_Z_Order.compute_z_order_for_active_layer(invert_z=False)
	elif selected_process == 'List Unique Values of a Field':
		fGetFieldUniqueVals()
	elif selected_process == 'Keep Unique Rows by Single Field (HD Cleanup)':
		fKeepUniqueByField()
	elif selected_process == 'Drop Empty Fields of a Layer':
		fDropEmptyLayerFields()
	elif selected_process == 'Duplicate as New Layer':
		fDuplicateLayerAsNew()
	elif selected_process == 'Duplicate as New Layer In-Memory':
		fDuplicateLayerAsNewInMemory()
	elif selected_process == 'Mark Temporary layers':
		fMarkTempLayers()
	elif selected_process == 'List layers':
		fSelectExtentLayer()
	elif selected_process == 'Get HD Layer New (geojson)':
		fGetHDLayer(extent_layer)

	elif selected_process == 'Get Hillshade':
		fGetHillshade(extent_layer, selected_location)


	elif selected_process == 'Get Orbis Raster Tiles':
		out_tif = fGetOrbisRaster(extent_layer)
		print(f"Orbis raster export result: {out_tif}")
		# fGetOrbisRaster(extent_layer)

	elif selected_process == 'Overture':
		fOverture(extent_layer)

	# imported from sub_OSM_queries
	elif selected_process == 'OSM Trees p1 (point,line,poly)':
		import sub_OSM_queries
		fGetOSMTrees(extent_layer) #imported from sub_OSM_queries
	elif selected_process == 'OSM Trees p2 (cleanup excess fields)':
		fCleanupOSMTrees() #imported from sub_OSM_queries

	elif selected_process == 'Separate ocean water':
		fSeparateOceanWater() 
	elif selected_process == 'Holes - interior rings':
		fHoleRings() 
	elif selected_process == 'Buildings - remove parts overlaps':
		fBuildingOverlapParts() 

	elif selected_process == 'Exit':
		print("Exit")
	else:
		print("Not yet implemented")

	
fMainUI()

