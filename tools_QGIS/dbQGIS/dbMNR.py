# MNR query collection, new version 

# append script folder
import os, sys
current_script_dir = os.path.dirname(os.path.abspath(__file__))
# print("Current script's directory:", current_script_dir)
# Add parent dir for legacy imports
sys.path.append(os.path.dirname(current_script_dir))
# Also add local 'modules' folder (contains sub_* helper modules) so imports like sub_MNR_Buildings work
modules_dir = os.path.join(current_script_dir, 'modules')
if os.path.isdir(modules_dir):
	# put modules dir at front so it shadows any system installs if needed
	sys.path.insert(0, modules_dir)
	# sanity check: report missing expected helpers (helps debug import problems)
	expected_helpers = [
		'sub_MNR_Buildings.py','sub_MNR_AdminArea.py','sub_MNR_PostalDistricts.py','sub_MNR_OtherAreas.py','sub_MNR_APTs.py',
		'sub_MNR_CityCenters.py','sub_MNR_LandUse.py','sub_MNR_Maneuver.py','sub_MNR_TrafficSign.py','sub_MNR_TrafficLight.py',
		'sub_MNR_NetworkZ.py','sub_MNR_NetworkZ_uuid.py','sub_MNR_NetworkZ_GSC.py','sub_MNR_POIs.py','sub_MNR_EVs.py',
		'sub_MNR_EVs2.py','sub_MNR_EVsDBeaver.py','sub_MNR_SpeedProfilesZ.py','sub_MNR_SpeedProfiles.py','sub_MNR_TrafficSpeed.py',
		'sub_MNR_Curvature.py','sub_MNR_Water.py','sub_Add_Centroid.py'
	]
	missing_helpers = [h for h in expected_helpers if not os.path.exists(os.path.join(modules_dir, h))]
	if missing_helpers:
		print(f"Warning: missing helper modules in {modules_dir}: {missing_helpers}")
import imp

from unittest import result
import b9PyQGIS
imp.reload(b9PyQGIS)
from b9PyQGIS import *

import sub_MNR_Buildings
imp.reload(sub_MNR_Buildings)
from sub_MNR_Buildings import *

import sub_MNR_AdminArea
imp.reload(sub_MNR_AdminArea)
from sub_MNR_AdminArea import *

import sub_MNR_PostalDistricts
imp.reload(sub_MNR_PostalDistricts)
from sub_MNR_PostalDistricts import *

import sub_MNR_OtherAreas
imp.reload(sub_MNR_OtherAreas)
from sub_MNR_OtherAreas import *

import sub_MNR_APTs
imp.reload(sub_MNR_APTs)
from sub_MNR_APTs import *

import sub_MNR_CityCenters
imp.reload(sub_MNR_CityCenters)
from sub_MNR_CityCenters import *

import sub_MNR_LandUse
imp.reload(sub_MNR_LandUse)
from sub_MNR_LandUse import *

import sub_MNR_Maneuver
imp.reload(sub_MNR_Maneuver)
from sub_MNR_Maneuver import *

import sub_MNR_TrafficSign
imp.reload(sub_MNR_TrafficSign)
from sub_MNR_TrafficSign import *

import sub_MNR_TrafficLight
imp.reload(sub_MNR_TrafficLight)
from sub_MNR_TrafficLight import *

import sub_MNR_NetworkZ
imp.reload(sub_MNR_NetworkZ)
from sub_MNR_NetworkZ import *

import sub_MNR_NetworkZ_uuid
imp.reload(sub_MNR_NetworkZ_uuid)
from sub_MNR_NetworkZ_uuid import *

import sub_MNR_NetworkZ_GSC
imp.reload(sub_MNR_NetworkZ_GSC)
from sub_MNR_NetworkZ_GSC import *

import sub_MNR_POIs
imp.reload(sub_MNR_POIs)
from sub_MNR_POIs import *

import sub_MNR_EVs
imp.reload(sub_MNR_EVs)
from sub_MNR_EVs import *

import sub_MNR_EVs2
imp.reload(sub_MNR_EVs2)
from sub_MNR_EVs2 import *

import sub_MNR_EVsDBeaver
imp.reload(sub_MNR_EVsDBeaver)
from sub_MNR_EVsDBeaver import *

import sub_MNR_SpeedProfilesZ
imp.reload(sub_MNR_SpeedProfilesZ)
from sub_MNR_SpeedProfilesZ import *

import sub_MNR_SpeedProfiles
imp.reload(sub_MNR_SpeedProfiles)
from sub_MNR_SpeedProfiles import *

import sub_MNR_TrafficSpeed
imp.reload(sub_MNR_TrafficSpeed)
from sub_MNR_TrafficSpeed import *

import sub_MNR_Curvature
imp.reload(sub_MNR_Curvature)
from sub_MNR_Curvature import *

import sub_MNR_Water
imp.reload(sub_MNR_Water)
from sub_MNR_Water import *

import sub_Add_Centroid
imp.reload(sub_Add_Centroid)
from sub_Add_Centroid import *


# VARIABLES
layerGeoId = ""
layerAttrId = ""
extentCoords = ""
dropLineList = []
# clipLayer = iface.activeLayer()
# clipLayerName = "" #clipLayer.name()

geomField = "geom"

commonLayers = []
root = QgsProject.instance().layerTreeRoot()
mainWindow=iface.mainWindow()

# read location coords from config file
iniFile = os.path.dirname( imp.find_module('b9PyQGIS')[1] ) + "/" + 'b9QGISdata.ini'
config = configparser.ConfigParser()
config.read(iniFile)

# =======




def fSchemaQuery(server, mnrPort, mnrdb, mnrUsr, mnrPwd):
	strQuery =  \
		"SELECT schema_name FROM information_schema.schemata"
	arrFields=['schema_name']
	lstResults = b9PyQGIS.fReadPostgresRecordStrings(server, mnrPort, mnrdb, mnrUsr, mnrPwd, strQuery, arrFields)
	# print("\n-- Schemas on {}".format(strResults))
	return(lstResults)

def fQueryRegions(source):
		lstRegions = []
		lstError = []
		for item in source:
			if item[0:3] == "_20":
				lstRegions.append(item[13:16])
			else:
				lstError.append(item)
		print("Errors in schema list: {}".format(lstError))
		lstRegionsUnique = list(set(lstRegions))
		lstRegionsUnique.sort()
		return lstRegionsUnique

def fSelectState(lstSchemas, strRegion, iniSelectors):
	lstStates = []
	for i in lstSchemas:
		region = i[13:16]
		if region == strRegion:
				lstStates.append(i)

	elem = ""
	lstRegionStates = iniSelectors.split(",")
	for i in range(0,len(lstRegionStates)):
		lstRecord = lstRegionStates[i].split(":")
		strIniRegion = lstRecord[0]
		if strIniRegion == strRegion:
			print("Found saved Ini Region: {}".format(strIniRegion))
			elem = lstRecord[1]
			index = lstStates.index(elem) if elem in lstStates else 0
			choiceState, ok = QInputDialog.getItem(mainWindow, "pyQGIS Region", "Select MNR State:", lstStates, index, False)
			if ok == True:
				lstRecord[1] = choiceState
				lstRegionStates[i] = ":".join(lstRecord)
				strFromLstRegionStates = ",".join(lstRegionStates)
				config['mnr']['selectors'] = strFromLstRegionStates
				with open(iniFile, 'w') as configfile:
					config.write(configfile)
			else:
				choiceState = "cancel"
			break
	if elem != "":
		print("selected {}".format(choiceState))
	else:
		print("Didnt find saved Ini Region")
		index = 0
		choiceState, ok = QInputDialog.getItem(mainWindow, "pyQGIS Region", "Select MNR State:", lstStates, index, False)
		if ok == True:
			lstRecord = [strRegion,choiceState]
			lstRegionStates.append(":".join(lstRecord))
			strFromLstRegionStates = ",".join(lstRegionStates)
			print(strFromLstRegionStates)
			config['mnr']['selectors'] = strFromLstRegionStates
			with open(iniFile, 'w') as configfile:
				config.write(configfile)
		else:
			choiceState = "cancel"
	return choiceState


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


def fLoad(serv, schema):
	clipLayer = iface.activeLayer()
	clipLayerName = config['mnr']['extentmnr']
	lstLayers = []
	lstLayerNames = []
	# lstLayerNames.sort()
	print ("ini clipName: {}, selected clip layer: {}".format(clipLayerName,clipLayer))

	for layer in QgsProject.instance().mapLayers().values():
		lstLayers.append(layer)
	
	lstLayers.sort(key=lambda layer: layer.name().lower())

	for layer in lstLayers:
		lstLayerNames.append(layer.name())

	intlayerIndex = lstLayerNames.index(clipLayerName) if clipLayerName in lstLayerNames else lstLayers.index(clipLayer)
	strInfo = "Database: \nServer:    {} \nRelease:   {}  \n\nExtent layer:".format(serv,schema)
	strChoice, ok = QInputDialog.getItem(mainWindow, "pyQGIS fLoad", strInfo, lstLayerNames, intlayerIndex, False)
	if ok:
		print(f"String Choice: {strChoice}")
		intlayerIndex = lstLayerNames.index(strChoice)
		clipLayer = lstLayers[intlayerIndex]
		clipLayerName = clipLayer.name()

		config['mnr']['extentmnr'] = clipLayerName
		with open(iniFile, 'w') as configfile:
			config.write(configfile)

		return(clipLayer)
	else:
		return('cancel')

# == Get Extent coordinates ==
def fGetExtentCoords(clipLayer):
	global extentCoords
	layerClipID = clipLayer.id()
	layerClipName = clipLayer.name()
	print("clip layer: {}\nlayer id: {}\nlayer name: {}".format(clipLayer, layerClipID, layerClipName))

	# Reproject Extent layer:
	print('Reproject layer...')
	epsgString = '4326'
	result = b9PyQGIS.fReprojectLayer(layerClipID, epsgString)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerClipName + '_' + epsgString)
	layerClipID = newLayer.id()

	# Calc WKT geometry of the Extent layer
	strFieldName = 'wkt'
	strFormula = 'geom_to_wkt( $geometry )'
	iFieldType = 2
	iFieldLength = 0
	iFieldPrecision = 0
	result = b9PyQGIS.fFieldCalc(layerClipID, strFieldName, strFormula, iFieldType, iFieldLength, iFieldPrecision)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerClipName + '_WKT')
	QgsProject.instance().removeMapLayer(layerClipID)
	layerClipID = newLayer.id()
	layer = newLayer

	# Get Extent as polygon 
	selectid = [1]
	layer.select(selectid)
	# features = layer.getFeatures()
	selFeatures = layer.getSelectedFeatures()
	for feature in selFeatures:
			extentCoords = feature['wkt'] 
			# print(extentCoords)
	layer.removeSelection()
	QgsProject.instance().removeMapLayer(layerClipID)
	return extentCoords

def fMainUIMNR():

	processOptions=[
	# 'Admin Areas Brute',
	'Admin Areas',
	'Admin Areas Population',
	'Postal Districts',
	'Postal Districts with Names',
	'Census Areas',
	"Other Areas",
	'City Centers',
	'Address Points',
	'Buildings',
	'Land Use',
	'Maneuver',
	'Traffic Sign',
	'Traffic Light',
	"POIs",
	"EV Charge Stations",
	"EV Charge Stations v2",
	"EV Charge Stations v3 dBeaver",
	"NetworkZ GSC Lines",
	"NetworkZ GSC Points",
	"NetworkZ Elevation (Old)",
	"NetworkZ UUID (Old)",
	"NetworkZ Speed Profile (Old)",
	"Speed Profile (Old)",
	"Speed Profiles Arrays Wednesday",
	"Speed Profiles Arrays - Select day of week",
	"Traffic Speed",
	"ADA curvature",
	'Water',
	'Add Centroid'
	] 

	# dirCommonGeopack = config['directories']['dirCommonGeopack']
	# clipLayerName = config['mnr']['extentmnr']
	caprod01 = config['mnr']['caprod01']
	caprod02 = config['mnr']['caprod02']
	caprod05 = config['mnr']['caprod05']
	caprod06 = config['mnr']['caprod06']
	mnrPort = config['mnr']['mnrport']
	mnrdb = config['mnr']['mnrdb']
	mnrUsr = config['mnr']['mnrusr']
	mnrPwd = config['mnr']['mnrpwd']

	iniServer = config['mnr']['servermnr']
	iniRegion = config['mnr']['region']
	iniSelectors = config['mnr']['selectors']
	iniProcess = config['mnr']['process']
	# strStateSchema = config['mnr']['state']

	serverOptions=[
	'caprod01',
	'caprod02',
	'caprod05',
	'caprod06'
	] 

	index = serverOptions.index(iniServer) if iniServer in serverOptions else 0
	choiceSvr, ok = QInputDialog.getItem(mainWindow, "pyQGIS Database", "Select MNR Server:", serverOptions, index, False)
	if ok:
		svrURL =	config['mnr'][choiceSvr]
		config['mnr']['servermnr'] = choiceSvr
		with open(iniFile, 'w') as configfile:
			config.write(configfile)
	else:
		print(f"Server: Cancelled")
		return "cancel"

	lstSchemas = fSchemaQuery(svrURL, mnrPort, mnrdb, mnrUsr, mnrPwd)  
	lstSchemas.sort()
	# print(f"Schema: {lstSchemas}")

	lstRegions = fQueryRegions(lstSchemas)
	# print(f"Regions: {lstRegions}")

	print("===== Make sure you are connected to the VPN =====")
	elem = iniRegion
	index = lstRegions.index(elem) if elem in lstRegions else 0
	choice, ok = QInputDialog.getItem(mainWindow, "pyQGIS Region", "Select MNR Region:", lstRegions, index, False)
	if ok:
		print(f"Region: {choice}")
		strRegion = choice
		config['mnr']['region'] = strRegion
		with open(iniFile, 'w') as configfile:
			config.write(configfile)

	else:
		print(f"Region: Cancelled")
		return "cancel"

	strStateSchema = fSelectState(lstSchemas, strRegion, iniSelectors)
	print("strStateSchema: {}".format(strStateSchema))

	index = processOptions.index(iniProcess) if iniProcess in processOptions else 0
	choiceProcess, ok = QInputDialog.getItem(mainWindow, "pyQGIS Database", "Select MNR process:", processOptions, index, False)
	if ok:
		print(f"Process: {choiceProcess}")
		strProcessResult = fSubExecute(svrURL, strStateSchema, choiceProcess)
		print("fSubExecute returned {}".format(strProcessResult))

		config['mnr']['process'] = choiceProcess
		with open(iniFile, 'w') as configfile:
			config.write(configfile)
	else:
		print("State Cancelled")
		return "cancel"

def fSubExecute(svrURL, strStateSchema, choiceProcess):
	clipLayer = fLoad(svrURL, strStateSchema)
	extentCoords = fGetExtentCoords(clipLayer)
	# print("Extent Coords = {}".format(extentCoords))

	if choiceProcess == "Admin Areas":
		sub_MNR_AdminArea.fLoadAdminAreasFast(svrURL, strStateSchema, clipLayer, extentCoords)
		return "Admin Areas selected"
	elif choiceProcess == "Admin Areas Population":
		sub_MNR_AdminArea.fLoadAdminAreasPopulation(svrURL, strStateSchema, clipLayer, extentCoords)
		return "Admin Areas selected"
	elif choiceProcess == "Postal Districts":
		sub_MNR_PostalDistricts.fLoadPostalDistricts(svrURL, strStateSchema, clipLayer, extentCoords)
		return "Postal Districts selected"
	elif choiceProcess == "Postal Districts with Names":
		sub_MNR_PostalDistricts.fLoadPostalDistrictNames(svrURL, strStateSchema, clipLayer, extentCoords)
		return "Postal Districts selected"
	elif choiceProcess == "Census Areas":
		sub_MNR_PostalDistricts.fLoadCensusAreas(svrURL, strStateSchema, clipLayer, extentCoords)
		return "Census Areas selected"
	elif choiceProcess == "Other Areas":
		sub_MNR_OtherAreas.main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "Other areas like built-up"
	elif choiceProcess == "City Centers":
		sub_MNR_CityCenters.main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "City Centers selected"
	elif choiceProcess == "Address Points":
		sub_MNR_APTs.main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "Address points and entry points selected"
	elif choiceProcess == "Buildings":
		sub_MNR_Buildings.main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "Buildings selected"
	elif choiceProcess == "Land Use":
		sub_MNR_LandUse.main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "LandUse selected"
	elif choiceProcess == "Maneuver":
		sub_MNR_Maneuver.main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "Maneuver selected"
	elif choiceProcess == "Traffic Sign":
		sub_MNR_TrafficSign.main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "Traffic Sign selected"
	elif choiceProcess == "Traffic Light":
		sub_MNR_TrafficLight.main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "Traffic Light selected"
	elif choiceProcess == "NetworkZ Elevation (Old)":
		sub_MNR_NetworkZ.main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "NetworkZ selected"
	elif choiceProcess == "NetworkZ UUID (Old)":
		sub_MNR_NetworkZ_uuid.main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "NetworkZ UUID selected"
	elif choiceProcess == "NetworkZ GSC Lines":
		sub_MNR_NetworkZ_GSC.fMNRNetworkGSCLines_main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "NetworkZ GSC lines selected"
	elif choiceProcess == "NetworkZ GSC Points":
		sub_MNR_NetworkZ_GSC.fMNRNetworkGSCPoints_main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "NetworkZ GSC junction points selected"
	elif choiceProcess == "POIs":
		sub_MNR_POIs.main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "POIs selected"
	elif choiceProcess == "EV Charge Stations":
		sub_MNR_EVs.main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "EV Charge Stations selected"
	elif choiceProcess == "EV Charge Stations v2":
		sub_MNR_EVs2.main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "EV Charge Stations selected"
	elif choiceProcess == "EV Charge Stations v3 dBeaver":
		sub_MNR_EVsDBeaver.main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "EV Charge Stations selected"
	elif choiceProcess == "NetworkZ Speed Profile (Old)":
		sub_MNR_SpeedProfilesZ.main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "NetworkZ Speed Profile selected"
	elif choiceProcess == "Speed Profile (Old)":
		sub_MNR_SpeedProfiles.main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "Speed Profile selected"
	elif choiceProcess == "Speed Profile 5min Slots":
		sub_MNR_SpeedProfiles.fLoadSpeedProfile5minSlots(svrURL, strStateSchema, clipLayer, extentCoords)
		return "Speed Profile 5min Slots selected"
	elif choiceProcess == "Speed Profiles Arrays Wednesday":
		sub_MNR_SpeedProfiles.fLoadSpeedProfile5minSlotsAggregateWednesday(svrURL, strStateSchema, clipLayer, extentCoords)
		return "Speed Profiles Arrays Wednesday selected"
	elif choiceProcess == "Speed Profiles Arrays - Select day of week":
		sub_MNR_SpeedProfiles.fLoadSpeedProfile5minSlotsAggregateDaySelect(svrURL, strStateSchema, clipLayer, extentCoords)
		return "Speed Profiles Arrays Day select"
	elif choiceProcess == "Traffic Speed":
		sub_MNR_TrafficSpeed.main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "Traffic Speed selected"
	elif choiceProcess == "ADA curvature":
		sub_MNR_Curvature.main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "ADA curvature selected"
	elif choiceProcess == "Water":
		sub_MNR_Water.main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "Water selected"
	elif choiceProcess == "Add Centroid":
		sub_Add_Centroid.main(svrURL, strStateSchema, clipLayer, extentCoords)
		return "Add Centroid selected"
	else:
		return "cancel"

	

print("Loading Main()")
fMainUIMNR()
