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
sys.path.append(os.path.dirname(current_script_dir))
import imp
# import importlib
# importlib.reload(my_module)

from unittest import result
import b9PyQGIS
imp.reload(b9PyQGIS)
# importlib.reload(b9PyQGIS)
from b9PyQGIS import *
from qgis.core import QgsDataSourceUri, QgsVectorLayer, QgsProject
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QComboBox, QPushButton, QLabel, QLineEdit, QCheckBox
# print("loaded qgis.core")

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
iniFile = os.path.dirname( imp.find_module('b9PyQGIS')[1] ) + "/" + 'b9QGISdata.ini'
# spec = importlib.util.find_spec('b9PyQGIS')
# iniFile = os.path.dirname(spec.origin) + "/b9QGISdata.ini"
config = configparser.ConfigParser()
config.read(iniFile)
dirCommonGeopack = config['directories']['dirCommonGeopack']

server_hostname=config['mcr']['server_hostname']

http_path=config['mcr']['http_path']
access_token=config['mcr']['access_token']
connection = sql.connect(server_hostname = server_hostname, http_path = http_path, access_token = access_token)
print("Connected to databricks")

# clipLayerName=config['common']['extent']
# ventura_qgisname = config['orbis2']['ventura_qgisname']
# ventura_url = config['orbis2']['ventura_qgis_ip']
# ventura_port = config['orbis2']['ventura_port']
# ventura_db = config['orbis2']['ventura_db']
# ventura_usr = config['orbis2']['ventura_usr']
# ventura_pass = config['orbis2']['ventura_pass']

import sub_H3_grid
imp.reload(sub_H3_grid)
from sub_H3_grid import *

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

def fProcessAdminAreas(extent_layer, product_version, license_zone, extentCoords, h3):
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
	# -- list admin-related columns from relations table, ok
	# -- hope that relation table alreeady includes the correct geometry
	# SELECT
	# 	orbis_id,
	# 	layer_id,
	# 	tags['name'] as name,
	# 	tags['default_language'] as language,
	# 	tags['boundary'] as boundary,
	# 	tags['type'] as type,
	# 	tags['place'] as place,
	# 	tags['admin_level'] as admin_level,
	# 	exploded_member.id AS admin_centre_id,
	# 	map_filter(tags, (key, value) -> NOT (key LIKE 'layer_id:%' OR key LIKE 'gers%' OR key LIKE 'license%' OR key LIKE 'maxspeed%' OR key LIKE 'oprod%' OR key LIKE 'source%' OR key LIKE 'supported%' OR key LIKE 'zoomlevel_min' OR key LIKE 'routing_class' OR key LIKE 'navigability' OR key LIKE 'postal_code%' OR key LIKE '%pronunciation%' )) AS tags_clean,
	# 	--members,
	# 	--tags,
	# 	geometry
	# FROM pu_orbis_platform_prod_catalog.map_central_repository.relations
	# LATERAL VIEW EXPLODE(FILTER(members, x -> x.role = 'admin_centre')) AS exploded_member
	# WHERE tags['type'] = 'boundary'
	# AND
	# tags['boundary'] = 'administrative'
	# AND
	# geom_type in ("ST_POLYGON","ST_MULTIPOLYGON")
	# AND {bounds}
	# AND product = '{product_version}'
	# AND license_zone like '%{license_zone}%' 
	# {h3_index};"""

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
	FROM pu_orbis_platform_prod_catalog.map_central_repository.relations,
	bbox
	LATERAL VIEW EXPLODE(FILTER(members, x -> x.role = 'admin_centre')) AS exploded_member
	WHERE tags['type'] = 'boundary'
	AND
	tags['boundary'] = 'administrative'
	AND
	geom_type in ("ST_POLYGON","ST_MULTIPOLYGON")
	AND 
	ST_Intersects(bbox.g, ST_GEOMFROMWKT(geometry))
	AND 
	product = '{product_version}'
	AND
	license_zone like '%{license_zone}%' 
	;""".format(product_version=product_version, license_zone=license_zone, extent=extentStr)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fProcessPlacePoint(extent_layer, product_version, license_zone, extentCoords, h3):
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
	FROM pu_orbis_platform_prod_catalog.map_central_repository.points,
	bbox
	WHERE 
	tags['place'] is not null
	AND 
	ST_Intersects(bbox.g, ST_GEOMFROMWKT(geometry))
	AND
	product = '{product_version}'
	AND
	license_zone like '%{license_zone}%'
	;
	""".format(product_version=product_version, license_zone=license_zone, extent=extentStr)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fProcessInlandWater(extent_layer, product_version, license_zone, extentCoords, h3):
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
	pu_orbis_platform_prod_catalog.map_central_repository.polygons,
	bbox
WHERE 
	natural = 'water' 
	AND ST_Intersects(bbox.g, ST_GEOMFROMWKT(geometry))
	AND product = '{product_version}'
	AND license_zone like '%{license_zone}%'

UNION 

SELECT 
	orbis_id,
	tags['intermittent'] AS intermittent,
	geometry 
FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.relations_geometries,
	bbox
WHERE 
	tags['natural'] = 'water'
	AND geom_type IN ("ST_POLYGON","ST_MULTIPOLYGON")
	AND ST_Intersects(bbox.g, ST_GEOMFROMWKT(geometry))
	AND product = '{product_version}'
	AND license_zone like '%{license_zone}%'
	""".format(product_version=product_version, license_zone=license_zone, extent=extentStr)


	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)

def fProcessOceanWater(extent_layer, product_version, license_zone, extentCoords, h3):
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
	pu_orbis_platform_prod_catalog.map_central_repository.polygons
	WHERE 
	(tags['geometry_type'] = 'area'
	OR
	tags['maritime_water'] = 'yes'
	OR
	tags['land_mass'] = 'yes')
	AND {bounds}
	AND product = '{product_version}'
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
	pu_orbis_platform_prod_catalog.map_central_repository.relations_geometries
	WHERE 
	(tags['geometry_type'] = 'area'
	OR
	tags['maritime_water'] = 'yes'
	OR
	tags['land_mass'] = 'yes')
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

def fProcessNetworkMajor(product_version, license_zone, extentCoords):
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
	# tags["sidewalk"] AS sidewalk,
	# tags["speed:free_flow"] AS speed_free_flow,
	# tags["speed:week"] AS speed_week,
	# tags["speed:weekday"] AS speed_weekday,
	# tags["speed:weekend"] AS speed_weekend,
	# tags["oneway"] AS oneway,
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
	-- road network with lanes, speeds 
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
	tags["sidewalk"] AS sidewalk,
	tags["speed:free_flow"] AS speed_free_flow,
	tags["speed:week"] AS speed_week,
	tags["speed:weekday"] AS speed_weekday,
	tags["speed:weekend"] AS speed_weekend,
	tags["oneway"] AS oneway,
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


def fProcessNetworkSimple(product_version, license_zone, extentCoords):
	extentStr = "'" + extentCoords + "'"

	# sql = """
	# select
	# orbis_id, 
	# highway,
	# railway, 
	# bridge, tunnel,
	# tags['navigability'] AS navigability,
	# tags['routing_class'] AS routing_class,
	# tags['maxspeed'] AS maxspeed,
	# layer, 
	# geometry
	# FROM 
	# pu_orbis_platform_prod_catalog.map_central_repository.lines
	# WHERE 
	# ("highway" is not null 
	# or 
	# tags['routing_class'] is not null
	# )
	# AND
	# ST_Intersects(ST_GEOMFROMWKT({extent}), ST_GEOMFROMWKT(geometry)) 
	# AND 
	# product = '{product_version}'
	# AND
	# license_zone like '%{license_zone}%' 
	# """.format(product_version=product_version, license_zone=license_zone, extent=extentStr)

	sql = """
	-- road network simple 
	WITH bbox AS (
		SELECT ST_GEOMFROMWKT({extent}) AS g
	)
	select
	orbis_id, 
	highway,
	railway, 
	bridge, tunnel,
	tags['navigability'] AS navigability,
	tags['routing_class'] AS routing_class,
	tags['maxspeed'] AS maxspeed,
	layer, 
	geometry

	FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.lines,
	bbox

	WHERE 
	("highway" is not null 
	or 
	tags['routing_class'] is not null
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


def fProcessSteetLamp(extent_layer, product_version, license_zone, extentCoords, h3):
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
	pu_orbis_platform_prod_catalog.map_central_repository.points
	WHERE
	-- layer_id = 21263 OR
	tags['highway'] = 'street_lamp'
	-- AND 
	-- highway IS NOT NULL AND highway != '' 
	-- AND tags['routing_class'] < 4
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


def fProcWaterNatural(extent_layer, product_version, license_zone, extentCoords, menu_name=None):
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
	  FROM pu_orbis_platform_prod_catalog.map_central_repository.polygons p
	  WHERE p.product = '{product_version}'
	    AND p.license_zone = '{license_zone}'
	    AND p.tags['natural'] = 'water'
	    AND p.element_type != 'RELATION'
	    AND p.geom_type IN ('ST_POLYGON', 'ST_MULTIPOLYGON')
	),
	polys_spatial_filtered AS (
	  SELECT
	    'polygons' AS source,
	    p.product,
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
	  FROM pu_orbis_platform_prod_catalog.map_central_repository.relations_geometries r
	  WHERE r.product = '{product_version}'
	    AND r.license_zone = '{license_zone}'
	    AND r.tags['natural'] = 'water'
	    AND r.geom_type IN ('ST_POLYGON', 'ST_MULTIPOLYGON')
	),
	rels_spatial_filtered AS (
	  SELECT
	    'relations_geometries' AS source,
	    r.product,
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
	;""".format(product_version=product_version, license_zone=license_zone, extentStr=extentStr)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe Water (natural=water) query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fProcBuilding_with_Relations_SpatialOptimised(product_version, license_zone, extentCoords, menu_name=None):
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
    SELECT orbis_id, product, license_zone, tags, building, geometry
    FROM pu_orbis_platform_prod_catalog.map_central_repository.polygons
    WHERE product = '{product_version}' AND license_zone = '{license_zone}'
  ),
  polys_pre AS (
    SELECT p.orbis_id, p.product, p.license_zone, p.tags, p.building, p.geometry, ST_GeomFromWKT(p.geometry) AS g
    FROM polys_src p
    WHERE (p.building = 'yes' OR p.tags['building'] IS NOT NULL OR p.tags['building:part'] IS NOT NULL)
  ),
  polys_spatial_filtered AS (
    SELECT p.orbis_id, p.product, p.license_zone, p.tags, p.building, p.geometry, p.g, ST_Envelope(p.g) AS env
    FROM polys_pre p
    CROSS JOIN q
    WHERE ST_Intersects(ST_Envelope(p.g), q.qenv) AND ST_Intersects(q.qg, p.g)
  ),
  -- Find relations whose members reference our spatially-filtered polygons using an array-test (no explode) and restrict to polygonal relation geometry
  rel_pick AS (
    SELECT p.orbis_id AS poly_orbis_id,
           MIN(r.orbis_id) AS parent_relation_id
    FROM pu_orbis_platform_prod_catalog.map_central_repository.relations r
    JOIN polys_spatial_filtered p
      ON r.product = p.product
      AND r.license_zone = p.license_zone
    WHERE r.product = '{product_version}'
      AND r.license_zone = 'NLD'
      AND r.geom_type IN ('ST_POLYGON','ST_MULTIPOLYGON')
      AND SIZE(FILTER(r.members, x -> x.id = p.orbis_id AND x.role IN ('outline','part'))) > 0
    GROUP BY p.orbis_id
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
;""".format(product_version=product_version, license_zone=license_zone, extent=extent) 

	# Put script on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe BuildingFootprints (new) script is on the clipboard.\nPaste and run it in DBeaver as a single statement.\nUse Export Query (streamed) with small fetch size (~2000)."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fProcBuilding_wo_Relations_SpatialOptimised(product_version, license_zone, extentCoords, menu_name=None):
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
    SELECT orbis_id, product, license_zone, tags, building, geometry
    FROM pu_orbis_platform_prod_catalog.map_central_repository.polygons
    WHERE product = '{product_version}' AND license_zone = '{license_zone}'
  ),
  polys_pre AS (
    SELECT p.orbis_id, p.product, p.license_zone, p.tags, p.building, p.geometry, ST_GeomFromWKT(p.geometry) AS g
    FROM polys_src p
    WHERE (p.building = 'yes' OR p.tags['building'] IS NOT NULL OR p.tags['building:part'] IS NOT NULL)
  ),
  polys_spatial_filtered AS (
    SELECT p.orbis_id, p.product, p.license_zone, p.tags, p.building, p.geometry, p.g, ST_Envelope(p.g) AS env
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
;""".format(product_version=product_version, license_zone=license_zone, extent=extent) 

	# Put script on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe BuildingFootprints (new) script is on the clipboard.\nPaste and run it in DBeaver as a single statement.\nUse Export Query (streamed) with small fetch size (~2000)."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fProcLoiArtificialGround(product_version, license_zone, extentCoords, menu_name=None):
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
    SELECT orbis_id, product, license_zone, tags, geometry
    FROM pu_orbis_platform_prod_catalog.map_central_repository.polygons
    WHERE product = '{product_version}'
      AND license_zone = '{license_zone}'
      AND (
        tags['landuse'] IN ('artificial_ground','brownfield','builtup_area','construction','farmyard','garages','greenfield','landfill','quarry','railway','residential')
        OR tags['aeroway'] IN ('runway','apron','taxiway')
        OR tags['man_made'] IN ('breakwater','pier')
        OR tags['leisure'] = 'common'
      )
  ),

  loi_relgeo_src AS (
    SELECT orbis_id, product, license_zone, tags AS tags, geometry, geom_type
    FROM pu_orbis_platform_prod_catalog.map_central_repository.relations_geometries
    WHERE product = '{product_version}'
      AND license_zone = '{license_zone}'
      AND geom_type IN ('ST_POLYGON','ST_MULTIPOLYGON')
      AND (
        tags['landuse'] IN ('artificial_ground','brownfield','builtup_area','construction','farmyard','garages','greenfield','landfill','quarry','railway','residential')
        OR tags['aeroway'] IN ('runway','apron','taxiway')
        OR tags['man_made'] IN ('breakwater','pier')
        OR tags['leisure'] = 'common'
      )
  ),

  loi_pre AS (
    SELECT orbis_id, product, license_zone, tags, geometry, ST_GeomFromWKT(geometry) AS g, 'polygons' AS source
    FROM loi_polys_src
    UNION ALL
    SELECT orbis_id, product, license_zone, tags, geometry, ST_GeomFromWKT(geometry) AS g, 'relations_geometries' AS source
    FROM loi_relgeo_src
  ),

  loi_spatial_filtered AS (
    SELECT p.orbis_id, p.product, p.license_zone, p.tags, p.geometry, p.g, ST_Envelope(p.g) AS env, p.source
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
""".format(product_version=product_version, license_zone=license_zone, extent=extent)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe LOI Artificial Ground query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fTurnRestrictions(product_version, license_zone, extentCoords):
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
		pu_orbis_platform_prod_catalog.map_central_repository.relations_geometries
		WHERE 
		tags['type']='restriction'
		AND
		geom_type in ('ST_MULTILINESTRING', 'ST_LINESTRING')
		AND 
		ST_Intersects(ST_GEOMFROMWKT({extent}), ST_GEOMFROMWKT(geometry)) 
		AND 
		product = '{product_version}'
		AND
		license_zone like '%{license_zone}%'
		) t
WHERE type LIKE 'restriction%'
""".format(product_version=product_version, license_zone=license_zone, extent=extentStr)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)



def fTrafficSigns(product_version, license_zone, extentCoords):
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
	pu_orbis_platform_prod_catalog.map_central_repository.points
	WHERE 
	tags['traffic_sign'] is not null
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


def fAdminPlaces(product_version, license_zone, extentCoords):
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
	FROM pu_orbis_platform_prod_catalog.map_central_repository.polygons
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
product = '{product_version}'
AND
license_zone like '%{license_zone}%'
AND
ST_Intersects(g, bbox)
""".format(product_version=product_version, license_zone=license_zone, extent=extentStr)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)

def fProcessLandUse(extent_layer, product_version, license_zone, extentCoords, h3):
	if h3 == True:
		hextiles = fHexesFromExtent(extent_layer)
		bounds = hexListToChildString(hextiles)
		h3_index = 'AND h3_index != \'0\''
	else:
		extentStr = "'" + extentCoords + "'"
		bounds = 	f"ST_Intersects(ST_GEOMFROMWKT({extentStr}), ST_GEOMFROMWKT(geometry))"
		h3_index = ''

	sql = f"""
	-- all landuse-realated polygons
	SELECT
	orbis_id,
	tags['aeroway'] as aeroway, 
	tags['landuse'] as landuse,  
	tags['leisure'] as leisure, 
	tags['military'] as military, 
	tags['natural'] as natural, 
	tags['tourism'] as tourism,
	tags['amenity'] as amenity,
	CAST(tags AS STRING) AS tags,
	geometry 
	FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.polygons
	WHERE 
	geom_type in ('ST_POLYGON','ST_MULTIPOLYGON')
	 AND (
		 tags['aeroway'] IS NOT NULL 
		 OR tags['landuse'] IS NOT NULL 
		 OR tags['leisure'] IS NOT NULL 
		 OR tags['military'] IS NOT NULL 
		 OR tags['natural'] IS NOT NULL 
		 OR tags['tourism'] IS NOT NULL
		 OR tags['amenity'] IS NOT NULL
	 )
	AND {bounds}
	AND 
	product = '{product_version}'
	AND
	license_zone like '%{license_zone}%' 
	{h3_index}

	UNION

	SELECT
	orbis_id,
	tags['aeroway'] as aeroway, 
	tags['landuse'] as landuse,  
	tags['leisure'] as leisure, 
	tags['military'] as military, 
	tags['natural'] as natural, 
	tags['tourism'] as tourism,
	tags['amenity'] as amenity,
	CAST(tags AS STRING) AS tags,
	geometry 
	FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.relations_geometries
	WHERE 
	geom_type in ('ST_POLYGON','ST_MULTIPOLYGON')
	 AND (
		 tags['aeroway'] IS NOT NULL 
		 OR tags['landuse'] IS NOT NULL 
		 OR tags['leisure'] IS NOT NULL 
		 OR tags['military'] IS NOT NULL 
		 OR tags['natural'] IS NOT NULL 
		 OR tags['tourism'] IS NOT NULL
		 OR tags['amenity'] IS NOT NULL
	 ) 
	AND {bounds} 
	AND 
	product = '{product_version}'
	AND
	license_zone like '%{license_zone}%' 
	{h3_index}
	;"""

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)


def fProcessEV(product_version, license_zone, extentCoords):
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
	pu_orbis_platform_prod_catalog.map_central_repository.points
	WHERE 
	tags['amenity']='charging_location'
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

def fProcessFireStations(product_version, license_zone, extentCoords):
	extentStr = "'" + extentCoords + "'"

	sql = """
	-- Fire Stations
	SELECT
	orbis_id,
	amenity,
	z_order,
	geometry 
	FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.points
	WHERE 
	amenity='fire_station'
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

def hexListToChildString(h3_hex_ids):
	result = "(\n"
	result += " OR \n".join([f"\th3_ischildof(h3_index,'{hex_id}')" for hex_id in h3_hex_ids])
	result += "\n)"
	return result

# COMMENTED OUT - Now using native Databricks H3 functions (h3_polyfillash3string, h3_kring, h3_toparent)
# def fGenerateMultiResH3Tiles(wkt_polygon, target_resolutions=None, base_res=None, k_ring=1):
# 	"""Generate H3 tiles at multiple resolutions from WKT polygon.
# 	Returns list of (h3_id, resolution) tuples.
# 	"""
# 	import sys
# 	import os
# 	
# 	# Import sub_h3_python from same directory
# 	try:
# 		import sub_h3_python
# 		# Reload to get latest version
# 		import importlib
# 		importlib.reload(sub_h3_python)
# 		
# 		if target_resolutions is None:
# 			# Default resolutions covering most use cases
# 			target_resolutions = [0, 3, 4, 5, 6, 7, 8]
# 		
# 		print(f"Generating H3 tiles for resolutions: {target_resolutions}")
# 		tiles = sub_h3_python.generate_expanded_tiles_from_wkt(
# 			wkt_polygon, 
# 			target_resolutions=target_resolutions,
# 			base_res=base_res,
# 			k_ring=k_ring
# 		)
# 		print(f"Generated {len(tiles)} H3 tiles across {len(set(r for _, r in tiles))} resolutions")
# 		return tiles
# 		
# 	except Exception as e:
# 		print(f"Error generating H3 tiles: {e}")
# 		print("Falling back to basic H3 generation...")
# 		# Fallback to existing single-resolution method
# 		return None

# COMMENTED OUT - Now using native Databricks H3 functions (h3_polyfillash3string, h3_kring, h3_toparent)
# def fH3TilesToSQLValues(h3_tiles):
# 	"""Convert list of (h3, resolution) tuples to SQL VALUES format.
# 	Returns string ready for SQL IN clause or CTE.
# 	"""
# 	if not h3_tiles:
# 		return ""
# 	
# 	values_lines = []
# 	for i, (h3_id, res) in enumerate(h3_tiles):
# 		suffix = ',' if i < (len(h3_tiles) - 1) else ''
# 		values_lines.append(f"        ('{h3_id}', {res}){suffix}")
# 	
# 	return "\n".join(values_lines)

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

	cursor.execute("SELECT distinct license_zone FROM pu_orbis_platform_prod_catalog.map_central_repository.polygons")
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
	'Water (natural)',
	'Buildings with Relations Optimised',
	'Buildings w/o Relations Optimised',
	'LOI Artificial Ground',
	'--',
	'Admin Areas',
	'Admin Point Places',
	'Inland Water',
	'Ocean Water',
	'Land Use',
	'Buildings with parts',
	'Buildings with parts H3',
	'Buildings with relations',
	'Buildings (Old)',
	'EV_Charging',
	'Network with Speeds',
	'Network Major with Lanes, Curv, Grad',
	'Network Simple (for large areas)',
	'Network Elevation (h3)',
	'Network Junctions (h3)',
	'--',
	'All relations WIP (not relation_geometry) (linestring) (h3)',
	'Relations-Geometry (point) (h3)',
	'Relations-Geometry (line) (h3)',
	'Relations-Geometry (polygon) (h3)',
	'Lane Connectivity relations (h3)',
	'--',
	'Fire Stations',
	'Street Lamps (h3)',
	'Admin Places (polygon)',
	'Turn Restrictions',
	'Traffic Signs',

	'State',
	'Trees',

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
		fProcWaterNatural(extent_layer, product_version, license_zone, extentCoords, menu_name=process)
	elif process == 'Buildings with Relations Optimised':
		fProcBuilding_with_Relations_SpatialOptimised(product_version, license_zone, extentCoords, menu_name=process)
	elif process == 'Buildings w/o Relations Optimised':
		fProcBuilding_wo_Relations_SpatialOptimised(product_version, license_zone, extentCoords, menu_name=process)
	elif process == 'LOI Artificial Ground':
		fProcLoiArtificialGround(product_version, license_zone, extentCoords, menu_name=process)

	elif process == 'All Polygons Contain':
		fAllPolyContains(product_version, license_zone, extentCoords)
	elif process == 'All Polygons Intersect':
		fAllPolyIntersect(product_version, license_zone, extentCoords)
	elif process == 'Admin Areas':
		fProcessAdminAreas(extent_layer, product_version, license_zone, extentCoords, h3)
	elif process == 'Admin Point Places':
		fProcessPlacePoint(extent_layer, product_version, license_zone, extentCoords, h3)
	elif process == 'Inland Water':
		fProcessInlandWater(extent_layer, product_version, license_zone, extentCoords, h3)
	elif process == 'Ocean Water':
		fProcessOceanWater(extent_layer, product_version, license_zone, extentCoords, h3)
	elif process == 'Land Use':
		fProcessLandUse(extent_layer, product_version, license_zone, extentCoords, h3)
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
	elif process == 'Network Major with Lanes, Curv, Grad':
		fProcessNetworkMajor(product_version, license_zone, extentCoords)
	elif process == 'Network Simple (for large areas)':
		fProcessNetworkSimple(product_version, license_zone, extentCoords)
	elif process == 'Network Elevation (h3)':
		fProcessNetworkElevation(extent_layer, product_version, license_zone, extentCoords, h3)
	elif process == 'Network Junctions (h3)':
		fProcessNetworkJunctions(extent_layer, product_version, license_zone, extentCoords, h3)
	elif process == 'Street Lamps (h3)':
		fProcessSteetLamp(extent_layer, product_version, license_zone, extentCoords, h3)
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
		fProcessEV(product_version, license_zone, extentCoords)
	elif process == 'Fire Stations':
		fProcessFireStations(product_version, license_zone, extentCoords)
	elif process == 'Admin Places (polygon)':
		fAdminPlaces(product_version, license_zone, extentCoords)
	elif process == 'Turn Restrictions':
		fTurnRestrictions(product_version, license_zone, extentCoords)
	elif process == 'Traffic Signs':
		fTrafficSigns(product_version, license_zone, extentCoords)

	elif process == 'Trees':
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