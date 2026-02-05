# bad:
# [ "79 Avenue Henri Martin 75116 Paris, France", "5 Rue de Chaillot 75116 Paris, France", "35 Rue Vernet 75008 Paris, France", "26 Avenue Bosquet 75007 Paris, France", "48 Rue de Ponthieu 75008 Paris, France", "20 Boulevard de la Tour-Maubourg 75007 Paris, France" ]
# good:
# [ "79 Avenue Henri Martin 75116 Paris, France", "5 Rue de Chaillot 75116 Paris, France", "106 Rue Saint-Dominique 75007 Paris, France", "35 Rue Vernet 75008 Paris, France", "48 Rue de Ponthieu 75008 Paris, France", "20 Boulevard de la Tour-Maubourg 75007 Paris, France" ]


# Installing python plugins in QGIS:
# https://gis.stackexchange.com/questions/351280/installing-python-modules-for-qgis-3-on-mac

from qgis.core import *
from qgis.core import QgsDataSourceUri, QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY, QgsProject, QgsSimpleMarkerSymbolLayerBase, QgsSymbol, QgsPalLayerSettings, QgsTextFormat, QgsVectorLayerSimpleLabeling, QgsPrintLayout, QgsLayoutItemMap, QgsLayoutPoint
from qgis.utils import *
from qgis.PyQt.QtCore import QVariant, QRectF
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import (QWidget, QPushButton, QLineEdit, QInputDialog, QMessageBox, QListView, QListWidget, QLabel, QFileDialog)



import requests
import pandas as pd
import json
import time
from urllib.parse import quote

# import processing

# from qgis.PyQt.QtWidgets import (QWidget, QPushButton, QLineEdit, QInputDialog, QApplication, QLabel,QMessageBox)

# manually append script folder 'cause fucking QGIS
import imp
sys.path.append('d:/Work/OneDrive/Dev/Python/TT_Qgis_Workspace/MNR_automation')
import b9PyQGIS
imp.reload(b9PyQGIS)
from b9PyQGIS import *
mainWindow=iface.mainWindow()


def main(svrURL, strStateSchema, clipLayer, extentCoords):
	mnrServer = svrURL
	mnrSchema = strStateSchema
	print ("server is {}\ntable is {}\n".format(mnrServer, mnrSchema))
	
	# newLayer = fLoadTableBuildings(mnrServer,mnrSchema,extentCoords)
	# fSymbol(newLayer)
	# newLayer = fAddCoords()


def fExportPDFMain():
	print("Export to PDF")
	fProcessChoice()

def fProcessChoice():
	# read location coords from config file
	iniFile = os.path.dirname( imp.find_module('b9PyQGIS')[1] ) + "/" + 'b9QGISdata.ini'
	# print(iniFile)
	config = configparser.ConfigParser()
	config.read(iniFile)

	PDFProcess=[
		'RoadNetwork_DC',
		'LandUse',
		'Water',
		'Buildings',
		'---------',
		'Export Selected to PDFs',
		'Test'
	]

	lastProcess = config['export']['export_process']
	index = PDFProcess.index(lastProcess) if lastProcess in PDFProcess else 0
	choiceUtil, ok = QInputDialog.getItem(mainWindow, "pyQGIS", "Select Process:", PDFProcess, index, False)
	if ok:
		print("\nContinue: {}\nChoice: {}".format(ok, choiceUtil))
		config['export']['export_process'] = choiceUtil
		with open(iniFile, 'w') as configfile:
			config.write(configfile)
		functionString = fProcessSwitch(choiceUtil)

		functionSequence = functionString.split(",")
		# print(functionSequence)
		possibles = globals().copy()
		possibles.update(locals())
		for f in functionSequence: # test the functions
			func_name = f.strip()
			funcRun = possibles.get(func_name)
			if not funcRun:
				print("\n+++ ERROR: Function \"{}\" not found +++".format(func_name))
				return
		for f in functionSequence: # cleared to run
			func_name = f.strip()
			funcRun = possibles.get(func_name)
			result = funcRun()
			if result == 'error':
				print("+++ Error encountered +++")
				return
	print("=== Finished ===")

def fProcessSwitch(userinput):
	switch={
		'RoadNetwork_DC' : 'fRoadNetworkDisplayClass',
		'LandUse' : 'fConvertPoints_ToHip, fCleanFid',
		'Water' : 'fConvertPoints_ToHip, fCleanFid',
		'Buildings' : 'fConvertPoints_ToHip',
		'Export Selected to PDFs' : 'fExportPDF',
		'Test' : 'fTest'
	}
	return switch.get(userinput,"Invalid selection")

def fRoadNetworkDisplayClass():
	### Split an existing Network layer by Display_Class
	print('fRoadNetworkDisplayClass')
	layerGeo = iface.activeLayer() # this is to allow only export
	if layerGeo: 
		print(layerGeo)
	else:
		qtMsgBox("Make sure to select the network layer \nintended for PDF expot")
		return

	layerGeoId = layerGeo.id() # this is to allow only export
	layerGeoBaseName = layerGeo.name()
	layerGeoBaseName = "Network_"
	fieldToSeparate = "display_class"
	result = b9PyQGIS.fListUniqueVals(layerGeo,fieldToSeparate)
	unique_values_str = result['UNIQUE_VALUES']
	unique_values = unique_values_str.split(";")
	try:
		unique_values.remove("NULL")
	except ValueError:
		qtMsgBox("Make sure to select the network layer \nintended for PDF expot")
		return

	mapping_dict = {10 : "Motorway", 20 : "Major Road", 30 : "Other Major Road", 40 : "Secondary Road", 51 : "Local Connecting Road", 52 : "Local Road High", 60 : "Local Road", 70 : "Local Road Minor", 80 : "Other Road"}
	layers_displayClass : list = []

	for i in unique_values:
		int_i = int(float(i))
		name = mapping_dict.get(int_i)
		strExpression = ' "display_class" = {}'.format(int_i)
		result = fExtractByExpression(layerGeoId, strExpression)
		newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
		newLayer.setName(layerGeoBaseName + str(int_i) + "_" + name)
		layers_displayClass.append(newLayer)
	print(layers_displayClass)

	### read the INI file
	iniFile = os.path.dirname( imp.find_module('b9PyQGIS')[1] ) + "/" + 'b9QGISdata.ini'
	config = configparser.ConfigParser()
	config.read(iniFile)

	### Select PDF Extent layer
	extentLayer = iface.activeLayer()
	extentLayerName = config['mnr']['extentmnr']
	lstLayers = []
	lstLayerNames = []
	for layer in QgsProject.instance().mapLayers().values():
		lstLayers.append(layer)
	for layer in lstLayers:
		lstLayerNames.append(layer.name())
	intlayerIndex = lstLayerNames.index(extentLayerName) if extentLayerName in lstLayerNames else lstLayers.index(extentLayer)
	strInfo = "Looking for extent..."
	strChoice, ok = QInputDialog.getItem(mainWindow, "pyQGIS fLoad", strInfo, lstLayerNames, intlayerIndex, False)
	if ok:
		print(strChoice)
		intlayerIndex = lstLayerNames.index(strChoice)
		extentLayer = lstLayers[intlayerIndex]
		extentLayerName = extentLayer.name()
		config['mnr']['extentmnr'] = extentLayerName
		with open(iniFile, 'w') as configfile:
			config.write(configfile)
	else:
		print("Cancelled")
		return "cancel"

	### Select PDF Export Folder
	filePDFexport = config['export']['filePDFexport']
	fdir = qtDirectoryDialog(filePDFexport,caption="Select a folder")
	if fdir:
		print(fdir)
		config['export']['filePDFexport'] = fdir
		with open(iniFile, 'w') as configfile:
			config.write(configfile)
	else:
		print("Cancelled")
		return "cancel"

	### Export layers
	## Store layer visibility
	layer_states = fGetAllLayersVisibility()
	project = QgsProject.instance()
	root = project.layerTreeRoot()
	tree_layersIds = root.findLayerIds()
	layers_visible = [key for key, value in layer_states.items() if value==True]
	# print("layers_visible: {}".format(layers_visible))  # Output: ['apple', 'cherry']

	## Hide All
	fSetLayerVisibility(tree_layersIds, False)
	# qtMsgBox("Just waistin' some time")

	## print one by one
	for layer in layers_displayClass:
		layers_list = [layer.id()]
		fSetLayerVisibility(layers_list, True)
		fname=layer.name() + ".pdf"
		file_path = os.path.join(fdir, fname)
		# print(file_path)
		fExportPDF(layer, extentLayerName, file_path)
		fSetLayerVisibility(layers_list, False)

	## Restore visibility
	fSetLayerVisibility(layers_visible, True)
	## Delete DC layers
	for layer in layers_displayClass:
		QgsProject.instance().removeMapLayer(layer)


def fExportPDF(layer, extentLayerName, file_path):
	#get a reference to the layout manager
	project = QgsProject.instance()
	manager = project.layoutManager()

	# Get the layout that you want to delete
	layoutDel = manager.layoutByName("PDF_Export")  # replace with your layout name
	# Remove the layout
	if layoutDel:
		manager.removeLayout(layoutDel)

	#make a new print layout object
	layout = QgsPrintLayout(project)
	#needs to call this according to API documentaiton
	layout.initializeDefaults()
	#cosmetic
	layout.setName('PDF_Export')
	#add layout to manager
	manager.addLayout(layout)

	#create a map item to add
	itemMap = QgsLayoutItemMap.create(layout)

	itemMap.setRect(QRectF(0, 0, 100, 100))  # The Rectangle will be overridden below

	# Extent
	# canvas = iface.mapCanvas()
	# #set an extent to canvas
	# itemMap.setExtent(canvas.extent())

	# #get the extent from a layer
	extentLayer = QgsProject.instance().mapLayersByName(extentLayerName)[0]
	extent = extentLayer.extent()
	rectangle = QgsRectangle(extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum())
	itemMap.setExtent(rectangle)
	layout.addLayoutItem(itemMap)

	# Export to PDF
	exporter = QgsLayoutExporter(layout)
	exporter.exportToPdf(file_path, QgsLayoutExporter.PdfExportSettings())


def fTest():
	print("test")


def fLayerVisibiityTest():
	layer_states = fGetAllLayersVisibility()
	# print("layer_states: {} {}".format(len(layer_states), layer_states))
	project = QgsProject.instance()
	root = project.layerTreeRoot()
	tree_layersIds = root.findLayerIds()
	layers_visible = [key for key, value in layer_states.items() if value==True]
	print("layers_visible: {}".format(layers_visible))  # Output: ['apple', 'cherry']
	## Hide All
	fSetLayerVisibility(tree_layersIds, False)
	qtMsgBox("Just waistin' some time")
	## Restore visibility
	fSetLayerVisibility(layers_visible, True)


def fGetAllLayersVisibility():
	project = QgsProject.instance()
	root = project.layerTreeRoot()
	tree_layersIds = root.findLayerIds()
	layer_states = {}
	# print("tree_layersIds: {} {}".format(len(tree_layersIds), tree_layersIds))
	for layerId in tree_layersIds:
		node = root.findLayer(layerId)
		layer_states[layerId] = node.isVisible()
		# print("LayerId: {} | {}".format(layerId, node.isVisible()))
	return layer_states

def fSetLayerVisibility(layerIDs, visibility = True):
	project = QgsProject.instance()
	root = project.layerTreeRoot()
	tree_layersIds = root.findLayerIds()
	layer_states = {}
	# print("tree_layersIds: {} {}".format(len(tree_layersIds), tree_layersIds))
	for layerId in tree_layersIds:
		if layerId in layerIDs:
			layer = root.findLayer(layerId)
			# layer = QgsProject.instance().mapLayer(layer_id)
			layer.setItemVisibilityChecked(visibility)  # Set to True to make the layer visible

		# layer_states[layerId] = node.isVisible()
		# print("LayerId: {} | {}".format(layerId, node.isVisible()))
	# return layer_states







def fTTWaypointOptimizationMain():
	print("TT API access")

	# read location coords from config file
	iniFile = os.path.dirname( imp.find_module('b9PyQGIS')[1] ) + "/" + 'b9QGISdata.ini'
	print(iniFile)
	config = configparser.ConfigParser()
	config.read(iniFile)
	ttkey = config['common']['ttkey']

	### UI - Get list of waypoints addresses, starting with first
	waypoints = config['common']['waypoints']
	# print("Saved waypoints: {}".format(waypoints))
	result = b9PyQGIS.qtInputDlg("Give me space delimited waypoint list,\nFirst point is the starting location.\nExample: [\"Addr1\" \"Addr2\"]", waypoints)
	config['common']['waypoints'] = result
	with open(iniFile, 'w') as configfile:
		config.write(configfile)
	addresses = json.loads(result)
	
	### API Geocode all addresses to lon-lat, display on map
	addressesLonLat = fGeocodeAdd2Coord(addresses, ttkey)
	# print(addressesLonLat, ttkey)

	# ### Run API query to optimize waypoint order and reorder the LonLat coordinates
	# addressesLonLat_optimized = fWaypointOptimization(addressesLonLat)

	# Run Adam's API query to build routes from the first one
	fRouting(addressesLonLat, addresses)

	### parse information 
	### put it on a layer


# API Geocode list of addresses to list of lon-lat coords
def fGeocodeAdd2Coord(addresses, ttkey):
	print("==geocode original entrypoints===")
	addressesLonLat = []
	for address in addresses:
		time.sleep(.1) #introduse a bit of wait between requests, otherwise API times out
		encoded_address = quote(address)
		# print(encoded_address)
		url = "https://api.tomtom.com/search/2/geocode/{}.json?key={}".format(encoded_address, ttkey)
		response = requests.get(url)

		if response.status_code == 200:
				try:
						data = response.json()
						print(json.dumps(data, indent=4))
						result = data['results'][0]  # Get the first result
						apt_position = result['position']
						entry_point = result['entryPoints'][0]["position"]
						addressesLonLat.append(entry_point)
				except json.JSONDecodeError:
						print("Error parsing JSON")
						qtMsgBox("Error parsing JSON: {}".format(address))
		else:
				if response.status_code == 400: responce_txt = "Bad request"
				elif response.status_code == 404: responce_txt = "Not found: Request path is incorrect"
				elif response.status_code == 429: responce_txt = "Too many requests: Too many requests were sent in a given amount of time for the supplied API Key."
				elif response.status_code == 500: responce_txt = "Internal Server Error: The service cannot handle the request right now, an unexpected condition has occurred."
				elif response.status_code == 503: responce_txt = "Service Unavailable: The service cannot handle the request right now, this is certainly a temporary state."

				print("Error status code: {}\n{}".format(response.status_code, responce_txt))
				qtMsgBox("Error status code: {}\n{}".format(response.status_code, responce_txt))

	print("===AddressLatLon======")
	print(addressesLonLat)

	# build 'waypoints' json for request body
	data_waypoints = {"waypoints": []}
	for point in addressesLonLat:
		waypoint = {
			"point": {
				"longitude": point['lon'],
				"latitude": point['lat']
			}
		}
		data_waypoints["waypoints"].append(waypoint)

	# json_string = json.dumps(json_structure)
	# print(json_string)
	print("===waypoint original request===")
	print(json.dumps(data_waypoints, indent=4))
	print("data_waypoints: {}".format(data_waypoints))
	print("addresses: {}".format(addresses))
	fJSON2PointLayer(data_waypoints, addresses, "Waypoints_Org", "red")

	return addressesLonLat


# Load JSON points into a new layer
def fJSON2PointLayer(waypoints_json, addresses, layer_name, color):
	# Create a new memory layer
	layer = QgsVectorLayer("Point", layer_name, "memory")

	# Get the data provider
	provider = layer.dataProvider()

	provider.addAttributes([QgsField("id", QVariant.Double),
										QgsField("address", QVariant.String)])
	layer.updateFields() 

	# Start editing the layer
	layer.startEditing()

	# For each waypoint, create a new feature and add it to the layer
	for i, waypoint in enumerate(waypoints_json["waypoints"]):
		feature = QgsFeature()

		# Set the feature's geometry
		lon = waypoint["point"]["longitude"]
		lat = waypoint["point"]["latitude"]
		feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
		feature.setAttributes([i, addresses[i]])

		# Add the feature to the layer
		provider.addFeature(feature)

	# Commit the changes
	layer.commitChanges()

	# Add the layer to the map
	QgsProject.instance().addMapLayer(layer)

	fLayerStyle(layer, color)
	fLayerLabel(layer)


def fLayerStyle(layer, color):
	# layer = QgsProject.instance().mapLayersByName('Waypoints')[0]
	renderer = layer.renderer()
	symbol = renderer.symbol()
	symbol_layer = symbol.symbolLayer(0)
	if isinstance(symbol_layer, QgsSimpleMarkerSymbolLayerBase):
		symbol_layer.setSizeUnit(QgsUnitTypes.RenderPoints)
		symbol_layer.setColor(QColor(color))
		symbol_layer.setSize(5)
	symbol.changeSymbolLayer(0, symbol_layer)
	layer.triggerRepaint()

def fLayerLabel(layer):
	# layer = QgsProject.instance().mapLayersByName('Waypoints')[0]
	label_settings = QgsPalLayerSettings()
	label_settings.fieldName = '"id" || \'\\n\' || "address"'
	label_settings.multilineAlign = QgsPalLayerSettings.MultiFollowPlacement
	text_format = QgsTextFormat()
	text_format.setSize(10)
	text_format.setSizeUnit(QgsUnitTypes.RenderPoints)
	label_settings.setFormat(text_format)
	labeling = QgsVectorLayerSimpleLabeling(label_settings)
	layer.setLabeling(labeling)
	layer.setLabelsEnabled(True)
	layer.triggerRepaint()


def fRouting(addressesLonLat, addresses):

	# Loop the addresses to finish at the start point
	addresses_closed_loop = addresses
	addresses_closed_loop.append(addresses[0])
	# Loop the addresses_LonLan to finish at the start point
	addressesLonLat_closed_loop = addressesLonLat
	addressesLonLat_closed_loop.append(addressesLonLat[0])

	# print("addressesLonLat_closed_loop: \n{}".format(addressesLonLat_closed_loop))
	# print("addressesLonLat: {}".format(addressesLonLat))

	# options = {
	# "travelMode": "truck",
	# "vehicleMaxSpeed": 50,
	# "departAt": "2024-10-26T09:00:00-04:00"
	# }

	iniFile = os.path.dirname( imp.find_module('b9PyQGIS')[1] ) + "/" + 'b9QGISdata.ini'
	config = configparser.ConfigParser()
	config.read(iniFile)
	options_string = config['common']['route_options']

	# Convert the JSON object to a string
	# options_string = json.dumps(options, indent=4)
	options_string_edit = qtInputDlgMultiline("question", options_string)
	print("options_string_edit: \n{}".format(options_string_edit))
	config['common']['route_options'] = options_string_edit
	with open(iniFile, 'w') as configfile:
		config.write(configfile)

	# Convert the string back to a JSON object
	options = json.loads(options_string_edit)

	data_request = {"waypoints": []}

	# create the waipoints object
	for point in addressesLonLat_closed_loop:
		waypoint = {
			"point": {
				"longitude": point['lon'],
				"latitude": point['lat']
			}
		}
		data_request["waypoints"].append(waypoint)
		# print("data_request: \n{}".format(data_request))

	data_request["options"] = options
	print("===request body===")
	print(json.dumps(data_request, indent=4))

	# Adam Routing url
	url = "https://waypoint-optimization.azurewebsites.net/api/optimizedRoute"

	# Send a POST request to the API
	response = requests.post(url, json=data_request)
	# response = requests.post(url, json=body)
	if response.status_code == 200:
		try:
				data_responce = response.json()
				print("===adam waypoint opt=======")
				print(json.dumps(data_responce, indent=4))
				# result = data['results'][0]  # Get the first result
				# apt_position = result['position']
				# entry_point = result['entryPoints'][0]["position"]
				# addressesLatLon.append(entry_point)
		except json.JSONDecodeError:
				print("Error parsing JSON")
	else:
			print("Error status code: ", response.status_code)

	print("optimizedOrder: \n{}".format(data_responce["optimizedOrder"]))

	optimized_order = data_responce["optimizedOrder"]
	print("addressesLonLat_closed_loop {}".format(addressesLonLat_closed_loop))
	# # Rearrange the points according to the optimized order
	addressesLonLat_optimized = [addressesLonLat_closed_loop[i] for i in optimized_order]
	print("addressesLonLat_optimized {}".format(addressesLonLat_optimized))
	addresses_optimized = [addresses_closed_loop[i] for i in optimized_order]
	print("addresses_optimized {}".format(addresses_optimized))

	# data_optimized_waypoints = {"waypoints": []}
	# data_optimized_waypoints["waypoints"].append(addressesLonLat_optimized)
	data_optimized_waypoints = {"waypoints":addressesLonLat_optimized}
	
	print("data_optimized_waypoints: {}".format(data_optimized_waypoints))
	print("addresses_optimized: {}".format(addresses_optimized))

	# Reconfigure the waypoints
	data_optimized_waypoints_fix = {'waypoints': []}

	# Reconfigure the waypoints
	for waypoint in data_optimized_waypoints['waypoints']:
			lat = waypoint['lat']
			lon = waypoint['lon']
			data_optimized_waypoints_fix['waypoints'].append({'point': {'latitude': lat, 'longitude': lon}})

	print(data_optimized_waypoints_fix)

	# Add layer with rearranged waypoints
	fJSON2PointLayer(data_optimized_waypoints_fix, addresses_optimized, "Waypoints_Optimized", "blue")






# Run Waypoint API query to optimize waypoint order
def fWaypointOptimization(points):
	json_structure = {"waypoints": []}

	for point in points:
		waypoint = {
			"point": {
				"longitude": point['lon'],
				"latitude": point['lat']
			}
		}
		json_structure["waypoints"].append(waypoint)

	json_string = json.dumps(json_structure)
	# print(json_string)
	print("===waypoint optimization request===")
	print(json.dumps(json_structure, indent=4))
	fJSON2PointLayer(json_structure)

	url = "https://api.tomtom.com/routing/waypointoptimization/1?key=GgqZsRtAJ8ANAalBNGneVGqOzPUhjWKL"

	# Send a POST request to the API
	response = requests.post(url, json=json_structure)
	# response = requests.post(url, json=body)
	if response.status_code == 200:
		try:
				data = response.json()
				print("===waypoint opt=======")
				print(json.dumps(data, indent=4))
				# result = data['results'][0]  # Get the first result
				# apt_position = result['position']
				# entry_point = result['entryPoints'][0]["position"]
				# addressesLatLon.append(entry_point)
		except json.JSONDecodeError:
				print("Error parsing JSON")
	else:
			print("Error status code: ", response.status_code)

	print(points)
	optimized_order = data["optimizedOrder"]
	# Rearrange the points according to the optimized order
	optimized_points = [points[i] for i in optimized_order]

	print(optimized_points)
	return optimized_points


# Open the file
# import json
# fileIn = '/Users/dunevv/OneDrive/Dev/Python/TT_Qgis/TomTomAPI/Api2QGIS/responce.json'
fileOut = '/Users/dunevv/OneDrive/Dev/Python/TT_Qgis/TomTomAPI/Api2QGIS/responce_forQGIS.geojson'
def fResponce2QJSON(data):
	# with open(fileIn, 'r') as f:
	# # Load JSON data from file
	# data = json.load(f)
	x = data.keys()

	dataOut = {
		"type": "FeatureCollection",
		"name": "Api2Qgis_geoJSON",
		"features": []
		}

	# parse the routes
	for i, key in enumerate(data['routes'][0]['legs']):
	# for key in data['routes'][0]['legs']:

		# print('=== key {} ==='.format(i))
		# print(key['points'])
		feature = {
			"type": "Feature",
			"properties": {
				"Name": 0
			},
			"geometry": {"type": "LineString"}
		}
		# print("==keycoord==")
		coordinates = []
		for keycoord in key['points']:
			coord = [keycoord['lng'],keycoord['lat']]
			coordinates.append(coord)
			# print(coord)
		# print("==end keycoord==")
		# print(coordinates)


	feature["properties"]["Leg"] = i
	feature["properties"].update(key['summary']) 
	# feature["geometry"]["coordinates"] = key['points']
	feature["geometry"]["coordinates"] = coordinates
	dataOut["features"].append(feature)
	# print('==endkey===')


	# Convert Python object to JSON string
	json_str = json.dumps(dataOut)
	# print(json_str)

	# Write Python object to JSON file
	with open(fileOut, 'w') as f:
		json.dump(dataOut, f)







def fGetExtentCoords():
	root = QgsProject.instance().layerTreeRoot()

	layerGeoInit = iface.activeLayer() # get current layer
	layerGeoId = layerGeoInit.id() # get current layer
	layerGeoBaseName = layerGeoInit.name()

	# Reproject Extent layer:
	print('Reproject layer...')
	epsgString = '4326'
	result = b9PyQGIS.fReprojectLayer(layerGeoId, epsgString)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_' + epsgString)
	layerGeoId = newLayer.id()

	# Reproject Extent layer:
	print('Extract Vertices...')
	result = b9PyQGIS.fExtractVertices(layerGeoId)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_vertices')
	QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()

	# Reproject Extent layer:
	print('Add geometry attibs...')
	result = b9PyQGIS.fAddGeometryAttribs(layerGeoId)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_coords')
	QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()

	# Select corner coordinates
	print('Cordinates...')

	# layer = QgsProject.instance().mapLayer(layerGeoId)
	idx = newLayer.fields().indexOf('xcoord')
	print(newLayer.uniqueValues(idx))
	xLength = len(newLayer.uniqueValues(idx))
	xMax = max(newLayer.uniqueValues(idx))
	xMin = min(newLayer.uniqueValues(idx))
	idx = newLayer.fields().indexOf('ycoord')
	print(newLayer.uniqueValues(idx))
	yMax = max(newLayer.uniqueValues(idx))
	yMin = min(newLayer.uniqueValues(idx))

	sBlenderOSM = str(xMin) + "," + str(yMin) + "," + str(xMax) + "," + str(yMax)
	print( "set length is {}, \nxMax is {}, xMin is {}, \nyMax is {}, yMin is {}".format(xLength, xMax,xMin,yMax,yMin) )
	print( "Coordinates to paste to BlenderOSM are:\n{}".format(sBlenderOSM) )
	QgsProject.instance().removeMapLayer(layerGeoId)

		# set active layer
	iface.setActiveLayer(layerGeoInit)


def fAddCentroid():
	root = QgsProject.instance().layerTreeRoot()

	layerGeoId = iface.activeLayer().id() # get current layer
	layerGeoBaseName = iface.activeLayer().name()

	# Add centroid point:
	print('Adding centroid...')
	result = b9PyQGIS.fAddCentroidPoint(layerGeoId)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_AddCentroid')
	layerGeo = root.findLayer(layerGeoId)
	# QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()


	# Add Meters coordinate to points:
	print('Adding XY positions in meters...')
	result = b9PyQGIS.fAddMeterCoordinate(layerGeoId,"centroidMeters")
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_CentroidXYmeters')
	layerGeo = root.findLayer(layerGeoId)
	QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()
	return newLayer

def fGetUTMcentroid():
	root = QgsProject.instance().layerTreeRoot()

	layerGeoInit = iface.activeLayer() # get current layer
	layerGeoId = layerGeoInit.id() # get current layer
	layerGeoBaseName = layerGeoInit.name()

	# Add centroid point:
	print('Adding centroid...')
	result = b9PyQGIS.fAddCentroidPoint(layerGeoId)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_AddCentroid')
	layerGeo = root.findLayer(layerGeoId)
	# QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()


	# Add Meters coordinate to points:
	print('Adding XY positions in meters...')
	result = b9PyQGIS.fAddMeterCoordinate(layerGeoId,"centroidMeters")
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_CentroidXYmeters')
	layerGeo = root.findLayer(layerGeoId)
	QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()

	# Reproject Extent layer:
	print('Reproject layer WGT84 ...')
	epsgString = '4326'
	result = b9PyQGIS.fReprojectLayer(layerGeoId, epsgString)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_' + epsgString)
	QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()

	# Calculate UTM
	print('Calculating UTM...')
	strFieldName = 'UTM'
	strFormula = ' utm($y, $x) \r\n'
	iFieldType = 2
	iFieldLength = 0
	iFieldPrecision = 0
	result = b9PyQGIS.fFieldCalc(layerGeoId, strFieldName, strFormula, iFieldType, iFieldLength, iFieldPrecision)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_UTM')
	QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()

	idx = newLayer.fields().indexOf('fieldName')
	value = newLayer.getFeature(1).attribute(idx)
	value = value.strip("Point (") #strip beginning
	value = value.strip(")") #strip end
	lstValues = value.split(" ") #strip end
	print("Centroid Coordinate is: {}, {}".format(lstValues[0], lstValues[1]))


	idx = newLayer.fields().indexOf('UTM')
	value = newLayer.getFeature(1).attribute(idx)
	utm = value[0:3]
	print("UTM Zone is: {}".format(utm))
	QgsProject.instance().removeMapLayer(layerGeoId)

	# print(utm[2])
	# # Reproject Extent layer:
	# print('Reproject layer...')
	# if utm[2] == "N":
	# 	epsgString = '326' + utm[0:2]
	# elif utm[2] == "S":
	# 	epsgString = '327' + utm[0:2]
	# else:
	# 	epsgString = "Invalid UTM"
	# print("Reproject Extent layer with epsg{}".format(epsgString))
	# result = b9PyQGIS.fReprojectLayer(layerGeoId, epsgString)
	# newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	# newLayer.setName(layerGeoBaseName + '_' + epsgString)
	# layerGeoId = newLayer.id()

	# set active layer
	iface.setActiveLayer(layerGeoInit)

def fAddChainagePointsOFF():
	layerGeoInit = iface.activeLayer() # get current layer
	layerGeoId = layerGeoInit.id() # get current layer
	layerGeoBaseName = layerGeoInit.name()

	result = b9PyQGIS.fPointsAlongLines(layerGeoId)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_chainage')

def fEPsFromMNR():
	root = QgsProject.instance().layerTreeRoot()

	layerGeoInit = iface.activeLayer() # get current layer
	layerGeoId = layerGeoInit.id() # get current layer
	layerGeoBaseName = layerGeoInit.name()

	# Get simplified bounding geometry:
	print('Get bounds ...')
	result = b9PyQGIS.fBoundingGeometry(layerGeoId)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_minBounds')
	# QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()

	# Add centroid point:
	print('Adding centroid...')
	result = b9PyQGIS.fAddCentroidPoint(layerGeoId)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_AddCentroid')
	layerGeo = root.findLayer(layerGeoId)
	QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()

	# Add Meters coordinate to points:
	print('Adding XY positions in meters...')
	result = b9PyQGIS.fAddMeterCoordinate(layerGeoId,"centroidMeters")
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_CentroidXYmeters')
	layerGeo = root.findLayer(layerGeoId)
	QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()

	# Reproject Extent layer:
	print('Reproject layer WGT84 ...')
	epsgString = '4326'
	result = b9PyQGIS.fReprojectLayer(layerGeoId, epsgString)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_' + epsgString)
	QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()

	# Calculate UTM
	print('Calculating UTM...')
	strFieldName = 'UTM'
	strFormula = ' utm($y, $x) \r\n'
	iFieldType = 2
	iFieldLength = 0
	iFieldPrecision = 0
	result = b9PyQGIS.fFieldCalc(layerGeoId, strFieldName, strFormula, iFieldType, iFieldLength, iFieldPrecision)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_UTM')
	QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()

	idx = newLayer.fields().indexOf('UTM')
	value = newLayer.getFeature(1).attribute(idx)
	utm = value[0:3]
	message = "UTM Zone:\n\n{}\n".format(utm)
	print(message)
	QgsProject.instance().removeMapLayer(layerGeoId)

	qtMsgBox(message)

	# set active layer
	iface.setActiveLayer(layerGeoInit)


	print('Reproject layer to user selected coord system ...')
	result = processing.execAlgorithmDialog('native:reprojectlayer')
	# Can take parameters to prefill the GUI fields
	# processing.execAlgorithmDialog('native:buffer', parameters= {'INPUT':iface.activeLayer(),'DISTANCE':10,'SEGMENTS':5,'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,'DISSOLVE':False,'OUTPUT':'TEMPORARY_OUTPUT'})

	layerGeoId = result['OUTPUT']
	print(layerGeoId)
	newLayer = root.findLayer(layerGeoId)
	print(newLayer)
	newLayer.setName(layerGeoBaseName + '_reproject')
	# QgsProject.instance().removeMapLayer(layerGeoId)
	# layerGeoId = newLayer.id()

	# Add chainage points:
	print('Add chainage points ...')
	result = b9PyQGIS.fPointsAlongLines(layerGeoId)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_EPs')
	QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()



def fReprojectUTM():
	root = QgsProject.instance().layerTreeRoot()

	layerGeoInit = iface.activeLayer() # get current layer
	layerGeoId = layerGeoInit.id() # get current layer
	layerGeoBaseName = layerGeoInit.name()

	# Get simplified bounding geometry:
	print('Get bounds ...')
	result = b9PyQGIS.fBoundingGeometry(layerGeoId)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_minBounds')
	# QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()

	# Add centroid point:
	print('Adding centroid...')
	result = b9PyQGIS.fAddCentroidPoint(layerGeoId)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_AddCentroid')
	layerGeo = root.findLayer(layerGeoId)
	QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()

	# Add Meters coordinate to points:
	print('Adding XY positions in meters...')
	result = b9PyQGIS.fAddMeterCoordinate(layerGeoId,"centroidMeters")
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_CentroidXYmeters')
	layerGeo = root.findLayer(layerGeoId)
	QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()

	# Reproject Extent layer:
	print('Reproject layer WGT84 ...')
	epsgString = '4326'
	result = b9PyQGIS.fReprojectLayer(layerGeoId, epsgString)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_' + epsgString)
	QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()

	# Calculate UTM
	print('Calculating UTM...')
	strFieldName = 'UTM'
	strFormula = ' utm($y, $x) \r\n'
	iFieldType = 2
	iFieldLength = 0
	iFieldPrecision = 0
	result = b9PyQGIS.fFieldCalc(layerGeoId, strFieldName, strFormula, iFieldType, iFieldLength, iFieldPrecision)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_UTM')
	QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()

	idx = newLayer.fields().indexOf('UTM')
	value = newLayer.getFeature(1).attribute(idx)
	utm = value[0:3]
	message = "UTM Zone:\n\n{}\n".format(utm)
	print(message)
	QgsProject.instance().removeMapLayer(layerGeoId)

	qtMsgBox(message)

	# set active layer
	iface.setActiveLayer(layerGeoInit)


	print('Reproject layer to user selected coord system ...')
	result = processing.execAlgorithmDialog('native:reprojectlayer')
	# Can take parameters to prefill the GUI fields
	# processing.execAlgorithmDialog('native:buffer', parameters= {'INPUT':iface.activeLayer(),'DISTANCE':10,'SEGMENTS':5,'END_CAP_STYLE':0,'JOIN_STYLE':0,'MITER_LIMIT':2,'DISSOLVE':False,'OUTPUT':'TEMPORARY_OUTPUT'})

	layerGeoId = result['OUTPUT']
	print(layerGeoId)
	newLayer = root.findLayer(layerGeoId)
	print(newLayer)
	newLayer.setName(layerGeoBaseName + '_reproject')
	# QgsProject.instance().removeMapLayer(layerGeoId)
	# layerGeoId = newLayer.id()



# 326 -> N + UTM
# 327 -> S + UTM