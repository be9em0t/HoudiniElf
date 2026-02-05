# MovePortal TrafficStats 
# Combine sequence of DBFs to a single array and then join to a UUID mnr network.

# Procedures:
# 	'Move Portal - Combine Time Blocks',
					# to merge all time blocks from the Move Portal (it sorts them internally, so dont worry bout that)
					# To run it select all db and the shapefile in QGIS 
# 	'Move Portal - Match to MNR-network-UUID',
					# to join the time arrays with segments of the MNR network. 
					# This stage also provides separately Positive and Negative hit arrays, 
					# to be merged in Houdini
					# To run it select the mnr_network_UUID file and the PosNeg file resulting from the previous stage
#		'Move Portal Single Hour',
					# need description
#		'Move Portal Join Pos-Neg',
					# select the combined NegSeg layer, 
					# use the script to join Hits column of negative segments to positive segments
					# Normally, the number of segments should drop (as there are no more duplicate Pos andNeg segments)

# manually append script folder 'cause fucking QGIS
import numpy as np
import pandas as pd
import geopandas as gpd
from dbfread import DBF
import sys, os
import re
import imp # allow module reload
sys.path.append('d:/Work/OneDrive/Dev/Python/TT_Qgis_Workspace/MNR_automation')
import b9PyQGIS
imp.reload(b9PyQGIS)
from b9PyQGIS import *
from qgis.core import QgsProject
from qgis.utils import iface

# manually append script folder 'cause fucking QGIS
sys.path.append('d:/Work/OneDrive/Dev/Python/TT_Qgis_Workspace/MNR_automation')
import b9PyQGIS
imp.reload(b9PyQGIS)
from b9PyQGIS import *

# == User Variables ==
# location =  'detroit' # 'france' # 'detroit'
# ==
root = QgsProject.instance().layerTreeRoot()
# layerGeoId = ''
layerGeoBaseName = ''
layerGeoIdTarget = ''
masterField = ''
mainWindow=iface.mainWindow()


def fJoinFields(layerGeoId, i, fieldType='Hits'):
	global layerGeoIdTarget
	global masterField
	# print(layerGeoId)

	# Select fields to keep
	layer = QgsProject.instance().mapLayer(layerGeoId)
	listFields = layer.fields().names()
	for f in listFields:
		if f.endswith("Id"):
			keyField = f
		if f.endswith(fieldType):
			joinField = f
	print('keyField is {}, joinField is {}'.format(keyField, joinField))

	# join Attribs 
	print ("Joining layers... ")
	aFieldsToCopy = [joinField]
	strPrefix = '' 
	result = b9PyQGIS.fJoinByAttrib(layerGeoIdTarget, layerGeoId, masterField, keyField, aFieldsToCopy, strPrefix)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	if i > 1:
		QgsProject.instance().removeMapLayer(layerGeoIdTarget)
	# newLayer.setName(layerGeoBaseName + '_JoinTime' + str(i))
	newLayer.setName(layerGeoBaseName + '_Collect_TBD_' + fieldType)
	layerGeoIdTarget = newLayer.id()


def fCalcHitsArray(layerGeoId, fieldType='Hits'):
	print('Calculating Hits Arrays...')
	layer = QgsProject.instance().mapLayer(layerGeoId)
	listFields = layer.fields().names()
	# print("Fields are: {}".format(listFields))

	strComma = ' + \',\' + ' 
	aHits = []
	dropFields = []
	for fld in listFields:
		if fld.endswith(fieldType):
			strIf = ( 'if ("' + fld + '" is not NULL, to_string("' + fld + '"), \'0\')' )
			aHits.append(strIf)
			dropFields.append(fld)
	strCalc = strComma.join(aHits)

	strFieldName = fieldType
	strFormula = strCalc
	iFieldType = 2
	iFieldLength = 0
	iFieldPrecision = 0
	result = b9PyQGIS.fFieldCalc(layerGeoId, strFieldName, strFormula, iFieldType, iFieldLength, iFieldPrecision)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_' + fieldType)
	# QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()

	# drop unnecessary fields to save space
	print('Dropping fields...')
	# networkLayerDropFields = ['Id', 'Segment Id', 'NewSegId', 'Length']
	networkLayerDropFields = ['Segment Id', 'Length']
	dropFields = dropFields + networkLayerDropFields
	result = b9PyQGIS.fDropFields(layerGeoId, dropFields)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_Clean' + '_' + fieldType)
	# QgsProject.instance().removeMapLayer(layerGeoId)
	QgsProject.instance().removeMapLayer(layerGeoIdTarget)
	layerGeoId = newLayer.id()
	return(layerGeoId)

def fCombineNegSegId(layer, fieldType='Hits'):
	# calculate NegSegId field 
	print ("Calculating NegSegId field... ")
	strFieldName = 'NegSegId'
	strFormula = 'if ( (left( "NewSegId" , 1) = \'-\'), right( "NewSegId" , 36), NULL)\r\n'
	iFieldType = 2
	iFieldLength = 36 
	iFieldPrecision = 0
	result = b9PyQGIS.fFieldCalc(layer, strFieldName, strFormula, iFieldType, iFieldLength, iFieldPrecision)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	# QgsProject.instance().removeMapLayer(layerGeoIdTarget)
	newLayer.setName(layerGeoBaseName + '_NegSeg' + '_' + fieldType)
	# layerGeoId = newLayer.id()


# merge all time blocks with the move network shapefile
def fJoinTimeHits():
	fieldType='Hits'
	global layerGeoIdTarget
	global masterField
	global layerGeoBaseName

	#sort db layers
	selectedLayersRaw = iface.layerTreeView().selectedLayers()
	# print("{} layers selected.\n{}".format(len(selectedLayersRaw), selectedLayersRaw))
	selectedLayersTemp = dict()
	for l in selectedLayersRaw:
		lname = l.name() 
		arrlnamesplit = lname.split("_")
		try:
			ltimeblock = int(arrlnamesplit[len(arrlnamesplit)-1])
			selectedLayersTemp[ltimeblock] = l
			# print(ltimeblock)
			layerGeoBaseName = arrlnamesplit[0]
		except:
			layerGeoIdTarget = l.id()
			masterField = 'Id'
			# layerGeoBaseName = (arrlnamesplit[0] + arrlnamesplit[1] + arrlnamesplit[2])
			# print(layerGeoBaseName)

	selectedLayersOrdered = dict(sorted(selectedLayersTemp.items()))
	print("\n{} Sorted db layers: \n{}".format(len(selectedLayersOrdered), selectedLayersOrdered))
	print("\nNetwork (shapefile) layer is: \n{}".format(layerGeoIdTarget))

	for i in range(0, len(selectedLayersOrdered), 1):
		layer = list(selectedLayersOrdered.values())[i]
		print(layer)
		fJoinFields(layer.id(), i)

	layerGeoId = fCalcHitsArray(layerGeoIdTarget)
	QgsProject.instance().removeMapLayer(layerGeoIdTarget)

	fCombineNegSegId(layerGeoId)
	print("=== Done Arrays ===")



# Select 2 layers, MNR_networkUUID and Move_NegSeg:
def fMergeMoveToRealNetwork():
	selected_layers = iface.layerTreeView().selectedLayers()

	ok = True
	if len(selected_layers) == 2:
		layerGeoNetworkUUID = selected_layers[0] 
		layerGeoNetworkUUIDId = layerGeoNetworkUUID.id() 
		layerGeoNetworkUUIDName = layerGeoNetworkUUID.name()
		layerGeoBaseName = layerGeoNetworkUUIDName
		# print(layerGeoNetworkUUIDName)

		layerGeoMove = selected_layers[1] 
		layerGeoMoveId = layerGeoMove.id() 
		layerGeoMoveName = layerGeoMove.name()
		# print(layerGeoMoveName)

	else:
		ok = False
		QMessageBox.information(mainWindow,'pyQGIS',"Select only MNR-network-UUID and MovePortal_NegSegIdd layers \nand try again.\nNames should end in UUID and NegSeg")

	if (layerGeoNetworkUUIDName.find('UUID') >= 0) and (layerGeoMoveName.find('NegSeg') >= 0):
		print("Seems Ok")
	else:
		ok = False
		QMessageBox.information(mainWindow,'pyQGIS',"Select only MNR-network-UUID and MovePortal_NegSegIdd layers \nand try again.\nNames should end in UUID and NegSeg")

	if ok == True:
		# join Neg Attribs 
		print ("Joining Neg Move data... ")
		masterField = 'feat_id'
		keyField = 'NegSegId'
		aFieldsToCopy = ['Hits']
		strPrefix = 'Neg'
		result = b9PyQGIS.fJoinByAttrib(layerGeoNetworkUUIDId, layerGeoMoveId, masterField, keyField, aFieldsToCopy, strPrefix)
		newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
		newLayer.setName(layerGeoBaseName + '_NegJoin')
		layerGeoNegJoin = newLayer.id()

		# join Pos Attribs 
		print ("Joining Pos Move data... ")
		masterField = 'feat_id'
		keyField = 'NewSegId'
		aFieldsToCopy = ['Hits']
		strPrefix = 'Pos'
		result = b9PyQGIS.fJoinByAttrib(layerGeoNegJoin, layerGeoMoveId, masterField, keyField, aFieldsToCopy, strPrefix)
		newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
		QgsProject.instance().removeMapLayer(layerGeoNegJoin)
		# QgsProject.instance().removeMapLayer(layerGeoMoveId)
		newLayer.setName(layerGeoBaseName + '_MovePosNegHits')
		layerGeoNegJoin = newLayer.id()

# Creates a simple 1-hour traffic netrwork
# Select 2 layers, network layer and 2024_0_8_00-9_00_8.dbf:
def fMergeSingleHour():
	selected_layers = iface.layerTreeView().selectedLayers()

	ok = True
	if len(selected_layers) == 2:
		layerGeoNetwork = selected_layers[0] 
		layerGeoNetworkId = layerGeoNetwork.id() 
		layerGeoNetworkName = layerGeoNetwork.name()
		layerGeoBaseName = layerGeoNetworkName
		# print(layerGeoNetworkUUIDName)

		layerGeoMove = selected_layers[1] 
		layerGeoMoveId = layerGeoMove.id() 
		layerGeoMoveName = layerGeoMove.name()
		# print(layerGeoMoveName)

	else:
		ok = False
		QMessageBox.information(mainWindow,'pyQGIS',"Select only MNR-network and MovePortal single hour layers \nand try again.\nNetwork name should be \'network\'")

	if (layerGeoNetworkName == "network"):
		print("Seems Ok")
	else:
		ok = False
		QMessageBox.information(mainWindow,'pyQGIS',"Select only MNR-network and MovePortal single hour layers \nand try again.\nNetwork name should be \'network\'")

		QMessageBox.information(mainWindow,'pyQGIS',"This procedure is unfinished")
# ADD SOME LOGIC TO FIND THE CORRECT FIELDS
#  processing.run("native:joinattributestable", {
# 	 'INPUT':'/Users/dunevv/OneDrive - TomTom/3D_projects/QGIS/Amsterdam/QGIS/move_traffic/shapefile/network.shp',
# 	 'FIELD':'Id',
# 	 'INPUT_2':'/Users/dunevv/OneDrive - TomTom/3D_projects/QGIS/Amsterdam/QGIS/move_traffic/shapefile/Feb 22 2024_0_9_00-10_00_9.dbf|layername=Feb 22 2024_0_9_00-10_00_9',
# 	 'FIELD_2':'CS10_Id',
# 	 'FIELDS_TO_COPY':['CS10_AvgSp','CS10_HvgSp','CS10_MedSp','CS10_Hits'],
# 	 'METHOD':1,
# 	 'DISCARD_NONMATCHING':False,
# 	 'PREFIX':'','OUTPUT':'TEMPORARY_OUTPUT'})

	# if ok == True:
	# 	# join Neg Attribs 
	# 	print ("Joining Neg Move data... ")
	# 	masterField = 'Id'
	# 	keyField = 'NegSegId'
	# 	aFieldsToCopy = ['Hits']
	# 	strPrefix = 'Neg'
	# 	result = b9PyQGIS.fJoinByAttrib(layerGeoNetworkId, layerGeoMoveId, masterField, keyField, aFieldsToCopy, strPrefix)
	# 	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	# 	newLayer.setName(layerGeoBaseName + '_NegJoin')
	# 	layerGeoNegJoin = newLayer.id()

	# 	# join Pos Attribs 
	# 	print ("Joining Pos Move data... ")
	# 	masterField = 'feat_id'
	# 	keyField = 'NewSegId'
	# 	aFieldsToCopy = ['Hits']
	# 	strPrefix = 'Pos'
	# 	result = b9PyQGIS.fJoinByAttrib(layerGeoNegJoin, layerGeoMoveId, masterField, keyField, aFieldsToCopy, strPrefix)
	# 	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	# 	QgsProject.instance().removeMapLayer(layerGeoNegJoin)
	# 	QgsProject.instance().removeMapLayer(layerGeoMoveId)
	# 	newLayer.setName(layerGeoBaseName + '_MovePosNegHits')
	# 	layerGeoNegJoin = newLayer.id()

# from qgis.PyQt.QtWidgets import QInputDialog
def fSelectMoveData():
	items = ["Hits","AvgSp","MedSp","ratio"]
	# Unpack the tuple into two variables: picked_item and ok
	picked_item, ok = QInputDialog.getItem(None, "Pick an option", "Choice:", items, 0, False)
	if ok:
		print("You picked:", picked_item)
		return picked_item
	else:
		print("Cancelled")
		return

def fCalcArray(layerGeoId, fieldType='Hits'):
	print(f'Calculating {fieldType} Arrays...')

	layer = QgsProject.instance().mapLayer(layerGeoId)
	listFields = layer.fields().names()
	# print("Fields are: {}".format(listFields))

	strComma = ' + \',\' + ' 
	aHits = []
	dropFields = []
	for fld in listFields:
		if fld.endswith(fieldType):
			strIf = ( 'if ("' + fld + '" is not NULL, to_string("' + fld + '"), \'0\')' )
			aHits.append(strIf)
			dropFields.append(fld)
	strCalc = strComma.join(aHits)

	strFieldName = fieldType
	strFormula = strCalc
	iFieldType = 2
	iFieldLength = 0
	iFieldPrecision = 0
	result = b9PyQGIS.fFieldCalc(layerGeoId, strFieldName, strFormula, iFieldType, iFieldLength, iFieldPrecision)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_' + fieldType)
	# QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()

	# drop unnecessary fields to save space
	print('Dropping fields...')
	# networkLayerDropFields = ['Id', 'Segment Id', 'NewSegId', 'Length']
	networkLayerDropFields = ['Segment Id', 'Length']
	dropFields = dropFields + networkLayerDropFields
	result = b9PyQGIS.fDropFields(layerGeoId, dropFields)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_Clean' + '_' + fieldType)
	QgsProject.instance().removeMapLayer(layerGeoId)
	QgsProject.instance().removeMapLayer(layerGeoIdTarget)
	layerGeo = newLayer
	layerGeoId = newLayer.id()
	return(layerGeo)

# merge all speed time blocks with the move network shapefile
def fJoinOrbis(moveTypePicked):
	fieldType=moveTypePicked
	global layerGeoIdTarget
	global masterField
	global layerGeoBaseName

	#sort db layers
	selectedLayersRaw = iface.layerTreeView().selectedLayers()
	# print("{} layers selected.\n{}".format(len(selectedLayersRaw), selectedLayersRaw))
	selectedLayersTemp = dict()
	for l in selectedLayersRaw:
		lname = l.name() 
		arrlnamesplit = lname.split("_")
		try:
			ltimeblock = int(arrlnamesplit[len(arrlnamesplit)-1])
			selectedLayersTemp[ltimeblock] = l
			# print(ltimeblock)
			layerGeoBaseName = arrlnamesplit[0]
		except:
			layerGeoIdTarget = l.id()
			masterField = 'Id'
			# layerGeoBaseName = (arrlnamesplit[0] + arrlnamesplit[1] + arrlnamesplit[2])
			# print(layerGeoBaseName)

	selectedLayersOrdered = dict(sorted(selectedLayersTemp.items()))
	print("\n{} Sorted db layers: \n{}".format(len(selectedLayersOrdered), selectedLayersOrdered))
	print("\nNetwork (shapefile) layer is: \n{}".format(layerGeoIdTarget))

	for i in range(0, len(selectedLayersOrdered), 1):
		layer = list(selectedLayersOrdered.values())[i]
		print(layer)
		fJoinFields(layer.id(), i, fieldType)

	layerGeo = fCalcArray(layerGeoIdTarget, fieldType)
	# QgsProject.instance().removeMapLayer(layerGeoIdTarget)
	return layerGeo

	# fCombineNegSegId(layerGeoId, fieldType)
	print("=== Done Arrays ===")

def fCombineOrbis():
	moveTypePicked = fSelectMoveData()
	print("You picked:", moveTypePicked)
	# from datetime import datetime

	# join the layers
	layerGeo = fJoinOrbis(moveTypePicked)
	print(layerGeo.name())

	print("This is going to be very slow besause of selecting overlapping features")
	# layerGeo = iface.activeLayer()
	layerGeoId = layerGeo.id()
	layerGeoName = layerGeo.name()
	arrlnamesplit = layerGeoName.split("_")
	layerGeoBaseName = arrlnamesplit[0]

	# print(layerGeoBaseName)
	# print(layerGeo.name())


	message = 'Fixing Geometry'
	print(f"=== {message} ===")
	iface.messageBar().pushMessage("Status", message, level=Qgis.Info)
	QgsApplication.processEvents()
	# Add output to project
	result = b9PyQGIS.fFixGeometries(layerGeo)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_FixGeometry')
	# layerGeoIdNeg = newLayer.id()
	layerGeo = newLayer


	message = 'Adding Spatial Index'
	print(f"=== {message} ===")
	iface.messageBar().pushMessage("Status", message, level=Qgis.Info)
	QgsApplication.processEvents()
	b9PyQGIS.fCreateSpatialIndex(layerGeo)
	layerGeo.setName(layerGeoBaseName + '_Fixed_Indexed')

	message = 'Join by location'
	print(f"=== {message} ===")
	iface.messageBar().pushMessage("Status", message, level=Qgis.Info)
	QgsApplication.processEvents() # Force the GUI to update

	lstPredicate = [2]  # 2 is equal
	# lstJoinFields = ['NewSegId', 'Hits']
	lstJoinFields = ['NewSegId', moveTypePicked]
	intSingleMultiOverlap = 0 
	result = b9PyQGIS.fJoinByLocation(layerGeo, layerGeo, lstPredicate, lstJoinFields, intSingleMultiOverlap, strPrefix='')
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + f'_Join{moveTypePicked}')
	QgsProject.instance().removeMapLayer(layerGeo.id())
	# layerGeoIdNeg = newLayer.id()
	layerGeo = newLayer


	message = 'Adding Spatial Index, again'
	print(f"=== {message} ===")
	iface.messageBar().pushMessage("Status", message, level=Qgis.Info)
	QgsApplication.processEvents() # Force the GUI to update
	b9PyQGIS.fCreateSpatialIndex(layerGeo)
	layerGeo.setName(layerGeoBaseName + '_Joined_Indexed')
	layerGeo = newLayer

	message = 'Counting duplicates'
	print(f"=== {message} ===")
	iface.messageBar().pushMessage("Status", message, level=Qgis.Info)
	QgsApplication.processEvents() # Force the GUI to update
	DiscardNonMatching=False
	aJoinFields=['Id']
	aPredicate = [2]
	aSummaries = [0]
	result = b9PyQGIS.fJoinByAttribSummary(layerGeo, layerGeo, DiscardNonMatching, aJoinFields, aPredicate, aSummaries)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_CountDuplicates')
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer

	message = 'Extracting only the correct rows'
	print(f"=== {message} ===")
	iface.messageBar().pushMessage("Status", message, level=Qgis.Info)
	QgsApplication.processEvents() # Force the GUI to update
	strExpression = 'NewSegId != NewSegId_2\nor\nId_count = 1'
	layerGeoId = layerGeo.id()
	result = b9PyQGIS.fExtractByExpression(layerGeoId, strExpression)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_FilterDuplicates1')
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer

	message = 'Removing all duplicates finally'
	print(f"=== {message} ===")
	iface.messageBar().pushMessage("Status", message, level=Qgis.Info)
	QgsApplication.processEvents() # Force the GUI to update
	result = b9PyQGIS.fDeleteDuplicateGeoms(layerGeo)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_ClearDuplicates2')
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeo = newLayer

	message = 'Zeroing out self-joined'
	print(f"=== {message} ===")
	iface.messageBar().pushMessage("Status", message, level=Qgis.Info)
	QgsApplication.processEvents() # Force the GUI to update
	strFieldName = f'{moveTypePicked}_2'
	# strFormula = 'if ( "NewSegId" = "NewSegId_2" , \'0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\', Hits_2)'
	strFormula = f'if ( "NewSegId" = "NewSegId_2" , \'0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0\', {strFieldName})'
	iFieldType = 2
	iFieldLength = 0
	iFieldPrecision = 0
	result = b9PyQGIS.fFieldCalc(layerGeo, strFieldName, strFormula, iFieldType, iFieldLength, iFieldPrecision)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_' + moveTypePicked)
	QgsProject.instance().removeMapLayer(layerGeo.id())
	layerGeoId = newLayer.id()

	message = 'Dropping unneeded fields'
	print(f"=== {message} ===")
	iface.messageBar().pushMessage("Status", message, level=Qgis.Info)
	QgsApplication.processEvents() # Force the GUI to update
	aDropFields = ['Id','NewSegId_2','Id_count']
	result = b9PyQGIS.fDropFields(layerGeoId, aDropFields)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_' + moveTypePicked + '_Done')
	QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()

	message = f'{moveTypePicked} Done...'
	print(f"=== {message} ===")
	iface.messageBar().pushMessage("Status", message, level=Qgis.Info)
	QgsApplication.processEvents() # Force the GUI to update

def fOriginDestinationAreas():
	print("""
	1. Usually use postal districts as O/D areas. Take care that each area has a name! 
	Export as json to use in Move Portal O/D. Might simplify geometry using https://mapshaper.org/
	Split to time periods in MovePortal, to have some animation.
	Save the entire Matrix as Excel, save also the regions json. Might exclude same OD trips.
	
	2. In Excel set as data table and filter by origin and by destination - export both as CSV with headers. 

	3. Run our little OD_Filter_and_Sort.py script from HoudiniElf to rename and sort columns.
	
	Import in QGIS, join each CSV to the json - now we have geometry with attached values.
	Export to Houdini. Use "Polygon CSV Load" digital asset.
	""")
		
def fJoinPosNeg():
	print("This is going to be very slow besause of selecting overlapping features")
	print("This needs to be reworked based on attribute comparisons")
	layerGeo = iface.activeLayer()
	layerGeoId = layerGeo.id()
	layerGeoName = layerGeo.name()
	arrlnamesplit = layerGeoName.split("_")
	layerGeoBaseName = arrlnamesplit[0]

	print(layerGeoBaseName)
	print(layerGeo.name())

	# extract by expression negative
	strExpression = 'left("NewSegId",1) = \'-\''
	result = b9PyQGIS.fExtractByExpression(layerGeoId, strExpression)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_NegSegments')
	layerGeoIdNeg = newLayer.id()
	layerGeoNeg = newLayer

	# extract by expression positive
	strExpression = 'left("NewSegId",1) != \'-\''
	result = b9PyQGIS.fExtractByExpression(layerGeoId, strExpression)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_PosSegments')
	layerGeoIdPos = newLayer.id()

	# select equal features
	predicate = 3
	result = b9PyQGIS.fSelectByLocation(layerGeoIdNeg, layerGeoIdPos, predicate)
	# newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	# newLayer.setName(layerGeoBaseName + '_PosSegments')
	# layerGeoIdSource = newLayer.id()

	# extract equal features as Joinable
	result = b9PyQGIS.fExtractSelectedFeatures(layerGeoIdNeg)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_NegSegmentsJoinable')
	layerGeoIdNegJoinable = newLayer.id()

	# invert feature selection
	# layer = iface.activeLayer()  # Get the active layer
	selected_features = layerGeoNeg.selectedFeatures()  # Get the currently selected features
	layerGeoNeg.removeSelection()
	for feature in layerGeoNeg.getFeatures():
		if feature not in selected_features:
			layerGeoNeg.select(feature.id())

	# extract equal features as UnJoinable (only neg direction)
	result = b9PyQGIS.fExtractSelectedFeatures(layerGeoIdNeg)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_NegSegmentsUnJoinable')
	layerGeoIdNegUnJoinable = newLayer.id()
	layerGeoUnjoinable = newLayer
	
	# join positive to negative 
	print ("Joining positive to negative... ")
	masterField = 'NewSegId'
	keyField = 'NegSegId'
	aFieldsToCopy = ['NewSegId','Hits']
	strPrefix = 'j' 
	result = b9PyQGIS.fJoinByAttrib(layerGeoIdPos, layerGeoIdNegJoinable, masterField, keyField, aFieldsToCopy, strPrefix)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_PosNegJoinTemp')
	layerGeoIdPosNegJoinTemp = newLayer.id()
	
	# merge layers
	mergeLayers = [newLayer,layerGeoUnjoinable]
	result = b9PyQGIS.fMergeLayers(mergeLayers)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_Merged')
	layerGeoId = newLayer.id()

	# drop extra fields 
	print ("Dropping unnecessary fields... ")
	aDropFields = ['NegSegId','layer','path','fid']
	result = b9PyQGIS.fDropFields(layerGeoId, aDropFields)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_PosNegJoin')
	# layerGeoId = newLayer.id()


	QgsProject.instance().removeMapLayer(layerGeoId)
	QgsProject.instance().removeMapLayer(layerGeoIdPos)
	QgsProject.instance().removeMapLayer(layerGeoIdNeg)
	QgsProject.instance().removeMapLayer(layerGeoIdPosNegJoinTemp)
	QgsProject.instance().removeMapLayer(layerGeoIdNegUnJoinable)
	QgsProject.instance().removeMapLayer(layerGeoIdNegJoinable)

def fGetLayerURI(layerId):
	# Get the current layer (make sure your shapefile layer is selected)
	# layer = iface.activeLayer()
	layer = QgsProject.instance().mapLayer(layerId)

	# Check if the layer is valid and a vector layer
	if layer and layer.type() == QgsVectorLayer.VectorLayer:
		# Get the file path to the shapefile or data source
		uri = layer.dataProvider().dataSourceUri()
		
		# If the URI contains a pipe '|', split it to extract only the file path and name
		if '|' in uri:
			file_path = uri.split('|')[0]  # Get the part before the pipe
		else:
			file_path = uri  # If no pipe, the URI is just the file path
		
		# Print the file path
		# print(f"File path and name1: {file_path}")
		return file_path
	else:
		print("Please select a vector layer.")

def fGetLayers():
	# global layerGeoIdTarget
	# global masterField
	# global layerGeoBaseName

	#sort db layers
	selectedLayersRaw = iface.layerTreeView().selectedLayers()
	print("{} layers selected.\n{}".format(len(selectedLayersRaw), selectedLayersRaw))

	selectedLayersTemp = dict()
	for l in selectedLayersRaw:
		lname = l.name() 
		arrlnamesplit = lname.split("_")
		try:
			ltimeblock = int(arrlnamesplit[len(arrlnamesplit)-1])
			selectedLayersTemp[ltimeblock] = l
			# print(ltimeblock)
			layerGeoBaseName = arrlnamesplit[0]
		except:
			layerGeoIdTarget = l.id()
			masterField = 'Id'
			# layerGeoBaseName = (arrlnamesplit[0] + arrlnamesplit[1] + arrlnamesplit[2])
			# print(layerGeoBaseName)

	selectedLayersOrdered = dict(sorted(selectedLayersTemp.items()))
	# print("\n{} Sorted db layers: \n{}".format(len(selectedLayersOrdered), selectedLayersOrdered))
	# print("\nNetwork (shapefile) layer is: \n{}".format(layerGeoIdTarget))
	
	return selectedLayersOrdered, layerGeoIdTarget

def fExternalPython():
	message = "nForget about this QGIS crap\nGet to command line and run \n>>> python Standalone_MovePortalJoin.py <shapefile.shx>"
	print(message)
	QMessageBox.information(mainWindow,'pyQGIS',message)






# === MAIN ===
if __name__ == "__console__":
	fJoinTimeBlocks()

