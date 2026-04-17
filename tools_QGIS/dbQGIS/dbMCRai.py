# Prepare query for MCR (databrics) 

# ToDO:

print("Loading modules")
# append script folder
from databricks import sql
import h3
# print("loaded databricks")
import os, sys
# print("loaded sys")
current_script_dir = os.path.dirname(os.path.abspath(__file__))
# print("Current script's directory:", current_script_dir)
# Add parent dir for legacy imports
sys.path.append(os.path.dirname(current_script_dir))
# Also add local 'modules' folder (contains sub_* helper modules) so imports like sub_H3_grid work
modules_dir = os.path.join(current_script_dir, 'modules')
if os.path.isdir(modules_dir):
	# put modules dir at front so it shadows any system installs if needed
	sys.path.insert(0, modules_dir)
	# sanity check: report missing expected helpers (helps debug import problems)
	expected_helpers = ['sub_H3_grid.py']
	missing_helpers = [h for h in expected_helpers if not os.path.exists(os.path.join(modules_dir, h))]
	if missing_helpers:
		print(f"Warning: missing helper modules in {modules_dir}: {missing_helpers}")
# import imp
import importlib as imp

from unittest import result
import b9PyQGIS
imp.reload(b9PyQGIS)
# importlib.reload(b9PyQGIS)
from b9PyQGIS import *
from secure_config import get_ini_secret
from qgis.core import QgsDataSourceUri, QgsVectorLayer, QgsProject
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QComboBox, QPushButton, QLabel, QLineEdit, QCheckBox
# print("loaded qgis.core")
import re

# import sub_OSM_queries
# imp.reload(sub_OSM_queries)
# from sub_OSM_queries import *

# VARIABLES
# layerGeoId = ""
# layerAttrId = ""
# dropLineList = []
# global clipLayer
# clipLayer = iface.activeLayer()
# clipLayerName = "" #clipLayer.name()

# geomField = "geom"

# commonLayers = []
# root = QgsProject.instance().layerTreeRoot()
# mainWindow=iface.mainWindow()

# read config file
print("Reading config")
# iniFile = os.path.dirname( imp.find_module('b9PyQGIS')[1] ) + "/" + 'b9QGISdata.ini'
iniFile = os.path.join(os.path.dirname(b9PyQGIS.__file__), 'b9QGISdata.ini')
# spec = importlib.util.find_spec('b9PyQGIS')
# iniFile = os.path.dirname(spec.origin) + "/b9QGISdata.ini"
config = configparser.ConfigParser()
config.read(iniFile)
dirCommonGeopack = config['directories']['dirCommonGeopack']

server_hostname=config['mcr']['server_hostname']

http_path=config['mcr']['http_path']
access_token=get_ini_secret(config, 'mcr', 'access_token')
connection = sql.connect(server_hostname = server_hostname, http_path = http_path, access_token = access_token)
print("Connected to databricks")

# clipLayerName=config['common']['extent']

try:
	import sub_H3_grid
	imp.reload(sub_H3_grid)
	from sub_H3_grid import *
except ModuleNotFoundError:
	print("Warning: 'sub_H3_grid' module not found in path; some features will be disabled. Look for 'modules/sub_H3_grid.py'")

try:
	import sub_overture_buildings
	imp.reload(sub_overture_buildings)
except ModuleNotFoundError:
	print("Warning: 'sub_overture_buildings' module not found in path; Overture download feature will be disabled.")

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


def fSelectExtentLayer(): # get the Extent Layer
	OGRLayers = []
	OGRLayerNames = []
	current_layer = iface.activeLayer()

	for layer in QgsProject.instance().mapLayers().values():
		if layer.providerType()!="wms":
			OGRLayers.append(layer)
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


def fMCR_Dialog(product_versions, process_list, license_zones_polygon, OGRLayerNames, extent_layer_index):

	class MultiInputDialog(QDialog):
		def __init__(self, parent=None):
			super(MultiInputDialog, self).__init__(parent)
			
			# Initialize the dropdown list and text input box
			self.dropdown1 = QComboBox(self) # product version
			self.dropdown2 = QComboBox(self) # process
			self.dropdown3 = QComboBox(self) # country
			self.dropdown4 = QComboBox(self) # extent
			self.checkbox_h3_tiles = QCheckBox("H3 Tiles", self)
			# self.text_input = QLineEdit(self)
			
			# Initialize labels
			label1 = QLabel("Product version:")
			label2 = QLabel("Process:")
			label3 = QLabel("Country:")
			label4 = QLabel("Extent layer:")
			# label3 = QLabel("Test:")

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
			layout.addWidget(self.checkbox_h3_tiles) # Add the checkbox to the layout
			# layout.addWidget(self.text_input)
			layout.addWidget(ok_button)
			layout.addWidget(cancel_button)
			
			# Populate the dropdown list
			self.dropdown1.addItems(product_versions)
			self.dropdown2.addItems(process_list)
			self.dropdown3.addItems(license_zones_polygon)
			self.dropdown4.addItems(OGRLayerNames)
			
			# Set default value for the dropdown
			lastProductVersion = config['mcr']['last_product_version']
			if lastProductVersion in product_versions:
					default_index = product_versions.index(lastProductVersion)
					self.dropdown1.setCurrentIndex(default_index)
			lastProcess = config['mcr']['last_process']
			if lastProcess in process_list:
					default_index = process_list.index(lastProcess)
					self.dropdown2.setCurrentIndex(default_index)
			lastZone = config['mcr']['last_zone']
			if lastZone in license_zones_polygon:
					default_index = license_zones_polygon.index(lastZone)
					self.dropdown3.setCurrentIndex(default_index)
			self.dropdown4.setCurrentIndex(extent_layer_index)
			# position = product_versions.index(lastProductVersion)
			# # Set default text for the QLineEdit
			# lastip=serverIPs[position]
			# self.text_input.setText(lastip)
			lastH3str = config['mcr']['last_h3']
			if lastH3str.lower() == "true":
				lastH3bool = True
			else:
				lastH3bool = False
			self.checkbox_h3_tiles.setChecked(lastH3bool)  # Checkbox starts checked
			# self.text_input.setText("bla")
			# Check the state of the checkbox

			# if self.checkbox_h3_tiles.isChecked():
			# 	print("The checkbox is checked!")
			# else:
			# 	print("The checkbox is not checked.")


		def get_selection(self):
			# Get the selected item from the dropdown list and text from QLineEdit
			choiceProductVersion = self.dropdown1.currentText()
			choiceProcess = self.dropdown2.currentText()
			choiceZone = self.dropdown3.currentText()
			choiceExtentLayerName = self.dropdown4.currentText()
			choiceExtentLayerNameIndex = self.dropdown4.currentIndex()
			choiceH3 = str(self.checkbox_h3_tiles.isChecked())
			print(choiceH3)
			# choiceIP = self.text_input.text()
			return choiceProductVersion, choiceProcess, choiceZone, choiceExtentLayerName, choiceExtentLayerNameIndex, choiceH3 #, choiceIP

	# display dialog:
	dialog = MultiInputDialog()
	result = dialog.exec_()

	# write config
	if result == QDialog.Accepted:
			choiceProductVersion, choiceProcess, choiceZone, choiceExtentLayerName, choiceExtentLayerNameIndex, choiceH3 = dialog.get_selection() #choiceIP
			config['mcr']['last_product_version'] = choiceProductVersion
			config['mcr']['last_process'] = choiceProcess
			config['mcr']['last_zone'] = choiceZone
			config['mcr']['extent_mcr'] = choiceExtentLayerName
			config['mcr']['last_h3'] = choiceH3
			with open(iniFile, 'w') as configfile:
				config.write(configfile)
			# print("QGIS server name:", choiceProductVersion)
			# print("Orbis server IP:", choiceIP)
			return [choiceProductVersion, choiceProcess, choiceZone, choiceExtentLayerName, choiceExtentLayerNameIndex, choiceH3] #choiceIP
	else:
		return 'cancel'


def _normalize_product_version_for_table(product_version):
	"""Normalize product version into table suffix format."""
	value = (product_version or "").strip().lower()
	value = re.sub(r'[^a-z0-9]+', '_', value)
	return value.strip('_')


def fGetMcrTableNames(cursor):
	"""List table names from map_central_repository schema."""
	cursor.execute("""
		SELECT table_name
		FROM pu_orbis_platform_prod_catalog.information_schema.tables
		WHERE table_schema = 'map_central_repository'
	""")
	return [row[0] for row in cursor.fetchall()]


def fResolveMcrVersionedTable(table_names, base_table, product_version):
	"""Resolve base table to versioned table for the selected product version."""
	if not table_names:
		return None

	product_suffix = _normalize_product_version_for_table(product_version)
	table_names_set = set(table_names)

	candidate_exact = f"{base_table}_{product_suffix}"
	if candidate_exact in table_names_set:
		return f"pu_orbis_platform_prod_catalog.map_central_repository.{candidate_exact}"

	# fallback for legacy layout
	if base_table in table_names_set:
		return f"pu_orbis_platform_prod_catalog.map_central_repository.{base_table}"

	# lenient fallback for variants that still end with the normalized product suffix
	for table_name in table_names:
		if table_name.startswith(base_table + "_") and table_name.endswith(product_suffix):
			return f"pu_orbis_platform_prod_catalog.map_central_repository.{table_name}"

	return None


def fResolveMcrVersionedTableExact(table_names, base_table, product_version):
	"""Resolve only the exact versioned table for the selected product version."""
	if not table_names:
		return None
	product_suffix = _normalize_product_version_for_table(product_version)
	candidate_exact = f"{base_table}_{product_suffix}"
	if candidate_exact in set(table_names):
		return f"pu_orbis_platform_prod_catalog.map_central_repository.{candidate_exact}"
	return None


def fAllPolyIntersect(product_version, license_zone, extentCoords):
	extentStr = "'" + extentCoords + "'"

	sql = """
	-- all polygons intersecting
	SELECT 
	orbis_id,
	map_entries(tags) AS tags_array,
	geometry 
	FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.polygons
	WHERE 
	ST_Intersects(ST_GEOMFROMWKT({extent}), ST_GEOMFROMWKT(geometry)) 
	AND 
	product = '{product_version}'
	AND
	license_zone like '%{license_zone}%'

	UNION

	SELECT 
	orbis_id,
	map_entries(tags) AS tags_array,
	geometry 
	FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.relations_geometries
	WHERE 
	geom_type in ("ST_POLYGON","ST_MULTIPOLYGON")
	AND
	ST_Intersects(ST_GEOMFROMWKT({extent}), ST_GEOMFROMWKT(geometry)) 
	AND 
	product = '{product_version}'
	AND
	license_zone like '%{license_zone}%'
	""".format(product_version=product_version, license_zone=license_zone, extent=extentStr)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)

def fAllPolyContains(product_version, license_zone, extentCoords):
	extentStr = "'" + extentCoords + "'"

	sql = """
	-- all polygons contains
	SELECT 
	orbis_id,
	map_entries(tags) AS tags_array,
	geometry 
	FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.polygons
	WHERE 
	ST_Contains(ST_GEOMFROMWKT({extent}), ST_GEOMFROMWKT(geometry)) 
	AND 
	product = '{product_version}'
	AND
	license_zone like '%{license_zone}%'

	UNION

	SELECT 
	orbis_id,
	map_entries(tags) AS tags_array,
	geometry 
	FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.relations_geometries
	WHERE 
	geom_type in ("ST_POLYGON","ST_MULTIPOLYGON")
	AND
	ST_Contains(ST_GEOMFROMWKT({extent}), ST_GEOMFROMWKT(geometry)) 
	AND 
	product = '{product_version}'
	AND
	license_zone like '%{license_zone}%'
	""".format(product_version=product_version, license_zone=license_zone, extent=extentStr)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fProcessOvertureBuildings(extentCoords):
	if 'sub_overture_buildings' not in globals():
		message = (
			"Overture module is unavailable.\n"
			"Missing: modules/sub_overture_buildings.py"
		)
		print(message)
		qtMsgBox(message)
		return

	# Optional override for external runtime that has overturemaps installed.
	# Example:
	# export OVERTURE_PYTHON=/path/to/python3.11
	# or make `overturemaps` / `uvx` available on PATH.
	external_python = os.environ.get("OVERTURE_PYTHON", "").strip() or None

	result = sub_overture_buildings.download_overture_buildings_from_wkt(
		wkt_polygon=extentCoords,
		output_path=None,
		output_format="geoparquet",
		overture_type="building",
		base_dir=dirCommonGeopack,
		python_exe=external_python,
		timeout_sec=3600,
	)

	if result.get("ok"):
		message = (
			"Overture buildings downloaded.\n\n"
			f"Output: {result.get('output_path')}\n"
			f"BBOX: {result.get('bbox')}\n\n"
			"Load the output GeoParquet into QGIS."
		)
		print(message)
		qtMsgBox(message)
		return

	error = result.get("error", "Unknown error.")
	message = (
		"Overture buildings download failed.\n\n"
		f"{error}\n\n"
		"Requirements:\n"
		"- External runtime with overturemaps CLI (Python >= 3.10)\n"
		"- Install with: pip install overturemaps\n"
		"- Optional env override: OVERTURE_PYTHON=/path/to/python3.11"
	)
	print(message)
	qtMsgBox(message)

def fProcessAdminAreas(extent_layer, product_version, license_zone, extentCoords, h3, relations_table, admin_name_filter=None):
	if h3 == True:
		hextiles = fHexesFromExtent(extent_layer)
		bounds = hexListToChildString(hextiles)
		h3_index = 'AND h3_index != \'0\''
	else:
		extentStr = "'" + extentCoords + "'"
		bounds = 	f"ST_Intersects(ST_GEOMFROMWKT({extentStr}), ST_GEOMFROMWKT(geometry))"
		h3_index = ''

	extentStr = "'" + extentCoords + "'"
	name_filter_sql = ""
	if admin_name_filter is not None:
		admin_name_filter = admin_name_filter.strip()
		if admin_name_filter != "":
			admin_name_filter_sql = admin_name_filter.replace("'", "''")
			name_filter_sql = f"\n\tAND tags['name'] ILIKE '%{admin_name_filter_sql}%'"

	sql = """
	-- list admin-related columns from relations table, ok
	-- hope that relation table alreeady includes the correct geometry
	WITH bbox AS (
		SELECT ST_GEOMFROMWKT({extent}) AS g
	)
	SELECT
		orbis_id,
		layer_id,
		tags['name'] as name,
		tags['default_language'] as language,
		tags['boundary'] as boundary,
		tags['type'] as type,
		tags['place'] as place,
		tags['admin_level'] as admin_level,
		exploded_member.id AS admin_centre_id,
		map_filter(tags, (key, value) -> NOT (key LIKE 'layer_id:%' OR key LIKE 'gers%' OR key LIKE 'license%' OR key LIKE 'maxspeed%' OR key LIKE 'oprod%' OR key LIKE 'source%' OR key LIKE 'supported%' OR key LIKE 'zoomlevel_min' OR key LIKE 'routing_class' OR key LIKE 'navigability' OR key LIKE 'postal_code%' OR key LIKE '%pronunciation%' )) AS tags_clean,
		--members,
		--tags,
		geometry
	FROM {relations_table},
	bbox
	LATERAL VIEW EXPLODE(FILTER(members, x -> x.role = 'admin_centre')) AS exploded_member
	WHERE tags['type'] = 'boundary'
	AND
	tags['boundary'] = 'administrative'
	{name_filter_sql}
	AND
	geom_type in ("ST_POLYGON","ST_MULTIPOLYGON")
	AND 
	ST_Intersects(bbox.g, ST_GEOMFROMWKT(geometry))
	AND
	license_zone like '%{license_zone}%' 
	;""".format(
		product_version=product_version,
		license_zone=license_zone,
		extent=extentStr,
		name_filter_sql=name_filter_sql,
		relations_table=relations_table
	)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fProcessPlacePoint(extent_layer, product_version, license_zone, extentCoords, h3, points_table):
	if h3 == True:
		hextiles = fHexesFromExtent(extent_layer)
		bounds = hexListToChildString(hextiles)
		h3_index = 'AND h3_index != \'0\''
	else:
		extentStr = "'" + extentCoords + "'"
		bounds = 	f"ST_Intersects(ST_GEOMFROMWKT({extentStr}), ST_GEOMFROMWKT(geometry))"
		h3_index = ''

	extentStr = "'" + extentCoords + "'"

	# sql = f"""
	# -- point places
	# -- admin centers
	# SELECT
	# orbis_id,
	# layer_id,
	# tags['name'] as name,
	# tags['place'] as place,
	# tags['capital'] as capital,
	# map_filter(tags, (key, value) -> NOT (key LIKE 'layer_id:%' OR key LIKE 'gers%' OR key LIKE 'license%' OR key LIKE 'maxspeed%' OR key LIKE 'oprod%' OR key LIKE 'source%' OR key LIKE 'supported%' OR key LIKE 'zoomlevel_min' OR key LIKE 'routing_class' OR key LIKE 'navigability' OR key LIKE 'postal_code%' OR key LIKE '%pronunciation%' OR key LIKE '%tokenized%')) AS tags_clean,
	# geometry 
	# FROM pu_orbis_platform_prod_catalog.map_central_repository.points
	# WHERE 
	# tags['place'] is not null
	# AND {bounds}
	# AND product = '{product_version}'
	# AND license_zone like '%{license_zone}%' 
	# {h3_index};"""

	sql = """
	-- point places
	-- admin centers
	WITH bbox AS (
	SELECT ST_GEOMFROMWKT({extent}) AS g
	)
	SELECT
	orbis_id,
	layer_id,
	tags['name'] as name,
	tags['place'] as place,
	tags['capital'] as capital,
	-- map_filter(tags, (key, value) -> NOT (key LIKE 'layer_id:%' OR key LIKE 'gers%' OR key LIKE 'license%' OR key LIKE 'maxspeed%' OR key LIKE 'oprod%' OR key LIKE 'source%' OR key LIKE 'supported%' OR key LIKE 'zoomlevel_min' OR key LIKE 'routing_class' OR key LIKE 'navigability' OR key LIKE 'postal_code%' OR key LIKE '%pronunciation%' OR key LIKE '%tokenized%')) AS tags_clean,
	geometry 
	FROM {points_table},
	bbox
	WHERE 
	tags['place'] is not null
	AND 
	ST_Intersects(bbox.g, ST_GEOMFROMWKT(geometry))
	AND
	license_zone like '%{license_zone}%'
	;
	""".format(
		product_version=product_version,
		license_zone=license_zone,
		extent=extentStr,
		points_table=points_table
	)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fProcessInlandWater(extent_layer, product_version, license_zone, extentCoords, h3, polygons_table, relations_geometries_table):
	if h3 == True:
		hextiles = fHexesFromExtent(extent_layer)
		bounds = hexListToChildString(hextiles)
		h3_index = 'AND h3_index != \'0\''
	else:
		extentStr = "'" + extentCoords + "'"
		bounds = 	f"ST_Intersects(ST_GEOMFROMWKT({extentStr}), ST_GEOMFROMWKT(geometry))"
		h3_index = ''

	extentStr = "'" + extentCoords + "'"

	# sql = f"""
	# -- inland water (natural=water)
	# SELECT 
	# orbis_id,
	# intermittent,
	# geometry 
	# FROM 
	# pu_orbis_platform_prod_catalog.map_central_repository.polygons
	# WHERE 
	# natural = 'water' 
	# AND {bounds}
	# AND product = '{product_version}'
	# AND license_zone like '%{license_zone}%' 
	# {h3_index}

	# UNION 

	# SELECT 
	# orbis_id,
	# --intermittent,
	# tags['intermittent'] as intermittent,
	# geometry 
	# FROM 
	# pu_orbis_platform_prod_catalog.map_central_repository.relations_geometries
	# WHERE 
	# tags['natural'] = 'water'
	# AND
	# geom_type in ("ST_POLYGON","ST_MULTIPOLYGON")
	# AND {bounds}
	# AND product = '{product_version}'
	# AND license_zone like '%{license_zone}%' 
	# {h3_index};"""

	sql = """
	-- inland water (natural=water)
	-- old is 2.55 : new is 1.45
WITH bbox AS (
	SELECT ST_GEOMFROMWKT({extent}) AS g
)

SELECT 
	orbis_id,
	intermittent,
	geometry 
FROM 
	{polygons_table},
	bbox
WHERE 
	natural = 'water' 
	AND ST_Intersects(bbox.g, ST_GEOMFROMWKT(geometry))
	AND license_zone like '%{license_zone}%'

UNION 

SELECT 
	orbis_id,
	tags['intermittent'] AS intermittent,
	geometry 
FROM 
	{relations_geometries_table},
	bbox
WHERE 
	tags['natural'] = 'water'
	AND geom_type IN ("ST_POLYGON","ST_MULTIPOLYGON")
	AND ST_Intersects(bbox.g, ST_GEOMFROMWKT(geometry))
	AND license_zone like '%{license_zone}%'
	""".format(
		product_version=product_version,
		license_zone=license_zone,
		extent=extentStr,
		polygons_table=polygons_table,
		relations_geometries_table=relations_geometries_table
	)


	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)

def fProcessOceanWater(extent_layer, product_version, license_zone, extentCoords, h3, polygons_table, relations_geometries_table):
	if h3 == True:
		hextiles = fHexesFromExtent(extent_layer)
		bounds = hexListToChildString(hextiles)
		h3_index = 'AND h3_index != \'0\''
	else:
		extentStr = "'" + extentCoords + "'"
		bounds = 	f"ST_Intersects(ST_GEOMFROMWKT({extentStr}), ST_GEOMFROMWKT(geometry))"
		h3_index = ''

	sql = f"""
	-- osean water with extra areas
	SELECT
	orbis_id,
	tags['maritime_water'] AS maritime_water,
	tags['land_mass'] AS land_mass,
	tags['geometry_type'] AS geometry_type,
	--to_json(mcr_tags) AS mcr_tags,
	geometry 
	FROM 
	{polygons_table}
	WHERE 
	(tags['geometry_type'] = 'area'
	OR
	tags['maritime_water'] = 'yes'
	OR
	tags['land_mass'] = 'yes')
	AND {bounds}
	AND license_zone like '%{license_zone}%' 
	{h3_index}

	UNION

	SELECT
	orbis_id,
	tags['maritime_water'] AS maritime_water,
	tags['land_mass'] AS land_mass,
	tags['geometry_type'] AS geometry_type,
	--to_json(mcr_tags) AS mcr_tags,
	geometry 
	FROM 
	{relations_geometries_table}
	WHERE 
	(tags['geometry_type'] = 'area'
	OR
	tags['maritime_water'] = 'yes'
	OR
	tags['land_mass'] = 'yes')
	AND {bounds}
	AND license_zone like '%{license_zone}%' 
	{h3_index};"""

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)

def fProcessNetworkSpeeds(product_version, license_zone, extentCoords):
	extentStr = "'" + extentCoords + "'"

	# sql = """
	# -- Maxscpeed is not captured when in variants
	# -- Check for Z-Level
	# select
	# orbis_id, 
	# highway,
	# railway, 
	# CASE	
	# 	WHEN route = 'ferry' THEN 'ferry'
	# 	ELSE NULL
	# 	END AS ferry_line,
	# CASE 
	# 	WHEN highway IN ('living_street','motorway','motorway_link','primary_link','primary','residential','construction','secondary_link','secondary','tertiary_link','tertiary','trunk_link','trunk','unclassified','road') THEN 'road_major'
	# 	WHEN highway IN ('bridleway','cycleway','footway','path','pedestrian','service','steps','track') THEN 'road_minor'
	# 	WHEN highway is null THEN null
	# 	ELSE 'highway'
	# 	END AS road_line,
	# CASE	
	# 	WHEN railway IN 
	# 	('funicular','light_rail','miniature','monorail','narrow_gauge','preserved','construction','rail','subway','tram') THEN 'rail_core'
	# 	WHEN railway IN ('abandoned','disused','proposed') THEN 'rail_other'
	# 	ELSE null
	# 	END AS railway_line,
	# bridge, tunnel,
	# tags['navigability'] AS navigability,
	# tags['routing_class'] AS routing_class,
	# tags['controlled_access'] AS controlled_access,
	# tags['dual_carriageway'] AS dual_carriageway,
	# tags['lanes'] AS lanes,
	# CASE
	# 	WHEN oneway is not null THEN oneway 
	# 	WHEN tags['oneway'] IS NOT NULL THEN tags['oneway']
	# 	ELSE NULL
	# 	END AS oneway,
	# CASE 
	# 	WHEN name IS NOT NULL THEN name
	# 	WHEN tags['name:en-Latn'] IS NOT NULL THEN tags['name:en-Latn']
	# 	WHEN tags['name:fr-Latn'] IS NOT NULL THEN tags['name:fr-Latn']
	# 	WHEN tags['name:de-Latn'] IS NOT NULL THEN tags['name:de-Latn']
	# 	WHEN tags['name:es-Latn'] IS NOT NULL THEN tags['name:es-Latn']
	# 	WHEN tags['name:it-Latn'] IS NOT NULL THEN tags['name:it-Latn']
	# 	WHEN tags['name:pt-Latn'] IS NOT NULL THEN tags['name:pt-Latn']
	# 	WHEN tags['name:ca-Latn'] IS NOT NULL THEN tags['name:ca-Latn']
	# 	END AS name,
	# --STRING_AGG(key || '=>' || value, ';') FILTER (WHERE key LIKE 'name:%' and key !~ 'pronunciation') AS name_values,
	# tags['maxspeed'] AS maxspeed,
	# --STRING_AGG(key || '=>' || value, ';') FILTER (WHERE key LIKE 'maxspeed:%' AND key NOT LIKE '%verification%') AS maxspeed_values,
	# layer, 
	# tags['layer_id'] AS layer_id,
	# tags['zoomlevel_min'] AS zoomlevel_min,
	# --z_order,
	# geometry

	# FROM 
	# pu_orbis_platform_prod_catalog.map_central_repository.lines

	# WHERE (
	# "highway" is not null or
	# "railway" is not null or
	# "route" = 'ferry'
	# )

	# AND
	# ST_Intersects(ST_GEOMFROMWKT({extent}), ST_GEOMFROMWKT(geometry)) 
	# AND 
	# product = '{product_version}'
	# AND
	# license_zone like '%{license_zone}%' 
	# """.format(product_version=product_version, license_zone=license_zone, extent=extentStr)

	sql = """
	-- road network
	WITH bbox AS (
		SELECT ST_GEOMFROMWKT({extent}) AS g
	)

	select
	orbis_id, 
	highway,
	railway, 
	CASE	
		WHEN route = 'ferry' THEN 'ferry'
		ELSE NULL
		END AS ferry_line,
	CASE 
		WHEN highway IN ('living_street','motorway','motorway_link','primary_link','primary','residential','construction','secondary_link','secondary','tertiary_link','tertiary','trunk_link','trunk','unclassified','road') THEN 'road_major'
		WHEN highway IN ('bridleway','cycleway','footway','path','pedestrian','service','steps','track') THEN 'road_minor'
		WHEN highway is null THEN null
		ELSE 'highway'
		END AS road_line,
	CASE	
		WHEN railway IN 
		('funicular','light_rail','miniature','monorail','narrow_gauge','preserved','construction','rail','subway','tram') THEN 'rail_core'
		WHEN railway IN ('abandoned','disused','proposed') THEN 'rail_other'
		ELSE null
		END AS railway_line,
	bridge, tunnel,
	tags['navigability'] AS navigability,
	tags['routing_class'] AS routing_class,
	tags['controlled_access'] AS controlled_access,
	tags['dual_carriageway'] AS dual_carriageway,
	tags['lanes'] AS lanes,
	CASE
		WHEN oneway is not null THEN oneway 
		WHEN tags['oneway'] IS NOT NULL THEN tags['oneway']
		ELSE NULL
		END AS oneway,
	CASE 
		WHEN name IS NOT NULL THEN name
		WHEN tags['name:en-Latn'] IS NOT NULL THEN tags['name:en-Latn']
		WHEN tags['name:fr-Latn'] IS NOT NULL THEN tags['name:fr-Latn']
		WHEN tags['name:de-Latn'] IS NOT NULL THEN tags['name:de-Latn']
		WHEN tags['name:es-Latn'] IS NOT NULL THEN tags['name:es-Latn']
		WHEN tags['name:it-Latn'] IS NOT NULL THEN tags['name:it-Latn']
		WHEN tags['name:pt-Latn'] IS NOT NULL THEN tags['name:pt-Latn']
		WHEN tags['name:ca-Latn'] IS NOT NULL THEN tags['name:ca-Latn']
		END AS name,
	--STRING_AGG(key || '=>' || value, ';') FILTER (WHERE key LIKE 'name:%' and key !~ 'pronunciation') AS name_values,
	tags['maxspeed'] AS maxspeed,
	--STRING_AGG(key || '=>' || value, ';') FILTER (WHERE key LIKE 'maxspeed:%' AND key NOT LIKE '%verification%') AS maxspeed_values,
	layer, 
	tags['layer_id'] AS layer_id,
	tags['zoomlevel_min'] AS zoomlevel_min,
	--z_order,
	geometry

	FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.lines,
	bbox

	WHERE (
	"highway" is not null or
	"railway" is not null or
	"route" = 'ferry'
	)

	AND 
	ST_Intersects(bbox.g, ST_GEOMFROMWKT(geometry))
	AND
	product = '{product_version}'
	AND
	license_zone like '%{license_zone}%' 
	""".format(product_version=product_version, license_zone=license_zone, extent=extentStr)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)

def fProcNetworkMajor(product_version, license_zone, extentCoords, lines_table, menu_name=None):
	extentStr = "'" + extentCoords + "'"
	menu = menu_name if menu_name else 'Transportation Line Extraction'

	sql = """
	-- {menu}
	-- road network with lanes, speeds (optimized: parse WKT once, envelope prefilter, push filters early)
WITH bbox AS (
	SELECT ST_GEOMFROMWKT({extent}) AS g,
		ST_Envelope(ST_GEOMFROMWKT({extent})) AS genv
),
lines_filtered AS (
	SELECT
		orbis_id,
		highway,
		railway,
		route,
		bridge,
		tunnel,
		tags,
		COALESCE(oneway, tags['oneway']) AS oneway,
		COALESCE(name, tags['name:en-Latn']) AS name,
		tags['navigability'] AS navigability,
		tags['routing_class'] AS routing_class,
		tags['controlled_access'] AS controlled_access,
		tags['dual_carriageway'] AS dual_carriageway,
		tags['lanes'] AS lanes,
		tags['sidewalk'] AS sidewalk,
		tags['speed:free_flow'] AS speed_free_flow,
		tags['speed:week'] AS speed_week,
		tags['speed:weekday'] AS speed_weekday,
		tags['speed:weekend'] AS speed_weekend,
		tags['maxspeed'] AS maxspeed,
		layer,
		tags['layer_id'] AS layer_id,
		tags['zoomlevel_min'] AS zoomlevel_min,
		geometry,
		ST_GEOMFROMWKT(geometry) AS g,
		ST_Envelope(ST_GEOMFROMWKT(geometry)) AS env
	FROM {lines_table}
	WHERE (highway IS NOT NULL OR railway IS NOT NULL OR route = 'ferry')
		AND license_zone LIKE '%{license_zone}%'
)

SELECT
	orbis_id,
	highway,
	railway,
	CASE	
		WHEN route = 'ferry' THEN 'ferry'
		ELSE NULL
		END AS ferry_line,
	CASE 
		WHEN highway IN ('living_street','motorway','motorway_link','primary_link','primary','residential','construction','secondary_link','secondary','tertiary_link','tertiary','trunk_link','trunk','unclassified','road') THEN 'road_major'
		WHEN highway IN ('bridleway','cycleway','footway','path','pedestrian','service','steps','track') THEN 'road_minor'
		WHEN highway IS NULL THEN NULL
		ELSE 'highway'
		END AS road_line,
	CASE	
		WHEN railway IN 
		('funicular','light_rail','miniature','monorail','narrow_gauge','preserved','construction','rail','subway','tram') THEN 'rail_core'
		WHEN railway IN ('abandoned','disused','proposed') THEN 'rail_other'
		ELSE NULL
		END AS railway_line,
	bridge, tunnel,
	navigability,
	routing_class,
	controlled_access,
	dual_carriageway,
	lanes,
	sidewalk,
	speed_free_flow,
	speed_week,
	speed_weekday,
	speed_weekend,
	oneway,
	CASE 
		WHEN name IS NOT NULL THEN name
		WHEN tags['name:en-Latn'] IS NOT NULL THEN tags['name:en-Latn']
		WHEN tags['name:fr-Latn'] IS NOT NULL THEN tags['name:fr-Latn']
		WHEN tags['name:de-Latn'] IS NOT NULL THEN tags['name:de-Latn']
		WHEN tags['name:es-Latn'] IS NOT NULL THEN tags['name:es-Latn']
		WHEN tags['name:it-Latn'] IS NOT NULL THEN tags['name:it-Latn']
		WHEN tags['name:pt-Latn'] IS NOT NULL THEN tags['name:pt-Latn']
		WHEN tags['name:ca-Latn'] IS NOT NULL THEN tags['name:ca-Latn']
		END AS name,
	maxspeed,
	layer, 
	layer_id,
	zoomlevel_min,
	--z_order,
	geometry

FROM lines_filtered lf
JOIN bbox b
	ON ST_Intersects(b.genv, lf.env) -- cheap envelope filter
	AND ST_Intersects(b.g, lf.g)     -- exact geometry filter
	""".format(
		product_version=product_version,
		license_zone=license_zone,
		extent=extentStr,
		menu=menu,
		lines_table=lines_table
	)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fProcNetworkSimple(product_version, license_zone, extentCoords, lines_table, menu_name=None):
	extentStr = "'" + extentCoords + "'"
	menu = menu_name if menu_name else 'Transportation Line Extraction'

	sql = """
	-- {menu}
	-- road network simple (optimized: parse WKT once, envelope prefilter, push filters early)
WITH bbox AS (
	SELECT ST_GEOMFROMWKT({extent}) AS g,
		ST_Envelope(ST_GEOMFROMWKT({extent})) AS genv
),
lines_filtered AS (
	SELECT
		orbis_id,
		highway,
		railway,
		bridge,
		tunnel,
		tags['navigability'] AS navigability,
		tags['routing_class'] AS routing_class,
		tags['maxspeed'] AS maxspeed,
		layer,
		geometry,
		ST_GEOMFROMWKT(geometry) AS g,
		ST_Envelope(ST_GEOMFROMWKT(geometry)) AS env
	FROM {lines_table}
	WHERE (highway IS NOT NULL OR tags['routing_class'] IS NOT NULL)
		AND license_zone LIKE '%{license_zone}%'
)

SELECT
	orbis_id, 
	highway,
	railway, 
	bridge, tunnel,
	navigability,
	routing_class,
	maxspeed,
	layer, 
	geometry
FROM lines_filtered lf
JOIN bbox b
	ON ST_Intersects(b.genv, lf.env) -- cheap envelope prefilter
	AND ST_Intersects(b.g, lf.g)     -- exact geometry check
	""".format(
		product_version=product_version,
		license_zone=license_zone,
		extent=extentStr,
		menu=menu,
		lines_table=lines_table
	)
	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)

def fProcessNetworkElevation(extent_layer, product_version, license_zone, extentCoords, h3):
	if h3 == True:
		hextiles = fHexesFromExtent(extent_layer)
		bounds = hexListToChildString(hextiles)
		h3_index = 'AND h3_index != \'0\''
	else:
		extentStr = "'" + extentCoords + "'"
		bounds = 	f"ST_Intersects(ST_GEOMFROMWKT({extentStr}), ST_GEOMFROMWKT(geometry))"
		h3_index = ''

	sql = f"""
	-- Network Elevation
	select
	orbis_id, 
	layer_id,
	tags['gers_identifier'] AS gers,
	--h3_index,
	--h3_resolution,
	tags['bridge'] AS bridge,
	tags['tunnel'] AS tunnel,
	tags['routing_class'] AS routing_class,
	tags['highway'] AS highway,
	tags['railway'] AS railway,
		CASE 
				WHEN tags['route'] = 'ferry' THEN tags['route']
				ELSE NULL
		END AS ferry,
	tags['navigability'] AS tag_navigability,
	tags['maxspeed'] AS maxspeed,
	layer,
	name,
	map_filter(mcr_tags, (key, value) -> NOT (key LIKE 'layer_id:%' OR key LIKE 'gers%' OR key LIKE 'license%' OR key LIKE 'maxspeed%' OR key LIKE 'oprod%' OR key LIKE 'source%' OR key LIKE 'supported%' OR key LIKE 'zoomlevel_min' OR key LIKE 'routing_class' OR key LIKE 'navigability' OR key LIKE 'postal_code%' OR key LIKE '%pronunciation%' )) AS mcr_clean,
	geometry
	FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.lines
	WHERE 
	(
		highway IS NOT NULL AND highway != '' 
		OR 
		tags['highway'] is not null
		OR 
		railway IS NOT NULL AND railway != '' 
		OR 
		tags['railway'] is not null
		OR 
		tags['route'] is not null
	)
	AND {bounds}
	AND product = '{product_version}'
	AND license_zone like '%{license_zone}%' 
	{h3_index};"""

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fProcessNetworkJunctions(extent_layer, product_version, license_zone, extentCoords, h3):
	if h3 == True:
		hextiles = fHexesFromExtent(extent_layer)
		bounds = hexListToChildString(hextiles)
		h3_index = 'AND h3_index != \'0\''
		# print(f"H3 bounds statement:\n{bounds}")
	else:
		extentStr = "'" + extentCoords + "'"
		bounds = 	f"ST_Intersects(ST_GEOMFROMWKT({extentStr}), ST_GEOMFROMWKT(geometry))"
		h3_index = ''

	sql = f"""
	-- junctions
	select
	orbis_id, 
	layer_id, 
	--h3_index, 
	--h3_resolution, 
	highway, 
	tags, 
	mcr_tags,
	mcr_tags['connector'] AS connector,
	geometry 
		FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.points
	WHERE 
	--layer_id = 6
	--AND 
	tags['connector'] IS NOT NULL AND tags['connector'] != ''
	AND 
	highway IS NOT NULL AND highway != '' 
	AND {bounds}
	AND product = '{product_version}'
	AND license_zone like '%{license_zone}%' 
	{h3_index};"""

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fProcessSteetLamp(extent_layer, product_version, license_zone, extentCoords, h3, points_table):
	if h3 == True:
		hextiles = fHexesFromExtent(extent_layer)
		bounds = hexListToChildString(hextiles)
		h3_index = 'AND h3_index != \'0\''
		# print(f"H3 bounds statement:\n{bounds}")
	else:
		extentStr = "'" + extentCoords + "'"
		bounds = 	f"ST_Intersects(ST_GEOMFROMWKT({extentStr}), ST_GEOMFROMWKT(geometry))"
		h3_index = ''

	sql = f"""
	-- street lamps
	select 
	tags['highway'] AS highway_object,
	tags, mcr_tags,
	geometry
	FROM 
	{points_table}
	WHERE
	-- layer_id = 21263 OR
	tags['highway'] = 'street_lamp'
	-- AND 
	-- highway IS NOT NULL AND highway != '' 
	-- AND tags['routing_class'] < 4
	AND {bounds}
	AND license_zone like '%{license_zone}%' 
	{h3_index}
	;"""

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)

def fProcessAllRelations(extent_layer, product_version, license_zone, extentCoords, h3):
	if h3 == True:
		hextiles = fHexesFromExtent(extent_layer)
		bounds = hexListToChildString(hextiles)
		h3_index = 'AND h3_index != \'0\''
		# print(f"H3 bounds statement:\n{bounds}")
	else:
		extentStr = "'" + extentCoords + "'"
		bounds = 	f"ST_Intersects(ST_GEOMFROMWKT({extentStr}), ST_GEOMFROMWKT(geometry))"
		h3_index = ''

	sql = f"""
	-- all connectivity relations (not relation_geometry) of type 'LINESTRING' 
	SELECT 
	orbis_id,
	layer_id,
	tags['type'] as type,
	--(filter(members, x -> x.role = 'from')[0]).id AS from_id,
	--(filter(members, x -> x.role = 'via')[0]).id AS via_id,
	--(filter(members, x -> x.role = 'to')[0]).id AS to_id,
	(filter(members, x -> x.role = 'from')[0]) AS from_id,
	(filter(members, x -> x.role = 'via')[0]) AS via_id,
	(filter(members, x -> x.role = 'to')[0]) AS to_id,
	members,
	-- tags,
	mcr_tags,
	geometry
	FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.relations
	WHERE 
	geom_type in ('ST_MULTILINESTRING', 'ST_LINESTRING')
	AND {bounds}
	AND product = '{product_version}'
	AND license_zone like '%{license_zone}%'
	{h3_index}
	;"""

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)

def fProcessRelationsGeomPoint(extent_layer, product_version, license_zone, extentCoords, h3):
	if h3 == True:
		hextiles = fHexesFromExtent(extent_layer)
		bounds = hexListToChildString(hextiles)
		h3_index = 'AND h3_index != \'0\''
		# print(f"H3 bounds statement:\n{bounds}")
	else:
		extentStr = "'" + extentCoords + "'"
		bounds = 	f"ST_Intersects(ST_GEOMFROMWKT({extentStr}), ST_GEOMFROMWKT(geometry))"
		h3_index = ''

	sql = f"""
	-- all polygonal relations_geometry
	SELECT 
	orbis_id,
	layer_id,
	tags['type'] as tag_type,
	--aeroway, historic, 
	amenity,boundary,building,highway,landuse,leisure,man_made,military,natural,place,public_transport,railway,shop,tourism,
	members,
	--(filter(members, x -> x.role = 'from')[0]).id AS from_id,
	--(filter(members, x -> x.role = 'via')[0]).id AS via_id,
	--(filter(members, x -> x.role = 'to')[0]).id AS to_id,
	--(filter(members, x -> x.role = 'from')[0]) AS from_id,
	--(filter(members, x -> x.role = 'via')[0]) AS via_id,
	--(filter(members, x -> x.role = 'to')[0]) AS to_id,
	map_filter(mcr_tags, (key, value) -> NOT (key LIKE 'layer_id:%' OR key LIKE 'gers%' OR key LIKE 'license%' OR key LIKE 'maxspeed%' OR key LIKE 'oprod%' OR key LIKE 'source%' OR key LIKE 'supported%' OR key LIKE 'zoomlevel_min' OR key LIKE 'routing_class' OR key LIKE 'navigability' OR key LIKE 'postal_code%' OR key LIKE '%pronunciation%' )) AS mcr_clean,
	geom_type, geometry
	FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.relations_geometries
	WHERE 
	geom_type in ('ST_POINT', 'ST_MULTIPOINT')
	--geom_type in ('ST_MULTILINESTRING', 'ST_LINESTRING')
	--geom_type in ('ST_POLYGON', 'ST_MULTIPOLYGON')
	--geom_type in ('ST_MULTILINESTRING', 'ST_LINESTRING', 'ST_POINT', 'ST_POLYGON', 'ST_MULTIPOLYGON')
	--'ST_MULTIPOINT', 'ST_GEOMETRYCOLLECTION', 
	AND {bounds}
	AND product = '{product_version}'
	AND license_zone like '%{license_zone}%'
	{h3_index}
	;"""

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)

def fProcessRelationsGeomLine(extent_layer, product_version, license_zone, extentCoords, h3):
	if h3 == True:
		hextiles = fHexesFromExtent(extent_layer)
		bounds = hexListToChildString(hextiles)
		h3_index = 'AND h3_index != \'0\''
		# print(f"H3 bounds statement:\n{bounds}")
	else:
		extentStr = "'" + extentCoords + "'"
		bounds = 	f"ST_Intersects(ST_GEOMFROMWKT({extentStr}), ST_GEOMFROMWKT(geometry))"
		h3_index = ''

	sql = f"""
	-- all polygonal relations_geometry
	SELECT 
	orbis_id,
	layer_id,
	tags['type'] as tag_type,
	--aeroway, historic, 
	amenity,boundary,building,highway,landuse,leisure,man_made,military,natural,place,public_transport,railway,shop,tourism,
	members,
	--(filter(members, x -> x.role = 'from')[0]).id AS from_id,
	--(filter(members, x -> x.role = 'via')[0]).id AS via_id,
	--(filter(members, x -> x.role = 'to')[0]).id AS to_id,
	--(filter(members, x -> x.role = 'from')[0]) AS from_id,
	--(filter(members, x -> x.role = 'via')[0]) AS via_id,
	--(filter(members, x -> x.role = 'to')[0]) AS to_id,
	map_filter(mcr_tags, (key, value) -> NOT (key LIKE 'layer_id:%' OR key LIKE 'gers%' OR key LIKE 'license%' OR key LIKE 'maxspeed%' OR key LIKE 'oprod%' OR key LIKE 'source%' OR key LIKE 'supported%' OR key LIKE 'zoomlevel_min' OR key LIKE 'routing_class' OR key LIKE 'navigability' OR key LIKE 'postal_code%' OR key LIKE '%pronunciation%' )) AS mcr_clean,
	geom_type, geometry
	FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.relations_geometries
	WHERE 
	--geom_type in ('ST_POINT', 'ST_MULTIPOINT')
	geom_type in ('ST_MULTILINESTRING', 'ST_LINESTRING')
	--geom_type in ('ST_POLYGON', 'ST_MULTIPOLYGON')
	--geom_type in ('ST_MULTILINESTRING', 'ST_LINESTRING', 'ST_POINT', 'ST_POLYGON', 'ST_MULTIPOLYGON')
	--'ST_MULTIPOINT', 'ST_GEOMETRYCOLLECTION', 
	AND {bounds}
	AND product = '{product_version}'
	AND license_zone like '%{license_zone}%'
	{h3_index}
	;"""

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)

def fProcessRelationsGeomPoly(extent_layer, product_version, license_zone, extentCoords, h3):
	if h3 == True:
		hextiles = fHexesFromExtent(extent_layer)
		bounds = hexListToChildString(hextiles)
		h3_index = 'AND h3_index != \'0\''
		# print(f"H3 bounds statement:\n{bounds}")
	else:
		extentStr = "'" + extentCoords + "'"
		bounds = 	f"ST_Intersects(ST_GEOMFROMWKT({extentStr}), ST_GEOMFROMWKT(geometry))"
		h3_index = ''

	sql = f"""
	-- all relations_geometry of type 'POLYGON'
	SELECT 
	orbis_id,
	layer_id,
	tags['type'] as tag_type,
	--aeroway, historic, 
	amenity,boundary,building,highway,landuse,leisure,man_made,military,natural,place,public_transport,railway,shop,tourism,
	members,
	--(filter(members, x -> x.role = 'from')[0]).id AS from_id,
	--(filter(members, x -> x.role = 'via')[0]).id AS via_id,
	--(filter(members, x -> x.role = 'to')[0]).id AS to_id,
	--(filter(members, x -> x.role = 'from')[0]) AS from_id,
	--(filter(members, x -> x.role = 'via')[0]) AS via_id,
	--(filter(members, x -> x.role = 'to')[0]) AS to_id,
	map_filter(mcr_tags, (key, value) -> NOT (key LIKE 'layer_id:%' OR key LIKE 'gers%' OR key LIKE 'license%' OR key LIKE 'maxspeed%' OR key LIKE 'oprod%' OR key LIKE 'source%' OR key LIKE 'supported%' OR key LIKE 'zoomlevel_min' OR key LIKE 'routing_class' OR key LIKE 'navigability' OR key LIKE 'postal_code%' OR key LIKE '%pronunciation%' )) AS mcr_clean,
	geom_type, geometry
	FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.relations_geometries
	WHERE 
	--geom_type in ('ST_POINT', 'ST_MULTIPOINT')
	--geom_type in ('ST_MULTILINESTRING', 'ST_LINESTRING')
	geom_type in ('ST_POLYGON', 'ST_MULTIPOLYGON')
	--geom_type in ('ST_MULTILINESTRING', 'ST_LINESTRING', 'ST_POINT', 'ST_POLYGON', 'ST_MULTIPOLYGON')
	--'ST_MULTIPOINT', 'ST_GEOMETRYCOLLECTION', 
	AND {bounds}
	AND product = '{product_version}'
	AND license_zone like '%{license_zone}%'
	{h3_index}
	;"""

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)

def fProcessLaneConnectivity(extent_layer, product_version, license_zone, extentCoords, h3):
	if h3 == True:
		hextiles = fHexesFromExtent(extent_layer)
		bounds = hexListToChildString(hextiles)
		h3_index = 'AND h3_index != \'0\''
		# print(f"H3 bounds statement:\n{bounds}")
	else:
		extentStr = "'" + extentCoords + "'"
		bounds = 	f"ST_Intersects(ST_GEOMFROMWKT({extentStr}), ST_GEOMFROMWKT(geometry))"
		h3_index = ''

	sql = f"""
	-- lane connectivity relations (not relations_geometry) of type 'LINESTRING'
	SELECT 
	orbis_id,
	layer_id,
	tags['type'] as type,
	--(filter(members, x -> x.role = 'from')[0]).id AS from_id,
	--(filter(members, x -> x.role = 'via')[0]).id AS via_id,
	--(filter(members, x -> x.role = 'to')[0]).id AS to_id,
	(filter(members, x -> x.role = 'from')[0]) AS from_id,
	(filter(members, x -> x.role = 'via')[0]) AS via_id,
	(filter(members, x -> x.role = 'to')[0]) AS to_id,
	-- members,
	-- tags,
	mcr_tags,
	geometry
	FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.relations
	WHERE 
	geom_type = 'ST_LINESTRING'
	AND 
	tags['type'] = 'connectivity'
	AND {bounds}
	AND product = '{product_version}'
	AND license_zone like '%{license_zone}%'
	{h3_index}
	;"""

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)

def fProcessBuildingsWithParts(product_version, license_zone, extentCoords):
	extentStr = "'" + extentCoords + "'"

	sql ="""
	-- buildings with parts (OPTIMIZED - bbox computed once, filter before geometry conversion)
	-- no relations_geometry
WITH bbox AS (
	SELECT ST_GeomFromWKT({extent}) AS geom
),

polygons_filtered AS (
	SELECT
		orbis_id,
		building,
		tags,
		geometry
	FROM pu_orbis_platform_prod_catalog.map_central_repository.polygons
	WHERE (building = 'yes' OR tags['building'] IS NOT NULL OR tags['building:part'] IS NOT NULL)
	  AND product = '{product_version}'
	  AND license_zone LIKE '%{license_zone}%'
),

polygons_geom AS (
	SELECT
		orbis_id,
		building,
		tags,
		geometry,
		ST_GeomFromWKT(geometry) AS g
	FROM polygons_filtered
)

SELECT 
	p.orbis_id,
	p.tags['layer'] as layer,
	p.tags['type'] as type,
	p.tags['building'] as building,
	p.tags['building:part'] as part,
	p.tags['height'] as height,
	p.tags['min_height'] as min_height,
	p.tags['building:levels'] as levels,
	p.tags['building:min_level'] as min_level,
	p.tags['location'] as location,
	p.tags['construction'] as construction,
	p.tags['zoomlevel_min'] as zoomlevel_min,
	p.geometry
FROM polygons_geom p
CROSS JOIN bbox b
WHERE ST_Intersects(b.geom, p.g)
	""".format(product_version=product_version, license_zone=license_zone, extent=extentStr)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\n Dont forget in QGIS to remove the overlap footprints with\n\'Buildings - remove parts overlaps\'."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)

def fProcessBuildingsRel(product_version, license_zone, extentCoords):
	extentStr = "'" + extentCoords + "'"

	sql = """
-- buildings with parts 
-- include relation geometries too (relations_geometries contains assembled relation polygons/multipolygons)
SELECT 
orbis_id,
tags['layer'] as layer,
tags['type'] as type,
tags['building'] as building,
tags['building:part'] as part,
tags['height'] as height,
tags['min_height'] as min_height,
tags['building:levels'] as levels,
tags['building:min_level'] as min_level,
tags['location'] as location,
tags['construction'] as construction,
tags['zoomlevel_min'] as zoomlevel_min,
CAST(mcr_tags AS STRING) as mcr_string,
--map_filter(mcr_tags, (key, value) -> NOT (key LIKE 'layer_id:%' OR key LIKE 'gers%' OR key LIKE 'license%' OR key LIKE 'maxspeed%' OR key LIKE 'oprod%' OR key LIKE 'source%' OR key LIKE 'supported%' OR key LIKE 'zoomlevel_min' OR key LIKE 'routing_class' OR key LIKE 'navigability' OR key LIKE 'postal_code%' OR key LIKE '%pronunciation%' )) AS mcr_clean,
geometry
FROM 
pu_orbis_platform_prod_catalog.map_central_repository.polygons
WHERE 
--( building ='yes' or tags['building'] is not null)
( building ='yes' or tags['building'] is not null or tags['building:part'] is not null)
AND 
ST_Intersects(ST_GEOMFROMWKT({extent}), ST_GEOMFROMWKT(geometry)) 
AND 
product = '{product_version}'
AND
license_zone like '%{license_zone}%'

UNION

-- buildings coming from relation geometries (assembled multipolygons / polygons)
SELECT 
orbis_id,
tags['layer'] as layer,
tags['type'] as type,
tags['building'] as building,
tags['building:part'] as part,
tags['height'] as height,
tags['min_height'] as min_height,
tags['building:levels'] as levels,
tags['building:min_level'] as min_level,
tags['location'] as location,
tags['construction'] as construction,
tags['zoomlevel_min'] as zoomlevel_min,
CAST(mcr_tags AS STRING) as mcr_string,
geometry
FROM 
pu_orbis_platform_prod_catalog.map_central_repository.relations_geometries
WHERE 
-- pick only polygonal relation geometries that represent buildings
( tags['building'] is not null OR tags['building:part'] is not null )
AND
geom_type in ("ST_POLYGON","ST_MULTIPOLYGON")
AND 
ST_Intersects(ST_GEOMFROMWKT({extent}), ST_GEOMFROMWKT(geometry)) 
AND 
product = '{product_version}'
AND
license_zone like '%{license_zone}%'
	""".format(product_version=product_version, license_zone=license_zone, extent=extentStr)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\n Dont forget in QGIS to remove the overlap footprints with\n\'Buildings - remove parts overlaps\'."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fProcessBuildingsOld(product_version, license_zone, extentCoords):
	extentStr = "'" + extentCoords + "'"

	sql = """
	-- buildings
	SELECT 
	orbis_id,
	tags['height'] as height,
	tags['layer'] as layer,
	tags['location'] as location,
	tags['building:levels'] as levels, 
	tags['construction'] as construction, 
	tags['zoomlevel_min'] as zoomlevel_min,
	CAST(mcr_tags AS STRING) as mcr_string,
	--map_filter(mcr_tags, (key, value) -> NOT (key LIKE 'layer_id:%' OR key LIKE 'gers%' OR key LIKE 'license%' OR key LIKE 'maxspeed%' OR key LIKE 'oprod%' OR key LIKE 'source%' OR key LIKE 'supported%' OR key LIKE 'zoomlevel_min' OR key LIKE 'routing_class' OR key LIKE 'navigability' OR key LIKE 'postal_code%' OR key LIKE '%pronunciation%' )) AS mcr_clean,
	geometry 
	FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.polygons
	WHERE 
	( building ='yes' or tags['building'] is not null)
	AND 
	ST_Intersects(ST_GEOMFROMWKT({extent}), ST_GEOMFROMWKT(geometry)) 
	AND 
	product = '{product_version}'
	AND
	license_zone like '%{license_zone}%'

	UNION

	SELECT 
	orbis_id,
	tags['height'] as height,
	tags['layer'] as layer,
	tags['location'] as location,
	tags['building:levels'] as levels, 
	tags['construction'] as construction, 
	tags['zoomlevel_min'] as zoomlevel_min,
	CAST(mcr_tags AS STRING) as mcr_string,
	-- map_filter(mcr_tags, (key, value) -> NOT (key LIKE 'layer_id:%' OR key LIKE 'gers%' OR key LIKE 'license%' OR key LIKE 'maxspeed%' OR key LIKE 'oprod%' OR key LIKE 'source%' OR key LIKE 'supported%' OR key LIKE 'zoomlevel_min' OR key LIKE 'routing_class' OR key LIKE 'navigability' OR key LIKE 'postal_code%' OR key LIKE '%pronunciation%' )) AS mcr_clean,
	geometry 
	FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.relations_geometries
	WHERE 
	tags['building'] is not null
	AND 
	geom_type in ("ST_POLYGON","ST_MULTIPOLYGON")
	AND
	ST_Intersects(ST_GEOMFROMWKT({extent}), ST_GEOMFROMWKT(geometry)) 
	AND 
	product = '{product_version}'
	AND
	license_zone like '%{license_zone}%'
	""".format(product_version=product_version, license_zone=license_zone, extent=extentStr)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fProcWaterNatural(extent_layer, product_version, license_zone, extentCoords, polygons_table, relations_geometries_table, menu_name=None):
	"""Natural water polygons (natural=water tag) from both polygons and relations_geometries.
	Optimized query based on tested SQL - filters by natural=water before spatial operations.
	"""
	extentStr = "'" + extentCoords + "'"

	sql = f"""
	-- {menu_name if menu_name else 'Natural Water Geometry (natural=water)'}
	-- Natural Water Geometry (natural=water)
	-- Confluence-optimized: pre-parse geometries and bbox prefilter
	WITH
	q AS (
	  SELECT
	    ST_GeomFromWKT({extentStr}) AS qg,
	    ST_Envelope(ST_GeomFromWKT({extentStr})) AS qenv
	),
	polys_pre AS (
	  SELECT
	    p.*,
	    ST_GeomFromWKT(p.geometry) AS g
	  FROM {polygons_table} p
	  WHERE p.license_zone = '{license_zone}'
	    AND p.tags['natural'] = 'water'
	    AND p.element_type != 'RELATION'
	    AND p.geom_type IN ('ST_POLYGON', 'ST_MULTIPOLYGON')
	),
	polys_spatial_filtered AS (
	  SELECT
	    'polygons' AS source,
	    '{product_version}' AS product,
	    p.element_type,
	    p.osm_identifier,
	    p.license_zone,
	    p.tags,
	    p.g,
	    ST_Envelope(p.g) AS env,
	    p.geometry
	  FROM polys_pre p
	  CROSS JOIN q
	  WHERE ST_Intersects(ST_Envelope(p.g), q.qenv)
	    AND ST_Intersects(q.qg, p.g)
	),
	rels_pre AS (
	  SELECT
	    r.*,
	    ST_GeomFromWKT(r.geometry) AS g
	  FROM {relations_geometries_table} r
	  WHERE r.license_zone = '{license_zone}'
	    AND r.tags['natural'] = 'water'
	    AND r.geom_type IN ('ST_POLYGON', 'ST_MULTIPOLYGON')
	),
	rels_spatial_filtered AS (
	  SELECT
	    'relations_geometries' AS source,
	    '{product_version}' AS product,
	    r.element_type,
	    r.osm_identifier,
	    r.license_zone,
	    r.tags,
	    r.g,
	    ST_Envelope(r.g) AS env,
	    r.geometry
	  FROM rels_pre r
	  CROSS JOIN q
	  WHERE ST_Intersects(ST_Envelope(r.g), q.qenv)
	    AND ST_Intersects(q.qg, r.g)
	),
	combined_filtered AS (
	  SELECT * FROM polys_spatial_filtered
	  UNION ALL
	  SELECT * FROM rels_spatial_filtered
	)
	SELECT
	  source,
	  product,
	  element_type,
	  osm_identifier,
	  license_zone,
	  tags['natural'] AS natural,
	  tags['water'] AS water,
	  tags['intermittent'] AS intermittent,
	  tags['bridge'] AS bridge,
	  tags['tunnel'] AS tunnel,
	  tags['name'] AS name,
	  tags['alt_name'] AS alt_name,
	  CAST(tags AS STRING) AS tags,
	  geometry
	FROM combined_filtered
	ORDER BY product, source, osm_identifier
	;""".format(
		product_version=product_version,
		license_zone=license_zone,
		extentStr=extentStr,
		polygons_table=polygons_table,
		relations_geometries_table=relations_geometries_table
	)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe Water (natural=water) query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fProcBuilding_with_Relations_SpatialOptimised(product_version, license_zone, extentCoords, polygons_table, relations_table, menu_name=None):
	"""BuildingFootprints (new): Export-ready CTE that pre-parses geometries and applies envelope prefilter.
	No ordering or ROW_NUMBER is added; results are returned unordered for streamed export.
	"""
	extent = "'" + extentCoords + "'"

	sql = f"""
-- {menu_name if menu_name else 'Buildings extraction: export-only pattern with parts (no ordering)'}
-- Buildings extraction: export-only pattern with parts (no ordering)
-- Single statement that streams results for export (no ORDER / ROW_NUMBER). Run this as a single execution in DBeaver.

WITH
  q AS (SELECT ST_GeomFromWKT({extent}) AS qg, ST_Envelope(ST_GeomFromWKT({extent})) AS qenv),
  polys_src AS (
    SELECT orbis_id, license_zone, tags, building, geometry
    FROM {polygons_table}
    WHERE license_zone = '{license_zone}'
  ),
  polys_pre AS (
    SELECT p.orbis_id, p.license_zone, p.tags, p.building, p.geometry, ST_GeomFromWKT(p.geometry) AS g
    FROM polys_src p
    WHERE (p.building = 'yes' OR p.tags['building'] IS NOT NULL OR p.tags['building:part'] IS NOT NULL)
  ),
  polys_spatial_filtered AS (
    SELECT p.orbis_id, p.license_zone, p.tags, p.building, p.geometry, p.g, ST_Envelope(p.g) AS env
    FROM polys_pre p
    CROSS JOIN q
    WHERE ST_Intersects(ST_Envelope(p.g), q.qenv) AND ST_Intersects(q.qg, p.g)
  ),
  -- exploded-members approach: explode relation members to make an equi-join possible
  rel_pick AS (
    SELECT m.id AS poly_orbis_id,
           MIN(r.orbis_id) AS parent_relation_id
    FROM {relations_table} r
    JOIN polys_spatial_filtered p
      ON r.license_zone = p.license_zone
    LATERAL VIEW EXPLODE(r.members) AS m
    WHERE r.license_zone = '{license_zone}'
      AND r.geom_type IN ('ST_POLYGON','ST_MULTIPOLYGON')
      AND m.role IN ('outline','part')
      AND m.id = p.orbis_id
    GROUP BY m.id
  ),
  polygons_out AS (
    -- include both outlines and parts, expose requested properties as columns (extracted from tags)
    SELECT
      rp.parent_relation_id AS parent_relation_id,
      p.orbis_id AS orbis_id,
--      p.license_zone AS license_zone,
      p.tags AS tags,
      p.g AS g,
      CASE WHEN p.building = 'yes' THEN 'outline' WHEN p.tags['building:part'] IS NOT NULL THEN 'part' ELSE 'outline' END AS role,
--      'polygons' AS source,
      p.tags['building'] AS building,
      p.tags['building:part'] AS building_part,
      p.tags['building_group'] AS building_group,
      p.tags['height'] AS height,
      p.tags['layer'] AS layer,
      p.tags['location'] AS location,
      p.tags['construction'] AS construction,
      p.tags['extrusion'] AS extrusion,
      p.tags['roof:shape'] AS roof_shape,
      p.tags['roof:orientation'] AS roof_orientation,
      p.tags['roof:direction'] AS roof_direction,
      p.tags['height:eave'] AS height_eave,
      p.tags['min_height'] AS min_height,
      p.tags['building:min_level'] AS building_min_level,
      p.tags['building:levels'] AS building_levels,
--      map_filter(p.tags, (k,v) -> k IN ('min_height','building:levels','building:min_level','roof_levels')) AS building_properties_tags,
--      map_filter(p.tags, (k,v) -> k LIKE 'layer_id%') AS layer_identifier_tags,
--      map_filter(p.tags, (k,v) -> k LIKE 'qa%') AS qa_info_tags,
--      map_filter(p.tags, (k,v) -> k LIKE 'license%') AS license_tags,
      p.tags['osm_identifier'] AS osm_identifier
--      map_filter(p.tags, (k,v) -> k LIKE 'feedback%') AS feedback_tags,
--      p.tags['geopolitical'] AS geopolitical,
--      map_filter(p.tags, (k,v) -> (k LIKE 'name%' OR k LIKE 'abbr_name' OR k LIKE 'alt_name' OR k LIKE 'loc_name' OR k LIKE 'nickname' OR k LIKE 'official_name' OR k LIKE 'short_name' OR k LIKE 'short_alt_name' OR k LIKE 'tokenized:%')) AS internal_name_tags
    FROM polys_spatial_filtered p
    LEFT JOIN rel_pick rp ON rp.poly_orbis_id = p.orbis_id
    WHERE (p.building = 'yes' OR p.tags['building:part'] IS NOT NULL)
  )

SELECT
  parent_relation_id,
  orbis_id,
  CAST(tags AS STRING) AS tags,
  building,
  building_part,
  building_group,
  height,
  layer,
  location,
  construction,
  extrusion,
  roof_shape,
  roof_orientation,
  roof_direction,
  height_eave,
  min_height,
  building_min_level,
  building_levels,
--  building_properties_tags,
--  layer_identifier_tags,
--  qa_info_tags,
--  license_tags,
--  license_zone,
  osm_identifier,
--  feedback_tags,
--  geopolitical,
--  internal_name_tags,
  ST_ASTEXT(g) AS geometry,
  role
--  source
FROM polygons_out
;""".format(
	product_version=product_version,
	license_zone=license_zone,
	extent=extent,
	polygons_table=polygons_table,
	relations_table=relations_table
) 

	# Put script on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe BuildingFootprints (new) script is on the clipboard.\nPaste and run it in DBeaver as a single statement.\nUse Export Query (streamed) with small fetch size (~2000)."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fProcBuilding_wo_Relations_SpatialOptimised(product_version, license_zone, extentCoords, polygons_table, menu_name=None):
	"""BuildingFootprints (new): Export-ready CTE that pre-parses geometries and applies envelope prefilter.
	No ordering or ROW_NUMBER is added; results are returned unordered for streamed export.
	"""
	extent = "'" + extentCoords + "'"

	sql = f"""
-- {menu_name if menu_name else 'Buildings extraction: export-only pattern with parts (no ordering)'}
-- Buildings extraction: export-only pattern with parts (no ordering)
-- Single statement that streams results for export (no ORDER / ROW_NUMBER). Run this as a single execution in DBeaver.

WITH
  q AS (SELECT ST_GeomFromWKT({extent}) AS qg, ST_Envelope(ST_GeomFromWKT({extent})) AS qenv),
  polys_src AS (
    SELECT orbis_id, license_zone, tags, building, geometry
    FROM {polygons_table}
    WHERE license_zone = '{license_zone}'
  ),
  polys_pre AS (
    SELECT p.orbis_id, p.license_zone, p.tags, p.building, p.geometry, ST_GeomFromWKT(p.geometry) AS g
    FROM polys_src p
    WHERE (p.building = 'yes' OR p.tags['building'] IS NOT NULL OR p.tags['building:part'] IS NOT NULL)
  ),
  polys_spatial_filtered AS (
    SELECT p.orbis_id, p.license_zone, p.tags, p.building, p.geometry, p.g, ST_Envelope(p.g) AS env
    FROM polys_pre p
    CROSS JOIN q
    WHERE ST_Intersects(ST_Envelope(p.g), q.qenv) AND ST_Intersects(q.qg, p.g)
  ),
  polygons_out AS (
    -- include both outlines and parts, expose requested properties as columns (extracted from tags)
    SELECT
      NULL AS parent_relation_id,
      p.orbis_id AS orbis_id,
      p.license_zone AS license_zone,
      p.tags AS tags,
      p.g AS g,
      CASE WHEN p.building = 'yes' THEN 'outline' WHEN p.tags['building:part'] IS NOT NULL THEN 'part' ELSE 'outline' END AS role,
      'polygons' AS source,
      p.tags['building'] AS building,
      p.tags['building:part'] AS building_part,
      p.tags['building_group'] AS building_group,
      p.tags['height'] AS height,
      p.tags['layer'] AS layer,
      p.tags['location'] AS location,
      p.tags['construction'] AS construction,
      p.tags['extrusion'] AS extrusion,
      p.tags['roof:shape'] AS roof_shape,
      p.tags['roof:orientation'] AS roof_orientation,
      p.tags['roof:direction'] AS roof_direction,
      p.tags['height:eave'] AS height_eave,
      map_filter(p.tags, (k,v) -> k IN ('min_height','building:levels','building:min_level','roof_levels')) AS building_properties_tags,
      map_filter(p.tags, (k,v) -> k LIKE 'layer_id%') AS layer_identifier_tags,
      map_filter(p.tags, (k,v) -> k LIKE 'qa%') AS qa_info_tags,
      map_filter(p.tags, (k,v) -> k LIKE 'license%') AS license_tags,
      p.tags['osm_identifier'] AS osm_identifier,
      map_filter(p.tags, (k,v) -> k LIKE 'feedback%') AS feedback_tags,
      p.tags['geopolitical'] AS geopolitical,
      map_filter(p.tags, (k,v) -> (k LIKE 'name%' OR k LIKE 'abbr_name' OR k LIKE 'alt_name' OR k LIKE 'loc_name' OR k LIKE 'nickname' OR k LIKE 'official_name' OR k LIKE 'short_name' OR k LIKE 'short_alt_name' OR k LIKE 'tokenized:%')) AS internal_name_tags
    FROM polys_spatial_filtered p
    WHERE (p.building = 'yes' OR p.tags['building:part'] IS NOT NULL)
  )

SELECT
  parent_relation_id,
  orbis_id,
  CAST(tags AS STRING) AS tags,
  building,
  building_part,
  building_group,
  height,
  layer,
  location,
  construction,
  extrusion,
  roof_shape,
  roof_orientation,
  roof_direction,
  height_eave,
  building_properties_tags,
  layer_identifier_tags,
  qa_info_tags,
  license_tags,
  license_zone,
  osm_identifier,
  feedback_tags,
  geopolitical,
  internal_name_tags,
  ST_ASTEXT(g) AS geometry,
  role,
  source
FROM polygons_out
;""".format(
	product_version=product_version,
	license_zone=license_zone,
	extent=extent,
	polygons_table=polygons_table
) 

	# Put script on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe BuildingFootprints (new) script is on the clipboard.\nPaste and run it in DBeaver as a single statement.\nUse Export Query (streamed) with small fetch size (~2000)."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fProcBuildingsV2(product_version, license_zone, extentCoords, polygons_table, relations_table, relations_geometries_table, menu_name=None):
	"""Buildings v2: prefer parts when a relation has qualifying parts.

	If a relation has qualifying parts with height, emit the parts only. Otherwise emit the
	outline only. This avoids the expensive union/match step and keeps the query cheap enough
	to survive the server's patience.
	"""
	extent = "'" + extentCoords + "'"

	sql = f"""
-- {menu_name if menu_name else 'Buildings v2'}
-- Buildings v2: relation-aware building extraction with parts-first precedence
-- Rule: if parts cover the outline, emit parts and suppress the outline.

WITH
	q AS (
		SELECT ST_GeomFromWKT({extent}) AS qg,
					 ST_Envelope(ST_GeomFromWKT({extent})) AS qenv
	),

	polys_src AS (
		SELECT orbis_id, license_zone, tags, building, geometry, mcr_tags
		FROM {polygons_table}
		WHERE license_zone = '{license_zone}'
	),

	polys_pre AS (
		SELECT
			p.orbis_id,
			p.license_zone,
			p.tags,
			p.mcr_tags,
			p.building,
			p.geometry,
			ST_GeomFromWKT(p.geometry) AS g
		FROM polys_src p
		WHERE (p.building = 'yes' OR p.tags['building'] IS NOT NULL OR p.tags['building:part'] IS NOT NULL)
	),

	polys_spatial_filtered AS (
		SELECT
			p.orbis_id,
			p.license_zone,
			p.tags,
			p.mcr_tags,
			p.building,
			p.geometry,
			p.g,
			ST_Envelope(p.g) AS env
		FROM polys_pre p
		CROSS JOIN q
		WHERE ST_Intersects(ST_Envelope(p.g), q.qenv)
			AND ST_Intersects(q.qg, p.g)
	),

	rg_src AS (
		SELECT
			orbis_id,
			license_zone,
			tags AS rg_tags,
			mcr_tags AS rg_mcr_tags,
			geom_type,
			geometry
		FROM {relations_geometries_table}
		WHERE license_zone = '{license_zone}'
			AND geom_type IN ('ST_POLYGON','ST_MULTIPOLYGON')
			AND (tags['building'] IS NOT NULL OR tags['building:part'] IS NOT NULL)
	),

	rg_pre AS (
		SELECT
			r.orbis_id,
			r.license_zone,
			r.rg_tags,
			r.rg_mcr_tags,
			r.geometry,
			ST_GeomFromWKT(regexp_replace(r.geometry, '^SRID=[0-9]+;', '')) AS g
		FROM rg_src r
	),

	rels_pre AS (
		SELECT
			r.orbis_id AS rel_id,
			r.tags,
			r.mcr_tags,
			r.members,
			r.product,
			r.license_zone
		FROM {relations_table} r
		WHERE r.license_zone = '{license_zone}'
			AND (
				r.tags['building'] IS NOT NULL
				OR r.tags['building:part'] IS NOT NULL
				OR SIZE(FILTER(r.members, x -> x.role = 'outline')) > 0
				OR SIZE(FILTER(r.members, x -> x.role = 'part')) > 0
			)
	),

	rel_members AS (
		SELECT
			rel_id,
			tags,
			mcr_tags,
			CASE
				WHEN SIZE(FILTER(members, x -> x.role = 'outline')) > 0
					THEN (FILTER(members, x -> x.role = 'outline')[0]).id
				ELSE NULL
			END AS outline_member_id,
			TRANSFORM(FILTER(members, x -> x.role = 'part'), x -> x.id) AS part_ids
		FROM rels_pre
	),

	rel_member_polygon_ids AS (
		SELECT DISTINCT outline_member_id AS orbis_id
		FROM rel_members
		WHERE outline_member_id IS NOT NULL
		UNION
		SELECT DISTINCT part_id AS orbis_id
		FROM rel_members
		LATERAL VIEW EXPLODE(part_ids) exploded_parts AS part_id
	),

	parts_per_rel AS (
		SELECT
			rm.rel_id,
			p.orbis_id AS part_orbis_id,
			p.tags AS part_tags,
			p.mcr_tags AS part_mcr_tags,
			p.g AS part_g
		FROM rel_members rm
		JOIN polys_spatial_filtered p
			ON array_contains(rm.part_ids, p.orbis_id)
		WHERE p.tags['height'] IS NOT NULL
	),

	outline_geom AS (
		SELECT
			rm.rel_id,
			op.g AS outline_from_member,
			rg.g AS outline_from_relgeom,
			COALESCE(op.g, rg.g) AS outline_g,
			CASE
				WHEN op.g IS NOT NULL THEN 'polygons'
				ELSE 'relations_geometries'
			END AS outline_source
		FROM rel_members rm
		LEFT JOIN polys_spatial_filtered op
			ON op.orbis_id = rm.outline_member_id
		LEFT JOIN rg_pre rg
			ON rg.orbis_id = rm.rel_id
	),

	parts_present AS (
		SELECT DISTINCT rel_id
		FROM parts_per_rel
	),

	decision AS (
		SELECT
			o.rel_id,
			o.outline_g,
			o.outline_source,
			CASE
				WHEN pp.rel_id IS NOT NULL THEN TRUE
				ELSE FALSE
			END AS prefer_parts
		FROM outline_geom o
		LEFT JOIN parts_present pp ON pp.rel_id = o.rel_id
	),

	emit_parts AS (
		SELECT
			p.rel_id AS parent_relation_id,
			p.part_orbis_id AS orbis_id,
			p.part_tags AS tags,
			p.part_mcr_tags AS mcr_tags,
			p.part_g AS g,
			'part' AS role,
			'polygons' AS source
		FROM parts_per_rel p
		JOIN decision d
			ON d.rel_id = p.rel_id AND d.prefer_parts = TRUE
	),

	emit_outlines AS (
		SELECT
			d.rel_id AS parent_relation_id,
			d.rel_id AS orbis_id,
			r.tags AS tags,
			r.mcr_tags AS mcr_tags,
			d.outline_g AS g,
			'outline' AS role,
			d.outline_source AS source
		FROM decision d
		JOIN rels_pre r
			ON r.rel_id = d.rel_id
		WHERE d.prefer_parts = FALSE
			AND d.outline_g IS NOT NULL
	),

	standalone_polygons AS (
		SELECT
			NULL AS parent_relation_id,
			p.orbis_id AS orbis_id,
			p.tags AS tags,
			p.mcr_tags AS mcr_tags,
			p.g AS g,
			'outline' AS role,
			'polygons' AS source
		FROM polys_spatial_filtered p
		WHERE NOT EXISTS (
			SELECT 1
			FROM rel_member_polygon_ids ids
			WHERE ids.orbis_id = p.orbis_id
		)
	),

	final_rows AS (
		SELECT * FROM emit_parts
		UNION ALL
		SELECT * FROM emit_outlines
		UNION ALL
		SELECT * FROM standalone_polygons
	)

SELECT
	parent_relation_id,
	orbis_id,
	CAST(tags AS STRING) AS tags,
	tags['building'] AS building,
	tags['building:part'] AS building_part,
	tags['building_group'] AS building_group,
	tags['height'] AS height,
	tags['min_height'] AS min_height,
	tags['building:levels'] AS building_levels,
	tags['building:min_level'] AS building_min_level,
	tags['layer'] AS layer,
	tags['location'] AS location,
	tags['construction'] AS construction,
	tags['extrusion'] AS extrusion,
	tags['roof:shape'] AS roof_shape,
	tags['roof:orientation'] AS roof_orientation,
	tags['roof:direction'] AS roof_direction,
	tags['height:eave'] AS height_eave,
	tags['zoomlevel_min'] AS zoomlevel_min,
	CAST(mcr_tags AS STRING) AS mcr_string,
	tags['osm_identifier'] AS osm_identifier,
	ST_ASTEXT(g) AS geometry,
	role,
	source
FROM final_rows
;""".format(
	product_version=product_version,
	license_zone=license_zone,
	extent=extent,
	polygons_table=polygons_table,
	relations_table=relations_table,
	relations_geometries_table=relations_geometries_table
)

	# Put script on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe Buildings v2 script is on the clipboard.\nPaste and run it in DBeaver as a single statement.\nUse Export Query (streamed) with small fetch size (~2000)."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fProcLoiArtificialGround(product_version, license_zone, extentCoords, polygons_table, relations_geometries_table, menu_name=None):
	"""LOI: Artificial Ground - envelope-prefiltered extraction for polygonal LOIs."""
	extent = "'" + extentCoords + "'"

	sql = f"""
-- {menu_name if menu_name else 'LOI Artificial Ground'}
-- LOI: Artificial Ground (spatial opt)
-- Filters: product_version, license_zone, extent (WKT)
-- Uses envelope pre-filter + exact ST_Intersects for efficiency

WITH
  q AS (
    SELECT ST_GeomFromWKT({extent}) AS qg,
           ST_Envelope(ST_GeomFromWKT({extent})) AS qenv
  ),

  loi_polys_src AS (
    SELECT orbis_id, license_zone, tags, geometry
    FROM {polygons_table}
    WHERE license_zone = '{license_zone}'
      AND (
        tags['landuse'] IN ('artificial_ground','brownfield','builtup_area','construction','farmyard','garages','greenfield','landfill','quarry','railway','residential')
        OR tags['aeroway'] IN ('runway','apron','taxiway')
        OR tags['man_made'] IN ('breakwater','pier')
        OR tags['leisure'] = 'common'
      )
  ),

  loi_relgeo_src AS (
    SELECT orbis_id, license_zone, tags AS tags, geometry, geom_type
    FROM {relations_geometries_table}
    WHERE license_zone = '{license_zone}'
      AND geom_type IN ('ST_POLYGON','ST_MULTIPOLYGON')
      AND (
        tags['landuse'] IN ('artificial_ground','brownfield','builtup_area','construction','farmyard','garages','greenfield','landfill','quarry','railway','residential')
        OR tags['aeroway'] IN ('runway','apron','taxiway')
        OR tags['man_made'] IN ('breakwater','pier')
        OR tags['leisure'] = 'common'
      )
  ),

  loi_pre AS (
    SELECT orbis_id, license_zone, tags, geometry, ST_GeomFromWKT(geometry) AS g, 'polygons' AS source
    FROM loi_polys_src
    UNION ALL
    SELECT orbis_id, license_zone, tags, geometry, ST_GeomFromWKT(geometry) AS g, 'relations_geometries' AS source
    FROM loi_relgeo_src
  ),

  loi_spatial_filtered AS (
    SELECT p.orbis_id, p.license_zone, p.tags, p.geometry, p.g, ST_Envelope(p.g) AS env, p.source
    FROM loi_pre p
    CROSS JOIN q
    WHERE ST_Intersects(ST_Envelope(p.g), q.qenv)
      AND ST_Intersects(q.qg, p.g)
  ),

  loi_out AS (
    SELECT
      p.orbis_id AS orbis_id,
      p.source AS source,
      p.tags AS tags,
      p.tags['landuse'] AS landuse,
      p.tags['aeroway'] AS aeroway,
      p.tags['man_made'] AS man_made,
      p.tags['leisure'] AS leisure,
      p.tags['name'] AS name,
      p.tags['osm_identifier'] AS osm_identifier,
      ST_ASTEXT(p.g) AS geometry
    FROM loi_spatial_filtered p
  )

SELECT * FROM loi_out;
""".format(
	product_version=product_version,
	license_zone=license_zone,
	extent=extent,
	polygons_table=polygons_table,
	relations_geometries_table=relations_geometries_table
)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe LOI Artificial Ground query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fProcNetwork_wo_Relations(product_version, license_zone, extentCoords, lines_table, menu_name=None):
	"""Transportation Line extraction (envelope-prefiltered lines).

	Builds a streaming-friendly SQL query for Transportation Line features (road, rail, ferry).
	Commented out fields (reserved for v2 relation work): parent_relation_id, route, service, tracktype, electrified, sign
	Filters: product_version, license_zone, extent (WKT)
	Uses envelope pre-filter + exact ST_Intersects for efficiency
	"""
	extent = "'" + extentCoords + "'"

	sql = f"""
-- {menu_name if menu_name else 'Transportation Line Extraction'}
-- Transportation Line extraction: envelope-prefiltered, spatially filtered, relation-ready (relations fields commented out for v2)
-- Commented out fields (reserved for v2 relation work): parent_relation_id, route, service, tracktype, electrified, sign
-- Filters: product_version, license_zone, extent (WKT)

WITH
  q AS (
    SELECT ST_GeomFromWKT({extent}) AS qg,
           ST_Envelope(ST_GeomFromWKT({extent})) AS qenv
  ),

  lines_src AS (
    SELECT orbis_id, license_zone, tags, geometry
    FROM {lines_table}
    WHERE license_zone = '{license_zone}'
  ),

  lines_pre AS (
    SELECT l.orbis_id, l.license_zone, l.tags, l.geometry, ST_GeomFromWKT(l.geometry) AS g
    FROM lines_src l
    -- quick property filter: include features that look like transportation lines
    WHERE l.tags['highway'] IS NOT NULL
       OR l.tags['railway'] IS NOT NULL
       OR l.tags['route'] = 'ferry'
       OR l.tags['ferry'] IS NOT NULL
       OR l.tags['transportation'] IS NOT NULL
  ),

  lines_spatial_filtered AS (
    SELECT l.orbis_id, l.license_zone, l.tags, l.geometry, l.g, ST_Envelope(l.g) AS env
    FROM lines_pre l
    CROSS JOIN q
    WHERE ST_Intersects(ST_Envelope(l.g), q.qenv)
      AND ST_Intersects(q.qg, l.g)
  ),

  -- (relations handled in v2) -- keeping placeholder rel_pick CTE removed for now to keep query compact

  lines_out AS (
    SELECT
--      rp.parent_relation_id AS parent_relation_id, -- commented out for now; handled in v2 (parent relations)
      l.orbis_id AS orbis_id,
      l.tags AS tags,
      l.g AS g,

      -- feature-group guess
      CASE
        WHEN l.tags['highway'] IS NOT NULL THEN 'road'
        WHEN l.tags['railway'] IS NOT NULL THEN 'railway'
        WHEN l.tags['route'] = 'ferry' OR l.tags['ferry'] IS NOT NULL THEN 'ferry'
        ELSE 'transportation_line'
      END AS feature_group,

      -- commonly useful properties extracted from tags
      l.tags['name'] AS name,
      l.tags['ref'] AS ref,
      l.tags['highway'] AS highway,
      l.tags['railway'] AS railway,
--      l.tags['route'] AS route, -- commented out for v2 relation work
--      l.tags['service'] AS service, -- commented out for v2 relation work
      l.tags['oneway'] AS oneway,
      l.tags['lanes'] AS lanes,
      l.tags['layer'] AS layer,
      l.tags['maxspeed'] AS maxspeed,
      l.tags['surface'] AS surface,
--      l.tags['tracktype'] AS tracktype, -- commented out for v2 relation work
--      l.tags['electrified'] AS electrified, -- commented out for v2 relation work
      l.tags['bridge'] AS bridge,
      l.tags['tunnel'] AS tunnel,
      l.tags['routing_class'] AS routing_class,
--      l.tags['sign'] AS sign, -- commented out for v2 relation work
      l.tags['osm_identifier'] AS osm_identifier

    FROM lines_spatial_filtered l
    -- LEFT JOIN rel_pick rp ON rp.line_orbis_id = l.orbis_id -- relations omitted for v2
  )

SELECT
--  parent_relation_id, -- commented out for now; handled in v2
  orbis_id,
  CAST(tags AS STRING) AS tags,
  feature_group,
  name,
  ref,
  highway,
  railway,
--  route, -- commented out for v2
--  service, -- commented out for v2
  oneway,
  lanes,
  layer,
  maxspeed,
  surface,
--  tracktype, -- commented out for v2
--  electrified, -- commented out for v2
  bridge,
  tunnel,
  routing_class,
--  sign, -- commented out for v2
  osm_identifier,
  ST_ASTEXT(g) AS geometry
FROM lines_out;
""".format(
	product_version=product_version,
	license_zone=license_zone,
	extent=extent,
	lines_table=lines_table
)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe Transportation Line query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)

def fProcNetworkDetailed_wo_Relations(product_version, license_zone, extentCoords, lines_table, menu_name=None):
	"""Transportation Line extraction (envelope-prefiltered lines).

	Builds a streaming-friendly SQL query for Transportation Line features (road, rail, ferry).
	Includes raw tag fields `curvature:linear` and `gradient:linear`.
	Also extracts speed tags: `speed:free_flow`, `speed:week`, `speed:weekday`, `speed:weekend`. Note: tag `speed:profile_ids` may reference external speed profile records (mentioned here for later resolution).
	Elevation / vertical constraints may be present in tags (examples: `height`, `min_height`, `maxheight`, `absolute_height`, `tunnel:height`, `bridge:height`, `clearance`) — these are only mentioned here for awareness.
	-- NOTE: The following fields are currently COMMENTED OUT pending experiments and implementation of length-weighted calculations: `speed_profile_ids`, `curvature_linear`, `curvature_avg_abs`, `gradient_linear`, `gradient_avg_abs`. These require careful handling (token parsing, interval lengths) before enabling.
	TODO (vNext): compute cheap summary stats (curvature_min, curvature_avg_abs, curvature_max, gradient_min, gradient_avg_abs, gradient_max). Note: averages should be computed from absolute values to avoid sign cancellation.
	Commented out fields (reserved for v2 relation work): parent_relation_id, route, service, tracktype, electrified, sign
	Filters: product_version, license_zone, extent (WKT)
	Uses envelope pre-filter + exact ST_Intersects for efficiency
	"""
	extent = "'" + extentCoords + "'"

	sql = f"""
-- {menu_name if menu_name else 'Transportation Line Extraction'}
-- Transportation Line extraction: envelope-prefiltered, spatially filtered, relation-ready (relations fields commented out for v2)
-- Commented out fields (reserved for v2 relation work): parent_relation_id, route, service, tracktype, electrified, sign
-- Filters: product_version, license_zone, extent (WKT)

WITH
  q AS (
    SELECT ST_GeomFromWKT({extent}) AS qg,
           ST_Envelope(ST_GeomFromWKT({extent})) AS qenv
  ),

  lines_src AS (
    SELECT orbis_id, license_zone, tags, geometry
    FROM {lines_table}
    WHERE license_zone = '{license_zone}'
  ),

  lines_pre AS (
    SELECT l.orbis_id, l.license_zone, l.tags, l.geometry, ST_GeomFromWKT(l.geometry) AS g
    FROM lines_src l
    -- quick property filter: include features that look like transportation lines
    WHERE l.tags['highway'] IS NOT NULL
       OR l.tags['railway'] IS NOT NULL
       OR l.tags['route'] = 'ferry'
       OR l.tags['ferry'] IS NOT NULL
       OR l.tags['transportation'] IS NOT NULL
  ),

  lines_spatial_filtered AS (
    SELECT l.orbis_id, l.license_zone, l.tags, l.geometry, l.g, ST_Envelope(l.g) AS env
    FROM lines_pre l
    CROSS JOIN q
    WHERE ST_Intersects(ST_Envelope(l.g), q.qenv)
      AND ST_Intersects(q.qg, l.g)
  ),

  -- (relations handled in v2) -- keeping placeholder rel_pick CTE removed for now to keep query compact

  lines_out AS (
    SELECT
--      rp.parent_relation_id AS parent_relation_id, -- commented out for now; handled in v2 (parent relations)
      l.orbis_id AS orbis_id,
      l.tags AS tags,
      l.g AS g,

      -- feature-group guess
      CASE
        WHEN l.tags['highway'] IS NOT NULL THEN 'road'
        WHEN l.tags['railway'] IS NOT NULL THEN 'railway'
        WHEN l.tags['route'] = 'ferry' OR l.tags['ferry'] IS NOT NULL THEN 'ferry'
        ELSE 'transportation_line'
      END AS feature_group,

      -- commonly useful properties extracted from tags
      l.tags['name'] AS name,
      l.tags['ref'] AS ref,
      l.tags['highway'] AS highway,
      l.tags['railway'] AS railway,
--      l.tags['route'] AS route, -- commented out for v2 relation work
--      l.tags['service'] AS service, -- commented out for v2 relation work
      l.tags['oneway'] AS oneway,
      l.tags['lanes'] AS lanes,
      l.tags['dual_carriageway'] AS dual_carriageway,
      l.tags['sidewalk'] AS sidewalk,
      l.tags['layer'] AS layer,
      l.tags['maxspeed'] AS maxspeed,
      l.tags['speed:free_flow'] AS speed_free_flow,
      l.tags['speed:week'] AS speed_week,
      l.tags['speed:weekday'] AS speed_weekday,
      l.tags['speed:weekend'] AS speed_weekend,
--      l.tags['speed:profile_ids'] AS speed_profile_ids, -- COMMENTED: pending profile resolution/experiments
      l.tags['surface'] AS surface,
--      l.tags['curvature:linear'] AS curvature_linear, -- COMMENTED: pending experiments (length-weighted parsing)
--      l.tags['gradient:linear'] AS gradient_linear, -- COMMENTED: pending experiments (length-weighted parsing)
      -- cheap unweighted summary stats computed from token values (tokens like 'offset#value' or 'start-end#value')
      CASE WHEN l.tags['curvature:linear'] IS NOT NULL AND size(filter(split(l.tags['curvature:linear'],';'), x -> x <> '')) > 0 THEN
        array_min(transform(filter(split(l.tags['curvature:linear'],';'), x -> x <> ''), x -> CAST(element_at(split(x,'#'), -1) AS DOUBLE)))
      ELSE NULL END AS curvature_min,
--      CASE WHEN l.tags['curvature:linear'] IS NOT NULL AND size(filter(split(l.tags['curvature:linear'],';'), x -> x <> '')) > 0 THEN
--        aggregate(transform(filter(split(l.tags['curvature:linear'],';'), x -> x <> ''), x -> CAST(element_at(split(x,'#'), -1) AS DOUBLE)), CAST(0.0 AS DOUBLE), (acc, x) -> acc + abs(x)) / size(filter(split(l.tags['curvature:linear'],';'), x -> x <> ''))
--      ELSE NULL END AS curvature_avg_abs, -- COMMENTED: pending length-weighted experiments
      CASE WHEN l.tags['curvature:linear'] IS NOT NULL AND size(filter(split(l.tags['curvature:linear'],';'), x -> x <> '')) > 0 THEN
        array_max(transform(filter(split(l.tags['curvature:linear'],';'), x -> x <> ''), x -> CAST(element_at(split(x,'#'), -1) AS DOUBLE)))
      ELSE NULL END AS curvature_max,
      CASE WHEN l.tags['gradient:linear'] IS NOT NULL AND size(filter(split(l.tags['gradient:linear'],';'), x -> x <> '')) > 0 THEN
        array_min(transform(filter(split(l.tags['gradient:linear'],';'), x -> x <> ''), x -> CAST(element_at(split(x,'#'), -1) AS DOUBLE)))
      ELSE NULL END AS gradient_min,
--      CASE WHEN l.tags['gradient:linear'] IS NOT NULL AND size(filter(split(l.tags['gradient:linear'],';'), x -> x <> '')) > 0 THEN
--        aggregate(transform(filter(split(l.tags['gradient:linear'],';'), x -> x <> ''), x -> CAST(element_at(split(x,'#'), -1) AS DOUBLE)), CAST(0.0 AS DOUBLE), (acc, x) -> acc + abs(x)) / size(filter(split(l.tags['gradient:linear'],';'), x -> x <> ''))
--      ELSE NULL END AS gradient_avg_abs, -- COMMENTED: pending length-weighted experiments
      CASE WHEN l.tags['gradient:linear'] IS NOT NULL AND size(filter(split(l.tags['gradient:linear'],';'), x -> x <> '')) > 0 THEN
        array_max(transform(filter(split(l.tags['gradient:linear'],';'), x -> x <> ''), x -> CAST(element_at(split(x,'#'), -1) AS DOUBLE)))
      ELSE NULL END AS gradient_max,
--      l.tags['tracktype'] AS tracktype, -- commented out for v2 relation work
--      l.tags['electrified'] AS electrified, -- commented out for v2 relation work
      l.tags['bridge'] AS bridge,
      l.tags['tunnel'] AS tunnel,
      l.tags['routing_class'] AS routing_class,
--      l.tags['sign'] AS sign, -- commented out for v2 relation work
      l.tags['osm_identifier'] AS osm_identifier

    FROM lines_spatial_filtered l
    -- LEFT JOIN rel_pick rp ON rp.line_orbis_id = l.orbis_id -- relations omitted for v2
  )

SELECT
--  parent_relation_id, -- commented out for now; handled in v2
  orbis_id,
  CAST(tags AS STRING) AS tags,
  feature_group,
  name,
  ref,
  highway,
  railway,
--  route, -- commented out for v2
--  service, -- commented out for v2
  oneway,
  lanes,
  dual_carriageway,
  sidewalk,
  layer,
  maxspeed,
  speed_free_flow,
  speed_week,
  speed_weekday,
  speed_weekend,
--  speed_profile_ids, -- COMMENTED: pending profile resolution
  surface,
--  curvature_linear, -- COMMENTED: pending experiments
  curvature_min,
--  curvature_avg_abs, -- COMMENTED: pending length-weighted experiments
  curvature_max,
--  gradient_linear, -- COMMENTED: pending experiments
  gradient_min,
--  gradient_avg_abs, -- COMMENTED: pending length-weighted experiments
  gradient_max,
--  tracktype, -- commented out for v2
--  electrified, -- commented out for v2
  bridge,
  tunnel,
  routing_class,
--  sign, -- commented out for v2
  osm_identifier,
  ST_ASTEXT(g) AS geometry
FROM lines_out;
""".format(
	product_version=product_version,
	license_zone=license_zone,
	extent=extent,
	lines_table=lines_table
)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe Transportation Line query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fTurnRestrictions(product_version, license_zone, extentCoords, relations_geometries_table):
	extentStr = "'" + extentCoords + "'"

	sql = """
	SELECT 
	* 
	FROM (
		SELECT 
			orbis_id,
			EXPLODE(tags) AS (type, restriction),
			tags,
			geometry
		FROM 
		{relations_geometries_table}
		WHERE 
		tags['type']='restriction'
		AND
		geom_type in ('ST_MULTILINESTRING', 'ST_LINESTRING')
		AND 
		ST_Intersects(ST_GEOMFROMWKT({extent}), ST_GEOMFROMWKT(geometry)) 
		AND
		license_zone like '%{license_zone}%'
		) t
WHERE type LIKE 'restriction%'
""".format(
	product_version=product_version,
	license_zone=license_zone,
	extent=extentStr,
	relations_geometries_table=relations_geometries_table
)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)



def fTrafficSigns(product_version, license_zone, extentCoords, points_table):
	extentStr = "'" + extentCoords + "'"

	sql = """
	-- Traffic signs
	SELECT 
	orbis_id
	element_type ,
	geom_type ,
	tags ,
	mcr_tags ,
	layer_id ,
	name ,
	tags['traffic_sign'] as traffic_sign,
	tags['hazard'] as hazard,
	tags['maxspeed'] as maxspeed,
	geometry 
	FROM 
	{points_table}
	WHERE 
	tags['traffic_sign'] is not null
	AND 
	ST_Intersects(ST_GEOMFROMWKT({extent}), ST_GEOMFROMWKT(geometry)) 
	AND
	license_zone like '%{license_zone}%'
	""".format(
		product_version=product_version,
		license_zone=license_zone,
		extent=extentStr,
		points_table=points_table
	)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fAdminPlaces(product_version, license_zone, extentCoords, polygons_table):
	extentStr = "'" + extentCoords + "'"

	# sql = """
	# SELECT 
	# orbis_id,
	# place,
	# geometry

	# FROM 
	# pu_orbis_platform_prod_catalog.map_central_repository.polygons

	# WHERE 
	# place is not null
	# AND 
	# ST_Intersects(ST_GEOMFROMWKT({extent}), ST_GEOMFROMWKT(geometry)) 
	# AND 
	# product = '{product_version}'
	# AND
	# license_zone like '%{license_zone}%'
	# """.format(product_version=product_version, license_zone=license_zone, extent=extentStr)

	sql = """
WITH polygons_geom AS (
	SELECT *, 
		ST_GeomFromWKT(geometry) AS g,
		ST_GeomFromWKT({extent}) AS bbox
	FROM {polygons_table}
)

SELECT
orbis_id,
place,
name,
boundary,
--mcr_tags,
geometry

FROM 
polygons_geom 

WHERE 
place is not null
AND
license_zone like '%{license_zone}%'
AND
ST_Intersects(g, bbox)
""".format(
	product_version=product_version,
	license_zone=license_zone,
	extent=extentStr,
	polygons_table=polygons_table
)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)

def fProcLandUse(extent_layer, product_version, license_zone, extentCoords, polygons_table, relations_geometries_table, menu_name=None):
	"""Land use polygons (envelope-prefiltered, ST-CTE optimized).
	"""
	menu = menu_name if menu_name else 'Land Use'
	extentStr = "'" + extentCoords + "'"

	sql = """
-- {menu}
WITH q AS (
  SELECT ST_GeomFromWKT({extent}) AS qg,
         ST_Envelope(ST_GeomFromWKT({extent})) AS qenv
),
polys_src AS (
  SELECT orbis_id, tags, geometry
  FROM {polygons_table}
  WHERE geom_type IN ('ST_POLYGON','ST_MULTIPOLYGON')
    AND license_zone LIKE '%{license_zone}%'
),
polys_pre AS (
  SELECT p.orbis_id, p.tags, p.geometry,
         ST_GeomFromWKT(p.geometry) AS g,
         ST_Envelope(ST_GeomFromWKT(p.geometry)) AS env
  FROM polys_src p
  WHERE (p.tags['aeroway'] IS NOT NULL
     OR p.tags['landuse'] IS NOT NULL
     OR p.tags['leisure'] IS NOT NULL
     OR p.tags['military'] IS NOT NULL
     OR p.tags['natural'] IS NOT NULL
     OR p.tags['tourism'] IS NOT NULL
     OR p.tags['amenity'] IS NOT NULL)
),
rels_src AS (
  SELECT orbis_id, tags, geometry
  FROM {relations_geometries_table}
  WHERE geom_type IN ('ST_POLYGON','ST_MULTIPOLYGON')
    AND license_zone LIKE '%{license_zone}%'
),
rels_pre AS (
  SELECT r.orbis_id, r.tags, r.geometry,
         ST_GeomFromWKT(r.geometry) AS g,
         ST_Envelope(ST_GeomFromWKT(r.geometry)) AS env
  FROM rels_src r
  WHERE (r.tags['aeroway'] IS NOT NULL
     OR r.tags['landuse'] IS NOT NULL
     OR r.tags['leisure'] IS NOT NULL
     OR r.tags['military'] IS NOT NULL
     OR r.tags['natural'] IS NOT NULL
     OR r.tags['tourism'] IS NOT NULL
     OR r.tags['amenity'] IS NOT NULL)
)

SELECT orbis_id,
       tags['aeroway'] AS aeroway,
       tags['landuse'] AS landuse,
       tags['leisure'] AS leisure,
       tags['military'] AS military,
       tags['natural'] AS natural,
       tags['tourism'] AS tourism,
       tags['amenity'] AS amenity,
       CAST(tags AS STRING) AS tags,
       geometry
FROM polys_pre p
CROSS JOIN q
WHERE ST_Intersects(q.qenv, p.env)
  AND ST_Intersects(q.qg, p.g)

UNION

SELECT orbis_id,
       tags['aeroway'] AS aeroway,
       tags['landuse'] AS landuse,
       tags['leisure'] AS leisure,
       tags['military'] AS military,
       tags['natural'] AS natural,
       tags['tourism'] AS tourism,
       tags['amenity'] AS amenity,
       CAST(tags AS STRING) AS tags,
       geometry
FROM rels_pre r
CROSS JOIN q
WHERE ST_Intersects(q.qenv, r.env)
  AND ST_Intersects(q.qg, r.g)
;""".format(
	product_version=product_version,
	license_zone=license_zone,
	extent=extentStr,
	menu=menu,
	polygons_table=polygons_table,
	relations_geometries_table=relations_geometries_table
)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)

def fProcLandUseOrderedWip(extent_layer, product_version, license_zone, extentCoords, polygons_table, relations_geometries_table, menu_name=None):
	"""Land use polygons with ordered output and extra display columns.
	"""
	menu = menu_name if menu_name else 'Land Use (ordered wip)'
	extentStr = "'" + extentCoords + "'"

	sql = """
-- {menu}
WITH q AS (
	SELECT ST_GeomFromWKT({extent}) AS qg,
				 ST_Envelope(ST_GeomFromWKT({extent})) AS qenv
),
polys_src AS (
	SELECT orbis_id, tags, geometry
	FROM {polygons_table}
	WHERE geom_type IN ('ST_POLYGON','ST_MULTIPOLYGON')
		AND license_zone LIKE '%{license_zone}%'
),
polys_pre AS (
	SELECT p.orbis_id, p.tags, p.geometry,
				 ST_GeomFromWKT(p.geometry) AS g,
				 ST_Envelope(ST_GeomFromWKT(p.geometry)) AS env
	FROM polys_src p
	WHERE (p.tags['aeroway'] IS NOT NULL
		 OR p.tags['landuse'] IS NOT NULL
		 OR p.tags['leisure'] IS NOT NULL
		 OR p.tags['military'] IS NOT NULL
		 OR p.tags['natural'] IS NOT NULL
		 OR p.tags['tourism'] IS NOT NULL
		 OR p.tags['amenity'] IS NOT NULL)
),
rels_src AS (
	SELECT orbis_id, tags, geometry
	FROM {relations_geometries_table}
	WHERE geom_type IN ('ST_POLYGON','ST_MULTIPOLYGON')
		AND license_zone LIKE '%{license_zone}%'
),
rels_pre AS (
	SELECT r.orbis_id, r.tags, r.geometry,
				 ST_GeomFromWKT(r.geometry) AS g,
				 ST_Envelope(ST_GeomFromWKT(r.geometry)) AS env
	FROM rels_src r
	WHERE (r.tags['aeroway'] IS NOT NULL
		 OR r.tags['landuse'] IS NOT NULL
		 OR r.tags['leisure'] IS NOT NULL
		 OR r.tags['military'] IS NOT NULL
		 OR r.tags['natural'] IS NOT NULL
		 OR r.tags['tourism'] IS NOT NULL
		 OR r.tags['amenity'] IS NOT NULL)
)

SELECT orbis_id,
			 tags['aeroway'] AS aeroway,
			 tags['landuse'] AS landuse,
			 tags['leisure'] AS leisure,
			 tags['military'] AS military,
			 tags['natural'] AS natural,
			 tags['tourism'] AS tourism,
			 tags['amenity'] AS amenity,
			 tags['importance'] AS importance,
			 tags['zoomlevel_min'] AS zoomlevel_min,
			 tags['zoomlevel_max'] AS zoomlevel_max,
			 CAST(tags AS STRING) AS tags,
			 geometry
FROM polys_pre p
CROSS JOIN q
WHERE ST_Intersects(q.qenv, p.env)
	AND ST_Intersects(q.qg, p.g)

UNION

SELECT orbis_id,
			 tags['aeroway'] AS aeroway,
			 tags['landuse'] AS landuse,
			 tags['leisure'] AS leisure,
			 tags['military'] AS military,
			 tags['natural'] AS natural,
			 tags['tourism'] AS tourism,
			 tags['amenity'] AS amenity,
			 tags['importance'] AS importance,
			 tags['zoomlevel_min'] AS zoomlevel_min,
			 tags['zoomlevel_max'] AS zoomlevel_max,
			 CAST(tags AS STRING) AS tags,
			 geometry
FROM rels_pre r
CROSS JOIN q
WHERE ST_Intersects(q.qenv, r.env)
	AND ST_Intersects(q.qg, r.g)
ORDER BY
	CASE
		WHEN importance = 'international' THEN 1
		WHEN importance = 'national' THEN 2
		WHEN importance = 'regional' THEN 3
		ELSE 4
	END,
	COALESCE(CAST(zoomlevel_min AS INT), 999),
	COALESCE(CAST(zoomlevel_max AS INT), 999),
	orbis_id
;""".format(
	product_version=product_version,
	license_zone=license_zone,
	extent=extentStr,
	menu=menu,
	polygons_table=polygons_table,
	relations_geometries_table=relations_geometries_table
)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fProcessEV(product_version, license_zone, extentCoords, points_table):
	extentStr = "'" + extentCoords + "'"

	sql = """
	-- EV - just from data, cause our documentation is crap
	-- maybe this works only in GBR
	SELECT
	tags['capacity'] as capacity,
	tags['charging_when_closed'] as charging_when_closed,
	tags['opening_hours'] as opening_hours,
	tags['owner'] as owner,
	tags['parking'] as parking,
	tags['rich_content_info'] as rich_content_info,
	tags['sub_operator'] as sub_operator,
	tags['addr:street'] as addr_street ,
	tags['payment:service_provider'] as payment_service_provider,
	tags,
	geometry 
	FROM 
	{points_table}
	WHERE 
	tags['amenity']='charging_location'
	AND
	ST_Intersects(ST_GEOMFROMWKT({extent}), ST_GEOMFROMWKT(geometry)) 
	AND
	license_zone like '%{license_zone}%'
	""".format(
		product_version=product_version,
		license_zone=license_zone,
		extent=extentStr,
		points_table=points_table
	)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)

# EV hint:
# capacity = value from charging_location tag (tags['capacity']), usually site/location-level capacity metadata.
# equipment_count = computed count of distinct charging_equipment relations linked to a station in the aggregated query.
def fProcessEVDetailed(product_version, license_zone, extentCoords, points_table, relations_table):
	extentStr = "'" + extentCoords + "'"

	sql = """
	-- EV Charging (detailed)
	-- Optimized: pre-parse geometry outside predicate, explode relations once, and keep only area-relevant EV entities.
	WITH
	q AS (
		SELECT
			ST_GEOMFROMWKT({extent}) AS qg
	),
	charging_location_candidates AS (
		SELECT
			p.orbis_id AS charging_location_orbis_id,
			p.license_zone AS charging_location_license_zone,
			p.tags AS charging_location_tags,
			p.tags['name'] AS charging_location_name,
			p.tags['capacity'] AS capacity,
			p.tags['charging_when_closed'] AS charging_when_closed,
			p.tags['opening_hours'] AS opening_hours,
			p.tags['owner'] AS owner,
			p.tags['sub_operator'] AS sub_operator,
			p.tags['parking'] AS parking,
			p.tags['access'] AS access,
			p.tags['premises'] AS premises,
			p.tags['private'] AS private,
			p.tags['payment:service_provider'] AS payment_service_provider,
			p.tags['rich_content_info'] AS rich_content_info,
			p.tags['addr:street'] AS addr_street,
			p.geometry AS charging_location_geometry,
			ST_GEOMFROMWKT(p.geometry) AS charging_location_g
		FROM {points_table} p
		WHERE p.tags['amenity'] = 'charging_location'
			AND p.license_zone LIKE '%{license_zone}%'
	),
	charging_locations AS (
		SELECT
			c.charging_location_orbis_id,
			c.charging_location_license_zone,
			c.charging_location_tags,
			c.charging_location_name,
			c.capacity,
			c.charging_when_closed,
			c.opening_hours,
			c.owner,
			c.sub_operator,
			c.parking,
			c.access,
			c.premises,
			c.private,
			c.payment_service_provider,
			c.rich_content_info,
			c.addr_street,
			c.charging_location_geometry
		FROM charging_location_candidates c
		CROSS JOIN q
		WHERE ST_Intersects(q.qg, c.charging_location_g)
	),
	charging_location_ids AS (
		SELECT DISTINCT charging_location_orbis_id
		FROM charging_locations
	),
	relations_pre AS (
		SELECT
			r.orbis_id AS relation_id,
			r.license_zone AS relation_license_zone,
			r.tags AS relation_tags,
			r.members AS relation_members,
			r.tags['type'] AS relation_type
		FROM {relations_table} r
		WHERE r.tags['type'] IN ('charging_station', 'charging_equipment')
			AND r.license_zone LIKE '%{license_zone}%'
	),
	rel_members AS (
		SELECT
			r.relation_id,
			r.relation_type,
			m.role AS member_role,
			m.id AS member_id
		FROM relations_pre r
		LATERAL VIEW EXPLODE(r.relation_members) AS m
	),
	equipment_to_location AS (
		SELECT DISTINCT
			rm.relation_id AS equipment_relation_id,
			rm.member_id AS charging_location_orbis_id
		FROM rel_members rm
		WHERE rm.relation_type = 'charging_equipment'
			AND rm.member_role = 'charging_location'
			AND rm.member_id IN (SELECT charging_location_orbis_id FROM charging_location_ids)
	),
	relevant_equipment_ids AS (
		SELECT DISTINCT equipment_relation_id
		FROM equipment_to_location
	),
	station_to_equipment AS (
		SELECT DISTINCT
			rm.relation_id AS station_relation_id,
			rm.member_id AS equipment_relation_id
		FROM rel_members rm
		WHERE rm.relation_type = 'charging_station'
			AND rm.member_role = 'charging_equipment'
			AND rm.member_id IN (SELECT equipment_relation_id FROM relevant_equipment_ids)
	),
	station_to_location AS (
		SELECT DISTINCT
			rm.relation_id AS station_relation_id,
			rm.member_id AS charging_location_orbis_id
		FROM rel_members rm
		WHERE rm.relation_type = 'charging_station'
			AND rm.member_role = 'charging_location'
			AND rm.member_id IN (SELECT charging_location_orbis_id FROM charging_location_ids)
	),
	relevant_station_ids AS (
		SELECT station_relation_id AS station_relation_id
		FROM station_to_location
		UNION
		SELECT station_relation_id AS station_relation_id
		FROM station_to_equipment
	),
	station_relations AS (
		SELECT
			rp.relation_id AS station_relation_id,
			rp.relation_license_zone AS station_relation_license_zone,
			rp.relation_tags AS station_relation_tags,
			rp.relation_tags['station_id'] AS station_id
		FROM relations_pre rp
		WHERE rp.relation_type = 'charging_station'
			AND rp.relation_id IN (SELECT station_relation_id FROM relevant_station_ids)
	),
	station_to_station_location AS (
		SELECT DISTINCT
			rm.relation_id AS station_relation_id,
			rm.member_id AS station_location_orbis_id
		FROM rel_members rm
		WHERE rm.relation_type = 'charging_station'
			AND rm.member_role = 'charging_station_location'
			AND rm.relation_id IN (SELECT station_relation_id FROM relevant_station_ids)
	),
	equipment_relations AS (
		SELECT
			rp.relation_id AS equipment_relation_id,
			rp.relation_license_zone AS equipment_relation_license_zone,
			rp.relation_tags AS equipment_relation_tags,
			rp.relation_tags['evse_id'] AS evse_id,
			rp.relation_tags['evse_uid'] AS evse_uid,
			rp.relation_tags['level'] AS level,
			rp.relation_tags['authentication:rfid'] AS authentication_rfid,
			rp.relation_tags['authentication:token_group'] AS authentication_token_group,
			rp.relation_tags['charging_preferences'] AS charging_preferences,
			rp.relation_tags['payment:cards'] AS payment_cards,
			rp.relation_tags['payment:credit_cards'] AS payment_credit_cards,
			rp.relation_tags['payment:debit_cards'] AS payment_debit_cards,
			rp.relation_tags['plug_and_charge'] AS plug_and_charge,
			rp.relation_tags['remotely_controllable'] AS remotely_controllable,
			rp.relation_tags['smart_charging_profile'] AS smart_charging_profile,
			rp.relation_tags['parking_space'] AS parking_space
		FROM relations_pre rp
		WHERE rp.relation_type = 'charging_equipment'
			AND rp.relation_id IN (SELECT equipment_relation_id FROM relevant_equipment_ids)
	),
	equipment_to_charge_point AS (
		SELECT DISTINCT
			rm.relation_id AS equipment_relation_id,
			rm.member_id AS charge_point_orbis_id
		FROM rel_members rm
		WHERE rm.relation_type = 'charging_equipment'
			AND rm.member_role = 'charge_point_location'
			AND rm.relation_id IN (SELECT equipment_relation_id FROM relevant_equipment_ids)
	),
	relevant_charge_point_ids AS (
		SELECT DISTINCT charge_point_orbis_id
		FROM equipment_to_charge_point
	),
	relevant_station_location_ids AS (
		SELECT DISTINCT station_location_orbis_id
		FROM station_to_station_location
	),
	charge_point_locations AS (
		SELECT
			p.orbis_id AS charge_point_orbis_id,
			p.tags AS charge_point_tags,
			p.geometry AS charge_point_geometry
		FROM {points_table} p
		WHERE p.orbis_id IN (SELECT charge_point_orbis_id FROM relevant_charge_point_ids)
			AND p.license_zone LIKE '%{license_zone}%'
	),
	charging_station_locations AS (
		SELECT
			p.orbis_id AS station_location_orbis_id,
			p.tags AS station_location_tags,
			p.geometry AS station_location_geometry
		FROM {points_table} p
		WHERE p.orbis_id IN (SELECT station_location_orbis_id FROM relevant_station_location_ids)
			AND p.license_zone LIKE '%{license_zone}%'
	)
	SELECT
		cl.charging_location_orbis_id,
		cl.charging_location_license_zone AS license_zone,
		station_from_location.station_relation_id AS station_relation_id_from_location_member,
		ste.station_relation_id AS station_relation_id_from_equipment_member,
		COALESCE(station_from_location.station_relation_id, ste.station_relation_id) AS station_relation_id,
		er.equipment_relation_id,
		sr.station_id,
		er.evse_id,
		er.evse_uid,
		er.level,
		er.authentication_rfid,
		er.authentication_token_group,
		er.charging_preferences,
		er.payment_cards,
		er.payment_credit_cards,
		er.payment_debit_cards,
		er.plug_and_charge,
		er.remotely_controllable,
		er.smart_charging_profile,
		er.parking_space,
		map_filter(er.equipment_relation_tags, (k,v) -> k LIKE 'socket:%') AS socket_tags,
		cl.charging_location_name,
		cl.capacity,
		cl.charging_when_closed,
		cl.opening_hours,
		cl.owner,
		cl.sub_operator,
		cl.parking,
		cl.access,
		cl.premises,
		cl.private,
		cl.payment_service_provider,
		cl.rich_content_info,
		cl.addr_street,
		cl.charging_location_tags,
		sr.station_relation_tags,
		er.equipment_relation_tags,
		cpl.charge_point_orbis_id,
		cpl.charge_point_tags,
		csl.station_location_orbis_id,
		csl.station_location_tags,
		cl.charging_location_geometry AS geometry,
		cpl.charge_point_geometry,
		csl.station_location_geometry
	FROM charging_locations cl
	LEFT JOIN equipment_to_location etl
		ON etl.charging_location_orbis_id = cl.charging_location_orbis_id
	LEFT JOIN equipment_relations er
		ON er.equipment_relation_id = etl.equipment_relation_id
	LEFT JOIN station_to_equipment ste
		ON ste.equipment_relation_id = er.equipment_relation_id
	LEFT JOIN station_to_location station_from_location
		ON station_from_location.charging_location_orbis_id = cl.charging_location_orbis_id
	LEFT JOIN station_relations sr
		ON sr.station_relation_id = COALESCE(station_from_location.station_relation_id, ste.station_relation_id)
	LEFT JOIN equipment_to_charge_point etcp
		ON etcp.equipment_relation_id = er.equipment_relation_id
	LEFT JOIN charge_point_locations cpl
		ON cpl.charge_point_orbis_id = etcp.charge_point_orbis_id
	LEFT JOIN station_to_station_location stsl
		ON stsl.station_relation_id = sr.station_relation_id
	LEFT JOIN charging_station_locations csl
		ON csl.station_location_orbis_id = stsl.station_location_orbis_id
	ORDER BY
		cl.charging_location_orbis_id,
		sr.station_relation_id,
		er.equipment_relation_id
	""".format(
		product_version=product_version,
		license_zone=license_zone,
		extent=extentStr,
		points_table=points_table,
		relations_table=relations_table
	)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe EV_Charging (detailed) query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fProcessEVDetailedByStation(product_version, license_zone, extentCoords, points_table, relations_table):
	extentStr = "'" + extentCoords + "'"

	sql = """
	-- EV Charging (stations aggregated)
	-- One row per charging station relation, with aggregated EVSE and location context.
	WITH
	q AS (
		SELECT
			ST_GEOMFROMWKT({extent}) AS qg
	),
	charging_location_candidates AS (
		SELECT
			p.orbis_id AS charging_location_orbis_id,
			p.license_zone AS charging_location_license_zone,
			p.tags AS charging_location_tags,
			p.tags['name'] AS charging_location_name,
			p.geometry AS charging_location_geometry,
			ST_GEOMFROMWKT(p.geometry) AS charging_location_g
		FROM {points_table} p
		WHERE p.tags['amenity'] = 'charging_location'
			AND p.license_zone LIKE '%{license_zone}%'
	),
	charging_locations AS (
		SELECT
			c.charging_location_orbis_id,
			c.charging_location_license_zone,
			c.charging_location_name,
			c.charging_location_tags,
			c.charging_location_geometry
		FROM charging_location_candidates c
		CROSS JOIN q
		WHERE ST_Intersects(q.qg, c.charging_location_g)
	),
	charging_location_ids AS (
		SELECT DISTINCT charging_location_orbis_id
		FROM charging_locations
	),
	relations_pre AS (
		SELECT
			r.orbis_id AS relation_id,
			r.license_zone AS relation_license_zone,
			r.tags AS relation_tags,
			r.members AS relation_members,
			r.tags['type'] AS relation_type
		FROM {relations_table} r
		WHERE r.tags['type'] IN ('charging_station', 'charging_equipment')
			AND r.license_zone LIKE '%{license_zone}%'
	),
	rel_members AS (
		SELECT
			r.relation_id,
			r.relation_type,
			m.role AS member_role,
			m.id AS member_id
		FROM relations_pre r
		LATERAL VIEW EXPLODE(r.relation_members) AS m
	),
	equipment_to_location AS (
		SELECT DISTINCT
			rm.relation_id AS equipment_relation_id,
			rm.member_id AS charging_location_orbis_id
		FROM rel_members rm
		WHERE rm.relation_type = 'charging_equipment'
			AND rm.member_role = 'charging_location'
			AND rm.member_id IN (SELECT charging_location_orbis_id FROM charging_location_ids)
	),
	relevant_equipment_ids AS (
		SELECT DISTINCT equipment_relation_id
		FROM equipment_to_location
	),
	station_to_equipment AS (
		SELECT DISTINCT
			rm.relation_id AS station_relation_id,
			rm.member_id AS equipment_relation_id
		FROM rel_members rm
		WHERE rm.relation_type = 'charging_station'
			AND rm.member_role = 'charging_equipment'
			AND rm.member_id IN (SELECT equipment_relation_id FROM relevant_equipment_ids)
	),
	station_to_location AS (
		SELECT DISTINCT
			rm.relation_id AS station_relation_id,
			rm.member_id AS charging_location_orbis_id
		FROM rel_members rm
		WHERE rm.relation_type = 'charging_station'
			AND rm.member_role = 'charging_location'
			AND rm.member_id IN (SELECT charging_location_orbis_id FROM charging_location_ids)
	),
	relevant_station_ids AS (
		SELECT station_relation_id AS station_relation_id
		FROM station_to_location
		UNION
		SELECT station_relation_id AS station_relation_id
		FROM station_to_equipment
	),
	station_relations AS (
		SELECT
			rp.relation_id AS station_relation_id,
			rp.relation_license_zone AS station_relation_license_zone,
			rp.relation_tags AS station_relation_tags,
			rp.relation_tags['station_id'] AS station_id
		FROM relations_pre rp
		WHERE rp.relation_type = 'charging_station'
			AND rp.relation_id IN (SELECT station_relation_id FROM relevant_station_ids)
	),
	station_to_station_location AS (
		SELECT DISTINCT
			rm.relation_id AS station_relation_id,
			rm.member_id AS station_location_orbis_id
		FROM rel_members rm
		WHERE rm.relation_type = 'charging_station'
			AND rm.member_role = 'charging_station_location'
			AND rm.relation_id IN (SELECT station_relation_id FROM relevant_station_ids)
	),
	equipment_relations AS (
		SELECT
			rp.relation_id AS equipment_relation_id,
			rp.relation_tags AS equipment_relation_tags,
			rp.relation_tags['evse_id'] AS evse_id,
			rp.relation_tags['evse_uid'] AS evse_uid,
			rp.relation_tags['level'] AS level,
			rp.relation_tags['authentication:rfid'] AS authentication_rfid,
			rp.relation_tags['authentication:token_group'] AS authentication_token_group,
			rp.relation_tags['charging_preferences'] AS charging_preferences,
			rp.relation_tags['payment:cards'] AS payment_cards,
			rp.relation_tags['payment:credit_cards'] AS payment_credit_cards,
			rp.relation_tags['payment:debit_cards'] AS payment_debit_cards,
			rp.relation_tags['plug_and_charge'] AS plug_and_charge,
			rp.relation_tags['remotely_controllable'] AS remotely_controllable,
			rp.relation_tags['smart_charging_profile'] AS smart_charging_profile,
			rp.relation_tags['parking_space'] AS parking_space
		FROM relations_pre rp
		WHERE rp.relation_type = 'charging_equipment'
			AND rp.relation_id IN (SELECT equipment_relation_id FROM relevant_equipment_ids)
	),
	equipment_to_charge_point AS (
		SELECT DISTINCT
			rm.relation_id AS equipment_relation_id,
			rm.member_id AS charge_point_orbis_id
		FROM rel_members rm
		WHERE rm.relation_type = 'charging_equipment'
			AND rm.member_role = 'charge_point_location'
			AND rm.relation_id IN (SELECT equipment_relation_id FROM relevant_equipment_ids)
	),
	relevant_station_location_ids AS (
		SELECT DISTINCT station_location_orbis_id
		FROM station_to_station_location
	),
	charging_station_locations AS (
		SELECT
			p.orbis_id AS station_location_orbis_id,
			p.geometry AS station_location_geometry
		FROM {points_table} p
		WHERE p.orbis_id IN (SELECT station_location_orbis_id FROM relevant_station_location_ids)
			AND p.license_zone LIKE '%{license_zone}%'
	),
	station_location_agg AS (
		SELECT
			stl.station_relation_id,
			COUNT(DISTINCT stl.charging_location_orbis_id) AS charging_location_count,
			CONCAT_WS(',', SORT_ARRAY(COLLECT_SET(CAST(stl.charging_location_orbis_id AS STRING)))) AS charging_location_ids,
			CONCAT_WS(' | ', SORT_ARRAY(COLLECT_SET(cl.charging_location_name))) AS charging_location_names,
			MAX(cl.charging_location_geometry) AS sample_charging_location_geometry
		FROM station_to_location stl
		LEFT JOIN charging_locations cl
			ON cl.charging_location_orbis_id = stl.charging_location_orbis_id
		GROUP BY stl.station_relation_id
	),
	station_equipment_agg AS (
		SELECT
			ste.station_relation_id,
			COUNT(DISTINCT ste.equipment_relation_id) AS equipment_count,
			COUNT(DISTINCT etcp.charge_point_orbis_id) AS charge_point_count,
			CONCAT_WS(',', SORT_ARRAY(COLLECT_SET(CAST(ste.equipment_relation_id AS STRING)))) AS equipment_relation_ids,
			CONCAT_WS(',', SORT_ARRAY(COLLECT_SET(er.evse_id))) AS evse_ids,
			CONCAT_WS(',', SORT_ARRAY(COLLECT_SET(er.evse_uid))) AS evse_uids,
			CONCAT_WS(',', SORT_ARRAY(COLLECT_SET(CAST(er.level AS STRING)))) AS evse_levels,
			CONCAT_WS(',', SORT_ARRAY(COLLECT_SET(er.authentication_rfid))) AS authentication_rfid_values,
			CONCAT_WS(',', SORT_ARRAY(COLLECT_SET(er.authentication_token_group))) AS authentication_token_group_values,
			CONCAT_WS(',', SORT_ARRAY(COLLECT_SET(er.charging_preferences))) AS charging_preferences_values,
			CONCAT_WS(',', SORT_ARRAY(COLLECT_SET(er.payment_cards))) AS payment_cards_values,
			CONCAT_WS(',', SORT_ARRAY(COLLECT_SET(er.payment_credit_cards))) AS payment_credit_cards_values,
			CONCAT_WS(',', SORT_ARRAY(COLLECT_SET(er.payment_debit_cards))) AS payment_debit_cards_values,
			CONCAT_WS(',', SORT_ARRAY(COLLECT_SET(er.plug_and_charge))) AS plug_and_charge_values,
			CONCAT_WS(',', SORT_ARRAY(COLLECT_SET(er.remotely_controllable))) AS remotely_controllable_values,
			CONCAT_WS(',', SORT_ARRAY(COLLECT_SET(er.smart_charging_profile))) AS smart_charging_profile_values,
			CONCAT_WS(',', SORT_ARRAY(COLLECT_SET(er.parking_space))) AS parking_space_values
		FROM station_to_equipment ste
		LEFT JOIN equipment_relations er
			ON er.equipment_relation_id = ste.equipment_relation_id
		LEFT JOIN equipment_to_charge_point etcp
			ON etcp.equipment_relation_id = ste.equipment_relation_id
		GROUP BY ste.station_relation_id
	),
	station_point_agg AS (
		SELECT
			stsl.station_relation_id,
			COUNT(DISTINCT stsl.station_location_orbis_id) AS station_location_point_count,
			CONCAT_WS(',', SORT_ARRAY(COLLECT_SET(CAST(stsl.station_location_orbis_id AS STRING)))) AS station_location_orbis_ids,
			MAX(csl.station_location_geometry) AS station_location_geometry
		FROM station_to_station_location stsl
		LEFT JOIN charging_station_locations csl
			ON csl.station_location_orbis_id = stsl.station_location_orbis_id
		GROUP BY stsl.station_relation_id
	)
	SELECT
		sr.station_relation_id,
		sr.station_relation_license_zone AS license_zone,
		sr.station_id,
		sla.charging_location_count,
		sla.charging_location_ids,
		sla.charging_location_names,
		sea.equipment_count,
		sea.charge_point_count,
		sea.equipment_relation_ids,
		sea.evse_ids,
		sea.evse_uids,
		sea.evse_levels,
		sea.authentication_rfid_values,
		sea.authentication_token_group_values,
		sea.charging_preferences_values,
		sea.payment_cards_values,
		sea.payment_credit_cards_values,
		sea.payment_debit_cards_values,
		sea.plug_and_charge_values,
		sea.remotely_controllable_values,
		sea.smart_charging_profile_values,
		sea.parking_space_values,
		spa.station_location_point_count,
		spa.station_location_orbis_ids,
		sr.station_relation_tags,
		COALESCE(spa.station_location_geometry, sla.sample_charging_location_geometry) AS geometry
	FROM station_relations sr
	LEFT JOIN station_location_agg sla
		ON sla.station_relation_id = sr.station_relation_id
	LEFT JOIN station_equipment_agg sea
		ON sea.station_relation_id = sr.station_relation_id
	LEFT JOIN station_point_agg spa
		ON spa.station_relation_id = sr.station_relation_id
	ORDER BY sr.station_relation_id
	""".format(
		product_version=product_version,
		license_zone=license_zone,
		extent=extentStr,
		points_table=points_table,
		relations_table=relations_table
	)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe EV_Charging (stations aggregated) query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)

def fProcessFireStations(product_version, license_zone, extentCoords, points_table):
	extentStr = "'" + extentCoords + "'"

	sql = """
	-- Fire Stations
	SELECT
	orbis_id,
	amenity,
	z_order,
	geometry 
	FROM 
	{points_table}
	WHERE 
	amenity='fire_station'
	AND
	ST_Intersects(ST_GEOMFROMWKT({extent}), ST_GEOMFROMWKT(geometry)) 
	AND
	license_zone like '%{license_zone}%'
	""".format(
		product_version=product_version,
		license_zone=license_zone,
		extent=extentStr,
		points_table=points_table
	)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)

def hexListToChildString(h3_hex_ids):
	result = "(\n"
	result += " OR \n".join([f"\th3_ischildof(h3_index,'{hex_id}')" for hex_id in h3_hex_ids])
	result += "\n)"
	return result

def fProcessBuildingsWithPartsH3(extent_layer, product_version, license_zone, extentCoords):
	"""Buildings query using native Databricks H3 functions (Option 1).
	Uses h3_polyfillash3string to generate tiles server-side - much faster than VALUES CTE.
	"""
	extentStr = "'" + extentCoords + "'"
	
	sql = f"""
	-- buildings with parts (H3 native server-side computation with k-ring buffer)
	-- Uses h3_polyfillash3string + h3_kring to avoid missing edge geometries
WITH bbox AS (
	SELECT ST_GEOMFROMWKT({extentStr}) AS g
),
bbox_h3_base AS (
	-- Generate base H3 tiles at resolution 8 from bbox polygon
	SELECT explode(h3_polyfillash3string(ST_ASWKT(bbox.g), 8)) AS h3_tile
	FROM bbox
),
bbox_h3_tiles AS (
	-- Expand with k-ring=1 to capture edge hexagons
	SELECT DISTINCT explode(h3_kring(h3_tile, 1)) AS h3_tile
	FROM bbox_h3_base
),
polygons_filtered AS (
	SELECT
		p.orbis_id,
		p.building,
		p.tags,
		p.geometry,
		p.h3_index,
		p.h3_resolution
	FROM pu_orbis_platform_prod_catalog.map_central_repository.polygons p
	WHERE (p.building = 'yes' OR p.tags['building'] IS NOT NULL OR p.tags['building:part'] IS NOT NULL)
	  AND p.product = '{product_version}'
	  AND p.license_zone LIKE '%{license_zone}%'
	  AND p.h3_index != '0'
)
SELECT 
	p.orbis_id,
	p.tags['layer'] as layer,
	p.tags['type'] as type,
	p.tags['building'] as building,
	p.tags['building:part'] as part,
	p.tags['height'] as height,
	p.tags['min_height'] as min_height,
	p.tags['building:levels'] as levels,
	p.tags['building:min_level'] as min_level,
	p.tags['location'] as location,
	p.tags['construction'] as construction,
	p.tags['zoomlevel_min'] as zoomlevel_min,
	p.geometry
FROM polygons_filtered p
INNER JOIN bbox_h3_tiles h ON (
	-- Match at resolution 8
	(p.h3_resolution = 8 AND p.h3_index = h.h3_tile)
	OR
	-- Match at lower resolutions: polygon is a parent of bbox tile
	(p.h3_resolution < 8 AND p.h3_index = h3_toparent(h.h3_tile, p.h3_resolution))
	OR
	-- Match at higher resolutions: convert polygon to parent at res 8
	(p.h3_resolution > 8 AND h3_toparent(p.h3_index, 8) = h.h3_tile)
)
	"""
	
	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)
	
	message = """H3 native query is on the clipboard!\n\nUses server-side h3_polyfillash3string - should be much faster.\n\nPaste and run it from DBeaver."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fBuildingsSimple_H3(extent_layer,product_version, license_zone, extentCoords, h3):
	if h3 == True:
		hextiles = fHexesFromExtent(extent_layer)
		bounds = hexListToChildString(hextiles)
		# print(f"H3 bounds statement:\n{bounds}")
	else:
		extentStr = "'" + extentCoords + "'"
		bounds = 	f"ST_Intersects(ST_GEOMFROMWKT({extentStr}), ST_GEOMFROMWKT(geometry))"

	sql = f"""
	SELECT  * 
	FROM pu_orbis_platform_prod_catalog.map_central_repository.polygons 
	WHERE   
		license_zone='{license_zone}' 
		AND building is not null 
		AND {bounds}
		AND h3_index != '0'
		AND product = '{product_version}';
	"""
	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fGetBoundingPolygon(extent_layer):
	"""Get the bounding box WKT polygon, print it, and copy to clipboard"""
	
	# Reproject to WGS84 (EPSG:4326) if needed
	target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
	
	if extent_layer.crs() != target_crs:
		# Reproject using processing
		params = {
			'INPUT': extent_layer,
			'TARGET_CRS': target_crs,
			'OUTPUT': 'memory:'
		}
		result = processing.run("native:reprojectlayer", params)
		wgs_layer = result['OUTPUT']
	else:
		wgs_layer = extent_layer
	
	# Get extent in WGS84
	extent = wgs_layer.extent()
	xmin = extent.xMinimum()
	xmax = extent.xMaximum()
	ymin = extent.yMinimum()
	ymax = extent.yMaximum()
	
	# Create WKT polygon (closed ring)
	wkt_polygon = f"POLYGON(({xmin} {ymin}, {xmin} {ymax}, {xmax} {ymax}, {xmax} {ymin}, {xmin} {ymin}))"
	
	# Print to console
	print("\n======= Bounding Polygon WKT =======")
	print(wkt_polygon)
	print("====================================\n")
	
	# Copy to clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(wkt_polygon)
	
	message = """Bounding polygon WKT copied to clipboard!\n\nYou can now paste it into your SQL queries."""
	qtMsgBox(message)


def fHexesFromExtent(extent_layer):
	# Adapted from 2021 matt wilkie <maphew@gmail.com>
	geographic_coordsys = "EPSG:4326"  # e.g. WGS84, NAD83(CSRS)
	#output_projection = "EPSG:3579"  # placeholder, not currently used
	# output_projection = "EPSG:3857"  # placeholder, not currently used
	debug = False

	def proj_to_geo(layer_proj):
	# def proj_to_geo(in_layer):
			"""Project to geographic coordinate system, in memory.
			H3 needs all coordinates in decimal degrees"""
			params = {
					"INPUT": layer_proj,
					"TARGET_CRS": geographic_coordsys,
					"OUTPUT": "memory:dd_",
			}
			geo_lyr = processing.run("native:reprojectlayer", params)["OUTPUT"]
			if debug:
					QgsProject.instance().addMapLayer(geo_lyr)
			return geo_lyr

	def poly_from_extent(layer):
			ext = layer.extent()
			xmin = ext.xMinimum()
			xmax = ext.xMaximum()
			ymin = ext.yMinimum()
			ymax = ext.yMaximum()
			return [(xmin, ymax), (xmax, ymax), (xmax, ymin), (xmin, ymin)]

	layer = proj_to_geo(extent_layer)
	ext_poly = poly_from_extent(layer)
	# Convert to format expected by h3: [[lat1, lng1], [lat2, lng2], ...]
	# polygon = [[p[1], p[0]] for p in ext_poly]  # swap to lat,lng order
	hex_ids = set()

	h3resolution=config['mcr']['h3resolution']
		
	# Input item from drop down list
	h3levels=["2","3","4","5","6","7","8","9"] 
	index = h3levels.index(h3resolution) if h3resolution in h3levels else 0
	h3level, ok = QInputDialog.getItem(iface.mainWindow(), "Select h3 level:", "H3 levels", h3levels, index, False)
	if ok:
		config['mcr']['h3resolution'] = h3level
		with open(iniFile, 'w') as configfile:
			config.write(configfile)
		print(f"H3 resolution level: {h3level}")
		level = int(h3level)
	else:
		print(f"H3 Cancelled")
		return "cancel"

	# Get the bounding box and create a grid of points
	min_lat = min(p[1] for p in ext_poly)
	max_lat = max(p[1] for p in ext_poly)
	min_lng = min(p[0] for p in ext_poly)
	max_lng = max(p[0] for p in ext_poly)
	
	# Calculate step size based on resolution level (rough approximation)
	step = max(0.001, (max_lat - min_lat) / (level*10))  # adjust step size based on extent
	
	# Sample points within the bounding box
	lat = min_lat
	while lat <= max_lat:
			lng = min_lng
			while lng <= max_lng:
					hex_ids.add(h3.latlng_to_cell(lat, lng, level))
					lng += step
			lat += step
	
	print(f"Hex IDs within extent poly: {str(len(hex_ids))}")
	# print(f"Hex IDs list: {hex_ids}")
	return hex_ids


def fMainUI():
	print("Connecting to databricks")
	cursor = connection.cursor()
	cursor.execute("SELECT product, ingestion_date FROM pu_orbis_platform_prod_catalog.map_central_repository.available_products")
	fetched = cursor.fetchall()
	product_versions = [row[0] for row in fetched]
	product_versions.sort(reverse=True)
	mcr_table_names = fGetMcrTableNames(cursor)
	print(f"Loaded {len(mcr_table_names)} tables from map_central_repository")

	# Resolve an existing polygons table for license zone list (legacy base table may not exist).
	last_product_version = config['mcr']['last_product_version']
	if last_product_version in product_versions:
		license_zone_seed_product = last_product_version
	elif product_versions:
		license_zone_seed_product = product_versions[0]
	else:
		license_zone_seed_product = ""

	license_zone_table = fResolveMcrVersionedTable(mcr_table_names, 'polygons', license_zone_seed_product)
	if not license_zone_table:
		polygon_like_tables = sorted(
			[t for t in mcr_table_names if t == 'polygons' or t.startswith('polygons_')]
		)
		if polygon_like_tables:
			license_zone_table = f"pu_orbis_platform_prod_catalog.map_central_repository.{polygon_like_tables[-1]}"

	if not license_zone_table:
		message = "\nCould not find any polygons table in map_central_repository to load license zones."
		print(message)
		qtMsgBox(message)
		return

	print(f"Loading license zones from: {license_zone_table}")
	cursor.execute(f"SELECT distinct license_zone FROM {license_zone_table}")
	fetched = cursor.fetchall()
	license_zones_polygon = [row[0] for row in fetched if len(row[0])==3]
	license_zones_polygon.sort(reverse=False)


	OGRLayers, OGRLayerNames, extent_layer_index = fSelectExtentLayer()

	print("Showing UI")
	process_list=[
	'Get bounding POLYGON',
	'--',
	'All Polygons Contain',
	'All Polygons Intersect',
	'--',
	'Admin Areas',
	'Admin Areas by name',
	'Admin Point Places',
	'Admin Places (polygon)',
	'Water (natural)',
	'Inland Water',
	'Ocean Water',
	'Buildings with Relations Optimised',
	'Buildings v2',
	'Buildings w/o Relations Optimised',
	'Land Use (older)',
	'Land Use (ordered wip)',
	'LOI Artificial Ground',
	'Network wo Relations',
	'Network Detailed wo Relations',
	'Network Major with Lanes, Curv, Grad (older)',
	'Network Simple (for large areas, older)',
	'--',
	'Turn Restrictions',
	'Fire Stations',
		'Street Lamps (h3)',
		'Traffic Signs',
		'EV_Charging',
		'EV_Charging (detailed)',
		'EV_Charging (stations aggregated)',
		'Overture Buildings (external)',
		'--',
	'Buildings with parts',
	'Buildings with parts H3',
	'Buildings with relations',
	'Buildings (Old)',
	'Network with Speeds',
	'Network Elevation (h3)',
	'Network Junctions (h3)',
	'--',
	'All relations WIP (not relation_geometry) (linestring) (h3)',
	'Relations-Geometry (point) (h3)',
	'Relations-Geometry (line) (h3)',
	'Relations-Geometry (polygon) (h3)',
	'Lane Connectivity relations (h3)',
	'--',
	'Trees - use dbHIP',
	'--',
	'BuildingsSimple (h3)',
	'Draw H3 tiles',
	'List H3 tiles',
	'-----------',
	'Everything Ways',
	'Everything Roads',
	'Everything Rels',
	'Everything Nodes',
	'Everything Lines',
	'Everything Points',
	'Address Points OLD',
	'Address Routing Nodes OLD',
	'Address ADP Rels',
	'Address RP Rels',
	'Turn Restriction Rels',
	]


	result = fMCR_Dialog(product_versions, process_list, license_zones_polygon, OGRLayerNames, extent_layer_index)
	if result=='cancel':
		process="Exit"
	else:
		print(f"fMCR_Dialog result: {result}")

	product_version = result[0]
	process = result[1]
	license_zone = result[2]
	extent_layer = OGRLayers[result[4]]
	extentCoords = fGetExtentPolygonCoords(extent_layer)
	h3str = result[5]
	if h3str.lower() == "true":
		h3 = True
	else:
		h3 = False
	print(f"h3 is {h3}")




	if process == 'Get bounding POLYGON':
		fGetBoundingPolygon(extent_layer)

	elif process == 'Water (natural)':
		water_polygons_table = fResolveMcrVersionedTableExact(mcr_table_names, 'polygons', product_version)
		water_relations_geometries_table = fResolveMcrVersionedTableExact(mcr_table_names, 'relations_geometries', product_version)
		if not water_polygons_table or not water_relations_geometries_table:
			available_polygons = sorted([t for t in mcr_table_names if t.startswith('polygons_')])
			available_rel_geoms = sorted([t for t in mcr_table_names if t.startswith('relations_geometries_')])
			expected_polygons = f"polygons_{_normalize_product_version_for_table(product_version)}"
			expected_rel_geoms = f"relations_geometries_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned tables found for selected product '{product_version}'.\n"
				f"Expected polygons table: {expected_polygons}\n"
				f"Expected relations_geometries table: {expected_rel_geoms}\n\n"
				f"Available polygons_* tables:\n{chr(10).join(available_polygons) if available_polygons else '(none)'}\n\n"
				f"Available relations_geometries_* tables:\n{chr(10).join(available_rel_geoms) if available_rel_geoms else '(none)'}\n\n"
				"Please select a product version that has matching tables."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"Water (natural) tables for '{product_version}': "
			f"polygons={water_polygons_table}, "
			f"relations_geometries={water_relations_geometries_table}"
		)
		fProcWaterNatural(
			extent_layer,
			product_version,
			license_zone,
			extentCoords,
			water_polygons_table,
			water_relations_geometries_table,
			menu_name=process
		)
	elif process == 'Land Use (older)':
		landuse_polygons_table = fResolveMcrVersionedTableExact(mcr_table_names, 'polygons', product_version)
		landuse_relations_geometries_table = fResolveMcrVersionedTableExact(mcr_table_names, 'relations_geometries', product_version)
		if not landuse_polygons_table or not landuse_relations_geometries_table:
			available_polygons = sorted([t for t in mcr_table_names if t.startswith('polygons_')])
			available_rel_geoms = sorted([t for t in mcr_table_names if t.startswith('relations_geometries_')])
			expected_polygons = f"polygons_{_normalize_product_version_for_table(product_version)}"
			expected_rel_geoms = f"relations_geometries_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned tables found for selected product '{product_version}'.\n"
				f"Expected polygons table: {expected_polygons}\n"
				f"Expected relations_geometries table: {expected_rel_geoms}\n\n"
				f"Available polygons_* tables:\n{chr(10).join(available_polygons) if available_polygons else '(none)'}\n\n"
				f"Available relations_geometries_* tables:\n{chr(10).join(available_rel_geoms) if available_rel_geoms else '(none)'}\n\n"
				"Please select a product version that has matching tables."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"Land Use (older) tables for '{product_version}': "
			f"polygons={landuse_polygons_table}, "
			f"relations_geometries={landuse_relations_geometries_table}"
		)
		fProcLandUse(
			extent_layer,
			product_version,
			license_zone,
			extentCoords,
			landuse_polygons_table,
			landuse_relations_geometries_table,
			menu_name=process
		)
	elif process == 'Land Use (ordered wip)':
		landuse_polygons_table = fResolveMcrVersionedTableExact(mcr_table_names, 'polygons', product_version)
		landuse_relations_geometries_table = fResolveMcrVersionedTableExact(mcr_table_names, 'relations_geometries', product_version)
		if not landuse_polygons_table or not landuse_relations_geometries_table:
			available_polygons = sorted([t for t in mcr_table_names if t.startswith('polygons_')])
			available_rel_geoms = sorted([t for t in mcr_table_names if t.startswith('relations_geometries_')])
			expected_polygons = f"polygons_{_normalize_product_version_for_table(product_version)}"
			expected_rel_geoms = f"relations_geometries_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned tables found for selected product '{product_version}'.\n"
				f"Expected polygons table: {expected_polygons}\n"
				f"Expected relations_geometries table: {expected_rel_geoms}\n\n"
				f"Available polygons_* tables:\n{chr(10).join(available_polygons) if available_polygons else '(none)'}\n\n"
				f"Available relations_geometries_* tables:\n{chr(10).join(available_rel_geoms) if available_rel_geoms else '(none)'}\n\n"
				"Please select a product version that has matching tables."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"Land Use (ordered wip) tables for '{product_version}': "
			f"polygons={landuse_polygons_table}, "
			f"relations_geometries={landuse_relations_geometries_table}"
		)
		fProcLandUseOrderedWip(
			extent_layer,
			product_version,
			license_zone,
			extentCoords,
			landuse_polygons_table,
			landuse_relations_geometries_table,
			menu_name=process
		)
	elif process == 'LOI Artificial Ground':
		loi_polygons_table = fResolveMcrVersionedTableExact(mcr_table_names, 'polygons', product_version)
		loi_relations_geometries_table = fResolveMcrVersionedTableExact(mcr_table_names, 'relations_geometries', product_version)
		if not loi_polygons_table or not loi_relations_geometries_table:
			available_polygons = sorted([t for t in mcr_table_names if t.startswith('polygons_')])
			available_rel_geoms = sorted([t for t in mcr_table_names if t.startswith('relations_geometries_')])
			expected_polygons = f"polygons_{_normalize_product_version_for_table(product_version)}"
			expected_rel_geoms = f"relations_geometries_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned tables found for selected product '{product_version}'.\n"
				f"Expected polygons table: {expected_polygons}\n"
				f"Expected relations_geometries table: {expected_rel_geoms}\n\n"
				f"Available polygons_* tables:\n{chr(10).join(available_polygons) if available_polygons else '(none)'}\n\n"
				f"Available relations_geometries_* tables:\n{chr(10).join(available_rel_geoms) if available_rel_geoms else '(none)'}\n\n"
				"Please select a product version that has matching tables."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"LOI Artificial Ground tables for '{product_version}': "
			f"polygons={loi_polygons_table}, "
			f"relations_geometries={loi_relations_geometries_table}"
		)
		fProcLoiArtificialGround(
			product_version,
			license_zone,
			extentCoords,
			loi_polygons_table,
			loi_relations_geometries_table,
			menu_name=process
		)
	elif process == 'Buildings with Relations Optimised':
		buildings_polygons_table = fResolveMcrVersionedTableExact(mcr_table_names, 'polygons', product_version)
		buildings_relations_table = fResolveMcrVersionedTableExact(mcr_table_names, 'relations', product_version)
		if not buildings_polygons_table or not buildings_relations_table:
			available_polygons = sorted([t for t in mcr_table_names if t.startswith('polygons_')])
			available_relations = sorted([t for t in mcr_table_names if t.startswith('relations_') and not t.startswith('relations_geometries_')])
			expected_polygons = f"polygons_{_normalize_product_version_for_table(product_version)}"
			expected_relations = f"relations_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned tables found for selected product '{product_version}'.\n"
				f"Expected polygons table: {expected_polygons}\n"
				f"Expected relations table: {expected_relations}\n\n"
				f"Available polygons_* tables:\n{chr(10).join(available_polygons) if available_polygons else '(none)'}\n\n"
				f"Available relations_* tables:\n{chr(10).join(available_relations) if available_relations else '(none)'}\n\n"
				"Please select a product version that has matching tables."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"Buildings with Relations Optimised tables for '{product_version}': "
			f"polygons={buildings_polygons_table}, "
			f"relations={buildings_relations_table}"
		)
		fProcBuilding_with_Relations_SpatialOptimised(
			product_version,
			license_zone,
			extentCoords,
			buildings_polygons_table,
			buildings_relations_table,
			menu_name=process
		)
	elif process == 'Buildings v2':
		buildings_v2_polygons_table = fResolveMcrVersionedTableExact(mcr_table_names, 'polygons', product_version)
		buildings_v2_relations_table = fResolveMcrVersionedTableExact(mcr_table_names, 'relations', product_version)
		buildings_v2_relations_geometries_table = fResolveMcrVersionedTableExact(mcr_table_names, 'relations_geometries', product_version)
		if not buildings_v2_polygons_table or not buildings_v2_relations_table or not buildings_v2_relations_geometries_table:
			available_polygons = sorted([t for t in mcr_table_names if t.startswith('polygons_')])
			available_relations = sorted([t for t in mcr_table_names if t.startswith('relations_') and not t.startswith('relations_geometries_')])
			available_rel_geoms = sorted([t for t in mcr_table_names if t.startswith('relations_geometries_')])
			expected_polygons = f"polygons_{_normalize_product_version_for_table(product_version)}"
			expected_relations = f"relations_{_normalize_product_version_for_table(product_version)}"
			expected_rel_geoms = f"relations_geometries_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned tables found for selected product '{product_version}'.\n"
				f"Expected polygons table: {expected_polygons}\n"
				f"Expected relations table: {expected_relations}\n"
				f"Expected relations_geometries table: {expected_rel_geoms}\n\n"
				f"Available polygons_* tables:\n{chr(10).join(available_polygons) if available_polygons else '(none)'}\n\n"
				f"Available relations_* tables:\n{chr(10).join(available_relations) if available_relations else '(none)'}\n\n"
				f"Available relations_geometries_* tables:\n{chr(10).join(available_rel_geoms) if available_rel_geoms else '(none)'}\n\n"
				"Please select a product version that has matching tables."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"Buildings v2 tables for '{product_version}': "
			f"polygons={buildings_v2_polygons_table}, "
			f"relations={buildings_v2_relations_table}, "
			f"relations_geometries={buildings_v2_relations_geometries_table}"
		)
		fProcBuildingsV2(
			product_version,
			license_zone,
			extentCoords,
			buildings_v2_polygons_table,
			buildings_v2_relations_table,
			buildings_v2_relations_geometries_table,
			menu_name=process
		)
	elif process == 'Buildings w/o Relations Optimised':
		buildings_wo_rel_polygons_table = fResolveMcrVersionedTableExact(mcr_table_names, 'polygons', product_version)
		if not buildings_wo_rel_polygons_table:
			available_polygons = sorted([t for t in mcr_table_names if t.startswith('polygons_')])
			expected_polygons = f"polygons_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned polygons table found for selected product '{product_version}'.\n"
				f"Expected polygons table: {expected_polygons}\n\n"
				f"Available polygons_* tables:\n{chr(10).join(available_polygons) if available_polygons else '(none)'}\n\n"
				"Please select a product version that has a matching polygons table."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"Buildings w/o Relations Optimised table for '{product_version}': "
			f"polygons={buildings_wo_rel_polygons_table}"
		)
		fProcBuilding_wo_Relations_SpatialOptimised(
			product_version,
			license_zone,
			extentCoords,
			buildings_wo_rel_polygons_table,
			menu_name=process
		)
	elif process == 'Network wo Relations':
		network_lines_table = fResolveMcrVersionedTableExact(mcr_table_names, 'lines', product_version)
		if not network_lines_table:
			available_lines = sorted([t for t in mcr_table_names if t.startswith('lines_')])
			expected_lines = f"lines_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned lines table found for selected product '{product_version}'.\n"
				f"Expected lines table: {expected_lines}\n\n"
				f"Available lines_* tables:\n{chr(10).join(available_lines) if available_lines else '(none)'}\n\n"
				"Please select a product version that has a matching lines table."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"Network wo Relations table for '{product_version}': "
			f"lines={network_lines_table}"
		)
		fProcNetwork_wo_Relations(
			product_version,
			license_zone,
			extentCoords,
			network_lines_table,
			menu_name=process
		)
	elif process == 'Network Detailed wo Relations':
		network_detailed_lines_table = fResolveMcrVersionedTableExact(mcr_table_names, 'lines', product_version)
		if not network_detailed_lines_table:
			available_lines = sorted([t for t in mcr_table_names if t.startswith('lines_')])
			expected_lines = f"lines_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned lines table found for selected product '{product_version}'.\n"
				f"Expected lines table: {expected_lines}\n\n"
				f"Available lines_* tables:\n{chr(10).join(available_lines) if available_lines else '(none)'}\n\n"
				"Please select a product version that has a matching lines table."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"Network Detailed wo Relations table for '{product_version}': "
			f"lines={network_detailed_lines_table}"
		)
		fProcNetworkDetailed_wo_Relations(
			product_version,
			license_zone,
			extentCoords,
			network_detailed_lines_table,
			menu_name=process
		)
	elif process == 'Network Major with Lanes, Curv, Grad (older)':
		network_major_lines_table = fResolveMcrVersionedTableExact(mcr_table_names, 'lines', product_version)
		if not network_major_lines_table:
			available_lines = sorted([t for t in mcr_table_names if t.startswith('lines_')])
			expected_lines = f"lines_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned lines table found for selected product '{product_version}'.\n"
				f"Expected lines table: {expected_lines}\n\n"
				f"Available lines_* tables:\n{chr(10).join(available_lines) if available_lines else '(none)'}\n\n"
				"Please select a product version that has a matching lines table."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"Network Major with Lanes, Curv, Grad (older) table for '{product_version}': "
			f"lines={network_major_lines_table}"
		)
		fProcNetworkMajor(
			product_version,
			license_zone,
			extentCoords,
			network_major_lines_table,
			menu_name=process
		)
	elif process == 'Network Simple (for large areas, older)':
		network_simple_lines_table = fResolveMcrVersionedTableExact(mcr_table_names, 'lines', product_version)
		if not network_simple_lines_table:
			available_lines = sorted([t for t in mcr_table_names if t.startswith('lines_')])
			expected_lines = f"lines_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned lines table found for selected product '{product_version}'.\n"
				f"Expected lines table: {expected_lines}\n\n"
				f"Available lines_* tables:\n{chr(10).join(available_lines) if available_lines else '(none)'}\n\n"
				"Please select a product version that has a matching lines table."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"Network Simple (for large areas, older) table for '{product_version}': "
			f"lines={network_simple_lines_table}"
		)
		fProcNetworkSimple(
			product_version,
			license_zone,
			extentCoords,
			network_simple_lines_table,
			menu_name=process
		)

	elif process == 'All Polygons Contain':
		fAllPolyContains(product_version, license_zone, extentCoords)
	elif process == 'All Polygons Intersect':
		fAllPolyIntersect(product_version, license_zone, extentCoords)
	elif process == 'Admin Areas':
		admin_relations_table = fResolveMcrVersionedTableExact(mcr_table_names, 'relations', product_version)
		if not admin_relations_table:
			available_relations = sorted([t for t in mcr_table_names if t.startswith('relations_') and not t.startswith('relations_geometries_')])
			expected_relations = f"relations_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned relations table found for selected product '{product_version}'.\n"
				f"Expected relations table: {expected_relations}\n\n"
				f"Available relations_* tables:\n{chr(10).join(available_relations) if available_relations else '(none)'}\n\n"
				"Please select a product version that has a matching relations table."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"Admin Areas table for '{product_version}': "
			f"relations={admin_relations_table}"
		)
		fProcessAdminAreas(
			extent_layer,
			product_version,
			license_zone,
			extentCoords,
			h3,
			admin_relations_table
		)
	elif process == 'Admin Areas by name':
		admin_relations_table = fResolveMcrVersionedTableExact(mcr_table_names, 'relations', product_version)
		if not admin_relations_table:
			available_relations = sorted([t for t in mcr_table_names if t.startswith('relations_') and not t.startswith('relations_geometries_')])
			expected_relations = f"relations_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned relations table found for selected product '{product_version}'.\n"
				f"Expected relations table: {expected_relations}\n\n"
				f"Available relations_* tables:\n{chr(10).join(available_relations) if available_relations else '(none)'}\n\n"
				"Please select a product version that has a matching relations table."
			)
			print(message)
			qtMsgBox(message)
			return

		search_text, ok = QInputDialog.getText(
			iface.mainWindow(),
			"Admin Areas by name",
			"Name contains (ILIKE):"
		)
		if not ok:
			print("Admin Areas by name cancelled by user.")
			return

		search_text = search_text.strip()
		if search_text == "":
			message = "Admin Areas by name requires a non-empty search string."
			print(message)
			qtMsgBox(message)
			return

		print(
			f"Admin Areas by name table for '{product_version}': "
			f"relations={admin_relations_table}, name_filter='{search_text}'"
		)
		fProcessAdminAreas(
			extent_layer,
			product_version,
			license_zone,
			extentCoords,
			h3,
			admin_relations_table,
			admin_name_filter=search_text
		)
	elif process == 'Admin Point Places':
		admin_points_table = fResolveMcrVersionedTableExact(mcr_table_names, 'points', product_version)
		if not admin_points_table:
			available_points = sorted([t for t in mcr_table_names if t.startswith('points_')])
			expected_points = f"points_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned points table found for selected product '{product_version}'.\n"
				f"Expected points table: {expected_points}\n\n"
				f"Available points_* tables:\n{chr(10).join(available_points) if available_points else '(none)'}\n\n"
				"Please select a product version that has a matching points table."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"Admin Point Places table for '{product_version}': "
			f"points={admin_points_table}"
		)
		fProcessPlacePoint(
			extent_layer,
			product_version,
			license_zone,
			extentCoords,
			h3,
			admin_points_table
		)
	elif process == 'Inland Water':
		inland_polygons_table = fResolveMcrVersionedTableExact(mcr_table_names, 'polygons', product_version)
		inland_relations_geometries_table = fResolveMcrVersionedTableExact(mcr_table_names, 'relations_geometries', product_version)
		if not inland_polygons_table or not inland_relations_geometries_table:
			available_polygons = sorted([t for t in mcr_table_names if t.startswith('polygons_')])
			available_rel_geoms = sorted([t for t in mcr_table_names if t.startswith('relations_geometries_')])
			expected_polygons = f"polygons_{_normalize_product_version_for_table(product_version)}"
			expected_rel_geoms = f"relations_geometries_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned tables found for selected product '{product_version}'.\n"
				f"Expected polygons table: {expected_polygons}\n"
				f"Expected relations_geometries table: {expected_rel_geoms}\n\n"
				f"Available polygons_* tables:\n{chr(10).join(available_polygons) if available_polygons else '(none)'}\n\n"
				f"Available relations_geometries_* tables:\n{chr(10).join(available_rel_geoms) if available_rel_geoms else '(none)'}\n\n"
				"Please select a product version that has matching tables."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"Inland Water tables for '{product_version}': "
			f"polygons={inland_polygons_table}, "
			f"relations_geometries={inland_relations_geometries_table}"
		)
		fProcessInlandWater(
			extent_layer,
			product_version,
			license_zone,
			extentCoords,
			h3,
			inland_polygons_table,
			inland_relations_geometries_table
		)
	elif process == 'Ocean Water':
		ocean_polygons_table = fResolveMcrVersionedTableExact(mcr_table_names, 'polygons', product_version)
		ocean_relations_geometries_table = fResolveMcrVersionedTableExact(mcr_table_names, 'relations_geometries', product_version)
		if not ocean_polygons_table or not ocean_relations_geometries_table:
			available_polygons = sorted([t for t in mcr_table_names if t.startswith('polygons_')])
			available_rel_geoms = sorted([t for t in mcr_table_names if t.startswith('relations_geometries_')])
			expected_polygons = f"polygons_{_normalize_product_version_for_table(product_version)}"
			expected_rel_geoms = f"relations_geometries_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned tables found for selected product '{product_version}'.\n"
				f"Expected polygons table: {expected_polygons}\n"
				f"Expected relations_geometries table: {expected_rel_geoms}\n\n"
				f"Available polygons_* tables:\n{chr(10).join(available_polygons) if available_polygons else '(none)'}\n\n"
				f"Available relations_geometries_* tables:\n{chr(10).join(available_rel_geoms) if available_rel_geoms else '(none)'}\n\n"
				"Please select a product version that has matching tables."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"Ocean Water tables for '{product_version}': "
			f"polygons={ocean_polygons_table}, "
			f"relations_geometries={ocean_relations_geometries_table}"
		)
		fProcessOceanWater(
			extent_layer,
			product_version,
			license_zone,
			extentCoords,
			h3,
			ocean_polygons_table,
			ocean_relations_geometries_table
		)
	elif process == 'Buildings with parts':
		fProcessBuildingsWithParts(product_version, license_zone, extentCoords)
	elif process == 'Buildings with parts H3':
		fProcessBuildingsWithPartsH3(extent_layer, product_version, license_zone, extentCoords)
	elif process == 'Buildings with relations':
		fProcessBuildingsRel(product_version, license_zone, extentCoords)
	elif process == 'Buildings (Old)':
		fProcessBuildingsOld(product_version, license_zone, extentCoords)
	elif process == 'Network with Speeds':
		fProcessNetworkSpeeds(product_version, license_zone, extentCoords)
	elif process == 'Network Elevation (h3)':
		fProcessNetworkElevation(extent_layer, product_version, license_zone, extentCoords, h3)
	elif process == 'Network Junctions (h3)':
		fProcessNetworkJunctions(extent_layer, product_version, license_zone, extentCoords, h3)
	elif process == 'Street Lamps (h3)':
		street_lamps_points_table = fResolveMcrVersionedTableExact(mcr_table_names, 'points', product_version)
		if not street_lamps_points_table:
			available_points = sorted([t for t in mcr_table_names if t.startswith('points_')])
			expected_points = f"points_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned points table found for selected product '{product_version}'.\n"
				f"Expected points table: {expected_points}\n\n"
				f"Available points_* tables:\n{chr(10).join(available_points) if available_points else '(none)'}\n\n"
				"Please select a product version that has a matching points table."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"Street Lamps (h3) table for '{product_version}': "
			f"points={street_lamps_points_table}"
		)
		fProcessSteetLamp(
			extent_layer,
			product_version,
			license_zone,
			extentCoords,
			h3,
			street_lamps_points_table
		)
	elif process == 'Relations-Geometry (point) (h3)':
		fProcessRelationsGeomPoint(extent_layer, product_version, license_zone, extentCoords, h3)
	elif process == 'Relations-Geometry (line) (h3)':
		fProcessRelationsGeomLine(extent_layer, product_version, license_zone, extentCoords, h3)
	elif process == 'Relations-Geometry (polygon) (h3)':
		fProcessRelationsGeomPoly(extent_layer, product_version, license_zone, extentCoords, h3)
	elif process == 'All relations WIP (not relation_geometry) (linestring) (h3)':
		fProcessAllRelations(extent_layer, product_version, license_zone, extentCoords, h3)
	elif process == 'Lane Connectivity relations (h3)':
		fProcessLaneConnectivity(extent_layer, product_version, license_zone, extentCoords, h3)
	elif process == 'EV_Charging':
		ev_points_table = fResolveMcrVersionedTableExact(mcr_table_names, 'points', product_version)
		if not ev_points_table:
			available_points = sorted([t for t in mcr_table_names if t.startswith('points_')])
			expected_points = f"points_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned points table found for selected product '{product_version}'.\n"
				f"Expected points table: {expected_points}\n\n"
				f"Available points_* tables:\n{chr(10).join(available_points) if available_points else '(none)'}\n\n"
				"Please select a product version that has a matching points table."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"EV_Charging table for '{product_version}': "
			f"points={ev_points_table}"
		)
		fProcessEV(
			product_version,
			license_zone,
			extentCoords,
			ev_points_table
		)
	elif process == 'EV_Charging (detailed)':
		ev_detailed_points_table = fResolveMcrVersionedTableExact(mcr_table_names, 'points', product_version)
		ev_detailed_relations_table = fResolveMcrVersionedTableExact(mcr_table_names, 'relations', product_version)
		if not ev_detailed_points_table or not ev_detailed_relations_table:
			available_points = sorted([t for t in mcr_table_names if t.startswith('points_')])
			available_relations = sorted([t for t in mcr_table_names if t.startswith('relations_')])
			expected_points = f"points_{_normalize_product_version_for_table(product_version)}"
			expected_relations = f"relations_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned EV tables found for selected product '{product_version}'.\n"
				f"Expected points table: {expected_points}\n"
				f"Expected relations table: {expected_relations}\n\n"
				f"Available points_* tables:\n{chr(10).join(available_points) if available_points else '(none)'}\n\n"
				f"Available relations_* tables:\n{chr(10).join(available_relations) if available_relations else '(none)'}\n\n"
				"Please select a product version that has matching points and relations tables."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"EV_Charging (detailed) tables for '{product_version}': "
			f"points={ev_detailed_points_table}, "
			f"relations={ev_detailed_relations_table}"
		)
		fProcessEVDetailed(
			product_version,
			license_zone,
			extentCoords,
			ev_detailed_points_table,
			ev_detailed_relations_table
		)
	elif process == 'EV_Charging (stations aggregated)':
		ev_station_points_table = fResolveMcrVersionedTableExact(mcr_table_names, 'points', product_version)
		ev_station_relations_table = fResolveMcrVersionedTableExact(mcr_table_names, 'relations', product_version)
		if not ev_station_points_table or not ev_station_relations_table:
			available_points = sorted([t for t in mcr_table_names if t.startswith('points_')])
			available_relations = sorted([t for t in mcr_table_names if t.startswith('relations_')])
			expected_points = f"points_{_normalize_product_version_for_table(product_version)}"
			expected_relations = f"relations_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned EV tables found for selected product '{product_version}'.\n"
				f"Expected points table: {expected_points}\n"
				f"Expected relations table: {expected_relations}\n\n"
				f"Available points_* tables:\n{chr(10).join(available_points) if available_points else '(none)'}\n\n"
				f"Available relations_* tables:\n{chr(10).join(available_relations) if available_relations else '(none)'}\n\n"
				"Please select a product version that has matching points and relations tables."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"EV_Charging (stations aggregated) tables for '{product_version}': "
			f"points={ev_station_points_table}, "
			f"relations={ev_station_relations_table}"
		)
		fProcessEVDetailedByStation(
			product_version,
			license_zone,
			extentCoords,
			ev_station_points_table,
			ev_station_relations_table
		)
	elif process == 'Overture Buildings (external)':
		fProcessOvertureBuildings(extentCoords)
	elif process == 'Fire Stations':
		fire_stations_points_table = fResolveMcrVersionedTableExact(mcr_table_names, 'points', product_version)
		if not fire_stations_points_table:
			available_points = sorted([t for t in mcr_table_names if t.startswith('points_')])
			expected_points = f"points_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned points table found for selected product '{product_version}'.\n"
				f"Expected points table: {expected_points}\n\n"
				f"Available points_* tables:\n{chr(10).join(available_points) if available_points else '(none)'}\n\n"
				"Please select a product version that has a matching points table."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"Fire Stations table for '{product_version}': "
			f"points={fire_stations_points_table}"
		)
		fProcessFireStations(
			product_version,
			license_zone,
			extentCoords,
			fire_stations_points_table
		)
	elif process == 'Admin Places (polygon)':
		admin_places_polygons_table = fResolveMcrVersionedTableExact(mcr_table_names, 'polygons', product_version)
		if not admin_places_polygons_table:
			available_polygons = sorted([t for t in mcr_table_names if t.startswith('polygons_')])
			expected_polygons = f"polygons_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned polygons table found for selected product '{product_version}'.\n"
				f"Expected polygons table: {expected_polygons}\n\n"
				f"Available polygons_* tables:\n{chr(10).join(available_polygons) if available_polygons else '(none)'}\n\n"
				"Please select a product version that has a matching polygons table."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"Admin Places (polygon) table for '{product_version}': "
			f"polygons={admin_places_polygons_table}"
		)
		fAdminPlaces(
			product_version,
			license_zone,
			extentCoords,
			admin_places_polygons_table
		)
	elif process == 'Turn Restrictions':
		turn_restrictions_rel_geoms_table = fResolveMcrVersionedTableExact(mcr_table_names, 'relations_geometries', product_version)
		if not turn_restrictions_rel_geoms_table:
			available_rel_geoms = sorted([t for t in mcr_table_names if t.startswith('relations_geometries_')])
			expected_rel_geoms = f"relations_geometries_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned relations_geometries table found for selected product '{product_version}'.\n"
				f"Expected relations_geometries table: {expected_rel_geoms}\n\n"
				f"Available relations_geometries_* tables:\n{chr(10).join(available_rel_geoms) if available_rel_geoms else '(none)'}\n\n"
				"Please select a product version that has a matching relations_geometries table."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"Turn Restrictions table for '{product_version}': "
			f"relations_geometries={turn_restrictions_rel_geoms_table}"
		)
		fTurnRestrictions(
			product_version,
			license_zone,
			extentCoords,
			turn_restrictions_rel_geoms_table
		)
	elif process == 'Traffic Signs':
		traffic_signs_points_table = fResolveMcrVersionedTableExact(mcr_table_names, 'points', product_version)
		if not traffic_signs_points_table:
			available_points = sorted([t for t in mcr_table_names if t.startswith('points_')])
			expected_points = f"points_{_normalize_product_version_for_table(product_version)}"
			message = (
				f"\nNo exact versioned points table found for selected product '{product_version}'.\n"
				f"Expected points table: {expected_points}\n\n"
				f"Available points_* tables:\n{chr(10).join(available_points) if available_points else '(none)'}\n\n"
				"Please select a product version that has a matching points table."
			)
			print(message)
			qtMsgBox(message)
			return
		print(
			f"Traffic Signs table for '{product_version}': "
			f"points={traffic_signs_points_table}"
		)
		fTrafficSigns(
			product_version,
			license_zone,
			extentCoords,
			traffic_signs_points_table
		)

	elif process == 'Trees - use dbHIP':
		print("This should be run in OSM Turbo, from dbHip")

	elif process == 'BuildingsSimple (h3)':
		print("Example of switching betwee H3 and Polygon")
		fBuildingsSimple_H3(extent_layer,product_version, license_zone, extentCoords, h3)
	elif process == 'Draw H3 tiles':
		print("Draw H3 fucking tiles")
		sub_H3_grid.main(extent_layer)
		# fDrawHexesFromExtent(extent_layer, h3)
	elif process == 'List H3 tiles':
		print("List H3 fucking tiles")
		fHexesFromExtent(extent_layer)
	elif process == 'Exit':
		print("Cancel")
	else:
		print("Not yet implemented")

	
print("Loading Main()")
fMainUI()


# extentLayer = fSelectExtentLayer()
# print(extentLayer)
# extentCoords = fGetExtentCoords(extentLayer)
# print(extentCoords)

# fGetExtentPolygonCoords()

# fBoundingPolygon()
