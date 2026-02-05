# PyQGIS function library

# from osgeo import ogr
# import os, sys
# import ogr, osr
from qgis.core import *
from qgis.core import QgsDataSourceUri, QgsVectorLayer

from qgis.utils import *
# from qgis.gui import QgsMessageBar
from qgis import processing
import xml.etree.ElementTree as ET
# import configparser
from qgis.PyQt.QtSql import QSqlDatabase
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import *
# from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtWidgets import (QWidget, QPushButton, QLineEdit, QInputDialog, QMessageBox, QListView, QListWidget, QLabel, QAction, QFileDialog)

qtParent=iface.mainWindow()
qtTitle = "pyQGIS"

### UI
def inputDlg(question, default):
	qid = QInputDialog()
	label = question #"Continue? (Y/N): "
	mode = QLineEdit.Normal
	# default = "Yes"
	answer, status = QInputDialog.getText(qid, qtTitle, label, mode, default)
	return answer

def qtMsgBox(information):
	# Provide information to user
	QMessageBox.information(qtParent, qtTitle, information)

def qtMsgBoxAsk(question):
	res = QMessageBox.question(qtParent, qtTitle, question)
	if res==QMessageBox.Yes:
		return True

	if res==QMessageBox.No:
		return False

def qtInputDlg(question, default):
	answer, status = QInputDialog().getText(qtParent, qtTitle, question, QLineEdit.Normal, default)
	return answer

def qtInputDlgMultiline(question, default):
	answer, status = QInputDialog.getMultiLineText(qtParent, qtTitle, question, default)
	return answer

def qtFileSaveDialog(caption,dir,filter="All Files (*)"):
	# QFileDialog.getSaveFileName(parent,caption,dir,filter,selectedFilter,options)
	parent=None
	# filter="Text Files (*.txt);;All Files (*)"
	file, pattern = QFileDialog.getSaveFileName(parent, caption, dir, filter)
	return file

def qtDirectoryDialog(dir,caption="Select a folder"):
	# QFileDialog.getSaveFileName(parent,caption,dir,filter,selectedFilter,options)
	parent=None
	# filter="Text Files (*.txt);;All Files (*)"
	folder = QFileDialog.getExistingDirectory(parent, caption, dir)
	# file, pattern = QFileDialog.getSaveFileName(parent, caption, dir, filter)
	return folder


### PostGIS
def fFieldsFromString(strPrefix, strSourceFields):
	# strPrefix = "a."
	# strSourceFields = "feat_id,feat_type,geocoding_method,in_car_importance,geom"
	listSourceFields = strSourceFields.split(",")
	listFields = []
	for s in listSourceFields:
		listFields.append(strPrefix + s)
	strResultFields = ",".join(listFields)
	return strResultFields

def fFieldsFromStringQ(strPrefix, strSourceFields):
	listSourceFields = strSourceFields.split(",")
	listFields = []
	for s in listSourceFields:
		listFields.append('\"' + strPrefix + '\".\"' + s + '\"')
	strResultFields = ",".join(listFields)
	return strResultFields

def fReadPostgresRecords(mnrServer, port, db, user, piss, strQuery, strField):
	uri = QgsDataSourceUri()
	# uri.setConnection(mnrServer, "5432", "mnr", "mnr_ro", "mnr_ro")
	uri.setConnection(mnrServer, port, db, user, piss)
	db = QSqlDatabase.addDatabase("QPSQL")
	db.setHostName(uri.host())
	db.setDatabaseName(uri.database())
	db.setPort(int(uri.port()))
	db.setUserName(uri.username())
	db.setPassword(uri.password())

	aRecords = []

	if db.open():
		query = db.exec(strQuery)

		while query.next():
			record = query.record()
			# print (record.field('release').value())
			# aRecords.append(record.field('release').value())
			aRecords.append(record.field(strField).value())
	else:
		err = db.lastError()
		print (err.driverText())
	
	return aRecords

def fReadPostgresMultiRecords(mnrServer, port, db, user, piss, strQuery, arrFields):
	uri = QgsDataSourceUri()
	# uri.setConnection(mnrServer, "5432", "mnr", "mnr_ro", "mnr_ro")
	uri.setConnection(mnrServer, port, db, user, piss)
	db = QSqlDatabase.addDatabase("QPSQL")
	db.setHostName(uri.host())
	db.setDatabaseName(uri.database())
	db.setPort(int(uri.port()))
	db.setUserName(uri.username())
	db.setPassword(uri.password())

	aRecords = []
	aResults = []

	if db.open():
		query = db.exec(strQuery)

		while query.next():
			record = query.record()
			# print (record.field('release').value())
			# aRecords.append(record.field('release').value())
			for f in arrFields:
				# print (f)
				aRecords.append(record.field(f).value())
				# print(aRecords)
				aResults.append(aRecords)
				aRecords = []
	else:
		err = db.lastError()
		print (err.driverText())
	
	return aResults

def fReadPostgresRecordRaws(mnrServer, port, db, user, piss, strQuery, arrFields):
	uri = QgsDataSourceUri()
	# uri.setConnection(mnrServer, "5432", "mnr", "mnr_ro", "mnr_ro")
	uri.setConnection(mnrServer, port, db, user, piss)
	db = QSqlDatabase.addDatabase("QPSQL")
	db.setHostName(uri.host())
	db.setDatabaseName(uri.database())
	db.setPort(int(uri.port()))
	db.setUserName(uri.username())
	db.setPassword(uri.password())

	aRecords = []
	aResults = []

	if db.open():
		query = db.exec(strQuery)

		while query.next():
			record = query.record()
			# print (record.field('release').value())
			# aRecords.append(record.field('release').value())
			for f in arrFields:
				# print (f)
				aRecords.append(record.field(f).value())
				aResults.append(aRecords)
				aRecords = []
			# print(aResults)
			# aResults=[]
	else:
		err = db.lastError()
		print (err.driverText())
	
	return aResults

def fReadPostgresRecordStrings(mnrServer, port, db, user, piss, strQuery, arrFields):
	uri = QgsDataSourceUri()
	# uri.setConnection(mnrServer, "5432", "mnr", "mnr_ro", "mnr_ro")
	uri.setConnection(mnrServer, port, db, user, piss)
	db = QSqlDatabase.addDatabase("QPSQL")
	db.setHostName(uri.host())
	db.setDatabaseName(uri.database())
	db.setPort(int(uri.port()))
	db.setUserName(uri.username())
	db.setPassword(uri.password())

	aRecords = []
	aResults = []

	if db.open():
		query = db.exec(strQuery)

		while query.next():
			record = query.record()
			for f in arrFields:
				aRecords.append(record.field(f).value())
				aResults.append(aRecords[0])
				aRecords = []
	else:
		err = db.lastError()
		print (err.driverText())
	return aResults


def fReadPostgresRecords(mnrServer, port, db, user, piss, strQuery, arrFields):
	uri = QgsDataSourceUri()
	# uri.setConnection(mnrServer, "5432", "mnr", "mnr_ro", "mnr_ro")
	uri.setConnection(mnrServer, port, db, user, piss)
	db = QSqlDatabase.addDatabase("QPSQL")
	db.setHostName(uri.host())
	db.setDatabaseName(uri.database())
	db.setPort(int(uri.port()))
	db.setUserName(uri.username())
	db.setPassword(uri.password())

	aResults = []

	if db.open():
		query = db.exec(strQuery)

		while query.next():
			record = query.record()
			aNewRecord = []
			for f in arrFields:
				aNewRecord.append(record.field(f).value())
			aResults.append(aNewRecord)
	else:
		err = db.lastError()
		# print (err.driverText())
	return aResults

def fLoadPostGISLayer(strPostgrServer, strPort, strDbase, u, p, strPostGisSchema, strPostGisTable, strType):
	uri = QgsDataSourceUri()
	uri.setConnection(strPostgrServer, strPort, strDbase, u, p)
	uri.setDataSource(strPostGisSchema, strPostGisTable, strType)
	layer = QgsVectorLayer(uri.uri(), strPostGisTable, "postgres")
	if not layer.isValid():
		print("Layer %s did not load" %layer.name())  
	QgsProject.instance().addMapLayer(layer)
	return layer.id()

def fLoadPostGISView(strPostgrServer, strPort, strDbase, u, p, strPostGisSchema, strPostGisTable, strType, strKey):
	uri = QgsDataSourceUri()
	uri.setConnection(strPostgrServer, strPort, strDbase, u, p)
	uri.setDataSource(strPostGisSchema, strPostGisTable, strType, aKeyColumn=strKey)
	# layer = iface.addVectorLayer(uri.uri(False), strPostGisTable, "postgres")
	layer = QgsVectorLayer(uri.uri(), strPostGisTable, "postgres")
	if not layer.isValid():
		print("Layer %s did not load" %layer.name())  
	QgsProject.instance().addMapLayer(layer)
	return layer.id()

def fPostGISexec(strServer, strQuery):
	result = processing.run("native:postgisexecutesql", 
		{'DATABASE':strServer,
		'SQL':strQuery}
		)
	return result

### QGIS Layers
def fTestMissingLayers(dirCommonGeopack, commonLayers):
	existingLayerNames = []
	for layer in QgsProject.instance().mapLayers().values():
		existingLayerNames.append(layer.name())
	for lName in commonLayers:
		if lName not in existingLayerNames:
			print("\n +++ Loading common layer: {} +++".format(lName))
			path_to_gpkg = dirCommonGeopack
			gpkg_countries_layer = path_to_gpkg + "|layername=" + lName
			print(path_to_gpkg)
			print(gpkg_countries_layer)
			vlayer = QgsVectorLayer(gpkg_countries_layer, lName, "ogr")
			if not vlayer.isValid():
					print("\nERROR: +++ Couldn't load layer: {} +++".format(lName))
			else:
					QgsProject.instance().addMapLayer(vlayer)


def fExtractByLocation(layer, strClipLayerName):
	clipLayers = QgsProject.instance().mapLayersByName(strClipLayerName)
	if len(clipLayers) == 0:
		iface.messageBar().pushMessage("Error", 'No layer found: {}'.format(clipLayer) , level=Qgis.Critical)
	result = processing.run("native:extractbylocation", 
		{ 'TARGET_CRS' : QgsCoordinateReferenceSystem('EPSG:3857'), 'PREDICATE':[0],
		'INTERSECT': clipLayers[0].id(),
		'INPUT':layer, 'OUTPUT':'memory:'})
	return result

def fClipByLayer(layer, strClipLayerName):
	clipLayers = QgsProject.instance().mapLayersByName(strClipLayerName)
	if len(clipLayers) == 0:
		iface.messageBar().pushMessage("Error", 'No layer found: {}'.format(clipLayer) , level=Qgis.Critical)
	result = processing.run("native:clip", 
		{ 'INPUT':layer, 'OVERLAY': clipLayers[0].id(), 'OUTPUT':'memory:'})
	return result

def fShowFeatureCount(layer):
	root = QgsProject.instance().layerTreeRoot()
	myLayerNode = root.findLayer(layer.id())
	myLayerNode.setCustomProperty("showFeatureCount", True)

def fCreateSpatialIndex(layer):
	result = processing.run("native:createspatialindex", 
		{ 'INPUT':layer, 'OUTPUT':'memory:'})
	return result

def fJoinByLocation(layer1, layer2, lstPredicate, lstJoinFields, intSingleMultiOverlap=2, strPrefix=''):
	result = processing.run("native:joinattributesbylocation", 
		{ 'PREDICATE':lstPredicate,
			'JOIN_FIELDS':lstJoinFields,
			'METHOD':intSingleMultiOverlap,
			'DISCARD_NONMATCHING':False,
			'PREFIX':strPrefix,
			'INPUT':layer1, 'JOIN' : layer2, 'OUTPUT':'memory:'})
	return result

def fJoinByAttrib(layer1, layer2, strField1, strField2, aFieldsToCopy, strPrefix=''):
	result = processing.run("native:joinattributestable", 
		{ 'FIELD':strField1,'FIELD_2': strField2,'FIELDS_TO_COPY':aFieldsToCopy,'METHOD':1,'DISCARD_NONMATCHING':False,'PREFIX':strPrefix,
		'INPUT':layer1, 'INPUT_2' : layer2, 'OUTPUT':'memory:'})
	return result

def fJoinByAttribMulti(layer1, layer2, strField1, strField2, aFieldsToCopy, strPrefix=''):
	result = processing.run("native:joinattributestable", 
		{ 'FIELD':strField1,'FIELD_2': strField2,'FIELDS_TO_COPY':aFieldsToCopy,'METHOD':0,'DISCARD_NONMATCHING':False,'PREFIX':strPrefix,
		'INPUT':layer1, 'INPUT_2' : layer2, 'OUTPUT':'memory:'})
	return result

def fJoinByAttribSummary(layer, join, DiscardNonMatching=False, aJoinFields=['Id'], aPredicate = [2], aSummaries = [0]):
	result = processing.run("native:joinbylocationsummary", 
		{ 'DISCARD_NONMATCHING' : DiscardNonMatching, 'JOIN_FIELDS' : aJoinFields, 'PREDICATE' : aPredicate, 'SUMMARIES' : aSummaries, 'INPUT':layer, 'JOIN' : join, 'OUTPUT' : 'TEMPORARY_OUTPUT'})
	return result

def fMergeLayers(layers):
	params = {'LAYERS' : layers, 'CRS':None, 'OUTPUT':'TEMPORARY_OUTPUT'}
	result = processing.run("native:mergevectorlayers", params)
	return result

def fDissolve(layer):
	params = {'INPUT' : layer, 'FIELD':[], 'SEPARATE_DISJOINT':False, 'OUTPUT' : 'memory:'}
	result = processing.run("native:dissolve", params)
	return result

# delete features in-place (no new layer)
def fDeleteFeatures(layer, featName, featValue):
	delfeats = []
	features = layer.getFeatures()
	for feat in features:
		if feat[featName] == featValue:
			delfeats.append(feat.id())
	result = layer.dataProvider().deleteFeatures(delfeats)
	layer.triggerRepaint()
	return layer

def fDropFields(layer, aDropFields):
	params = {'COLUMN':aDropFields, 'INPUT' : layer, 'OUTPUT' : 'memory:'}
	result = processing.run("qgis:deletecolumn", params)
	return result


def fRetainFields(layer, aRetainFields):
	params = {'FIELDS':aRetainFields, 'INPUT' : layer, 'OUTPUT' : 'memory:'}
	result = processing.run("native:retainfields", params)
	return result

def fAddField(layer, strAddField):
	params = {'INPUT':layer, 'OUTPUT':'memory:','FIELD_NAME':strAddField,'FIELD_TYPE':2,'FIELD_LENGTH':-1,'FIELD_PRECISION':0,'FIELD_ALIAS':'','FIELD_COMMENT':''}
	result = processing.run("native:addfieldtoattributestable", params)
	print('WTF?')
	return result

def fRenameField(layer, oldName, newName):
	params = {'INPUT' : layer, 'FIELD':oldName,'NEW_NAME':newName,'OUTPUT' : 'memory:'}
	result = processing.run("native:renametablefield", params)
	return result

def fRefactor(layer, fieldsMap):
	# fieldsMap = [{'expression': '"building"','length': 0,'name': 'building','precision': 0,'sub_type': 0,'type': 10,'type_name': 'text'},{'expression': '"name"','length': 0,'name': 'name','precision': 0,'sub_type': 0,'type': 10,'type_name': 'text'},{'expression': '"ele"','length': 0,'name': 'ele','precision': 0,'sub_type': 0,'type': 10,'type_name': 'text'},{'expression': '"height"','length': 0,'name': 'height','precision': 0,'sub_type': 0,'type': 10,'type_name': 'text'},{'expression': '"building:levels"','length': 0,'name': 'building:levels','precision': 0,'sub_type': 0,'type': 10,'type_name': 'text'},{'expression': '"building:min_level"','length': 0,'name': 'building:min_level','precision': 0,'sub_type': 0,'type': 10,'type_name': 'text'},{'expression': '"building:levels:underground"','length': 0,'name': 'building:levels:underground','precision': 0,'sub_type': 0,'type': 10,'type_name': 'text'},{'expression': '"building:colour"','length': 0,'name': 'building:colour','precision': 0,'sub_type': 0,'type': 10,'type_name': 'text'},{'expression': '"roof:levels"','length': 0,'name': 'roof:levels','precision': 0,'sub_type': 0,'type': 10,'type_name': 'text'},{'expression': '"roof:height"','length': 0,'name': 'roof:height','precision': 0,'sub_type': 0,'type': 10,'type_name': 'text'},{'expression': '"roof:shape"','length': 0,'name': 'roof:shape','precision': 0,'sub_type': 0,'type': 10,'type_name': 'text'},{'expression': '"roof:colour"','length': 0,'name': 'roof:colour','precision': 0,'sub_type': 0,'type': 10,'type_name': 'text'},{'expression': '"colour"','length': 0,'name': 'colour','precision': 0,'sub_type': 0,'type': 10,'type_name': 'text'},{'expression': '"amenity"','length': 0,'name': 'amenity','precision': 0,'sub_type': 0,'type': 10,'type_name': 'text'}]
	params = {'INPUT' : layer, 'FIELDS_MAPPING':fieldsMap,'OUTPUT' : 'memory:'}
	result = processing.run("native:refactorfields", params)
	return result

# predicate 3:equal
def fSelectByLocation(baseLayer, clipLayer, predicate):
	result = processing.run("native:selectbylocation", 
		{'PREDICATE':predicate,
		'INTERSECT': clipLayer,
		'METHOD':0,'INPUT':baseLayer, 'OUTPUT':'memory:'})
	return result

def fSelectByExpression(layer, strExpression):
	result = processing.run("qgis:selectbyexpression", 
		{ 'EXPRESSION': strExpression, 'INPUT':layer, 'METHOD':0}
		)
	return result

def fExtractByExpression(layer, strExpression):
	result = processing.run("native:extractbyexpression", 
		{ 'EXPRESSION': strExpression,
		'INPUT':layer, 'OUTPUT':'memory:'})
	return result


def fExtractByAttrib(layer, strField, strValue, intOperator):
	result = processing.run("native:extractbyattribute", 
		{ 'FIELD':strField,'VALUE':strValue,'OPERATOR':intOperator,
		'INPUT':layer, 'OUTPUT':'memory:'})
	return result

def fExtentBoundingBox(layer):
	params = {'INPUT' : layer, 'OUTPUT' : 'memory:'}
	result = processing.run("native:boundingboxes", params)
	return result

def fBoundingGeometry(layer):
	params = {'INPUT' : layer, 'FIELD':'', 'TYPE':0, 'OUTPUT' : 'memory:'}
	result = processing.run("qgis:minimumboundinggeometry", params)
	return result

def fExtractByExtent(layer, extentLayer):
	params = {'CLIP':True, 'INPUT' : layer, 'EXTENT':extentLayer, 'OUTPUT' : 'memory:'}
	result = processing.run("native:extractbyextent", params)
	return result

def fExtractSelectedFeatures(layer):
	params = {'INPUT' : layer, 'OUTPUT' : 'memory:'}
	result = processing.run("native:saveselectedfeatures", params)
	return result

def fMultiToSingleParts(layer):
	result = processing.run("native:multiparttosingleparts", 
		{ 'INPUT':layer, 'OUTPUT':'memory:'})
	return result

def fForceRightHand(layer):
	result = processing.run("native:forcerhr", 
		{ 'INPUT':layer, 'OUTPUT':'memory:'})
	return result

# === EXPORT RELATED ======

def fPolygons2Lines(layer):
	result = processing.run("native:polygonstolines", 
	{ 'INPUT' : layer, 'OUTPUT' : 'memory:' })
	return result

def fExplodeLines(layer):
	result = processing.run("native:explodelines", 
	{ 'INPUT' : layer, 'OUTPUT' : 'memory:' })
	return result

def fFieldCalc(layer, strFieldName, strFormula, iFieldType, iFieldLength, iFieldPrecision):
	params = { 
		'FIELD_NAME' : '{}'.format(strFieldName), 
		'FORMULA' : '{}'.format(strFormula), 
		'FIELD_TYPE' : iFieldType, 
		'FIELD_LENGTH' : iFieldLength, 
		'FIELD_PRECISION' : iFieldPrecision, 
		'NEW_FIELD':True,  
	'INPUT' : layer, 'OUTPUT' : 'memory:' }
	result = processing.run("qgis:fieldcalculator", params )
	# result = processing.run("native:fieldcalculator", params )
	return result

def fPointLayerFromTable(layer, pointX, pointY, pointZ, epsgCode='4326'):
		epsg = 'EPSG:' + epsgCode # 'EPSG:4326'
		result = processing.run("native:createpointslayerfromtable", 
				{'INPUT':layer, 
				'XFIELD':pointX,
				'YFIELD':pointY,
				'ZFIELD':pointZ,
				'MFIELD':'',
				'TARGET_CRS' : QgsCoordinateReferenceSystem(epsg), 
				'OUTPUT':'memory:'})
		return result

def fRemoveDuplicates(layer,strFields):
	params = { 'FIELDS':strFields,  
	'INPUT' : layer, 'OUTPUT' : 'memory:' }
	result = processing.run("qgis:removeduplicatesbyattribute", params )
	return result

def fDeleteDuplicateGeoms(layer):
	params = { 'INPUT' : layer, 'OUTPUT' : 'memory:' }
	result = processing.run("native:deleteduplicategeometries", params )
	return result


def fAddRowID(layer,strField, strFormula, iFieldType, iFieldLength, iFieldPrecision):
	params = { 'FIELD_NAME' : '{}'.format(strField), 'FORMULA' : '{}'.format(strFormula), 'FIELD_TYPE' : iFieldType, 'FIELD_LENGTH' : iFieldLength, 'FIELD_PRECISION' : iFieldPrecision, 'NEW_FIELD':True,  
	'INPUT' : layer, 'OUTPUT' : 'memory:' }
	result = processing.run("qgis:fieldcalculator", params )
	return result

def fExtractVerts(layer):
	result = processing.run("native:extractvertices", 
	{'INPUT' : layer, 'OUTPUT' : 'memory:' }
	)
	return result

def fAddXYmeters(layer):
	result = processing.run("native:addxyfields", 
	{ 'CRS' : QgsCoordinateReferenceSystem('EPSG:3857'),  
	'PREFIX' : 'm' ,
	'INPUT' : layer, 'OUTPUT' : 'memory:' }
	)
	return result

def fExpXYcoordOffset(layer, offsetXm, offsetYm):
	params = { 'FIELD_NAME':'mXzero','FIELD_TYPE':0,'FIELD_LENGTH':20,'FIELD_PRECISION':10, 'FORMULA':' "mx" - {} '.format(offsetXm), 
	'INPUT' : layer, 'OUTPUT' : 'memory:'}
	result = processing.run("qgis:fieldcalculator", params)
	newLayerX = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayerX.setName('netw' + '_ZeroX')
	params = { 'FIELD_NAME':'mYzero','FIELD_TYPE':0,'FIELD_LENGTH':20,'FIELD_PRECISION':10, 'FORMULA':' "my" - {} '.format(offsetYm), 
	'INPUT' : newLayerX, 'OUTPUT' : 'memory:'}
	result = processing.run("qgis:fieldcalculator", params)
	newLayerY = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayerY.setName('netw' + '_ZeroXY')
	QgsProject.instance().removeMapLayer(newLayerX.id())
	return result

def fExtractVertices(layer):
	params = { 'INPUT' : layer, 'OUTPUT' : 'memory:'}
	result = processing.run("native:extractvertices", params)
	return result

def temp():
	rowIDLayer.selectByExpression(" \"rowID\" >= {} AND  \"rowID\" <= {}".format(iMin, iMax))
	result = b9PyQGIS.fExtractSelectedFeatures(rowIDLayerId)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + str(iMin))
	# QgsProject.instance().removeMapLayer(layerGeoId)
	layerGeoId = newLayer.id()

def fPointsAlongLines(layer):
	params = {'INPUT':layer,'DISTANCE':1000,'START_OFFSET':QgsProperty.fromExpression('"chainage" / 100'),'END_OFFSET':0,'OUTPUT':'TEMPORARY_OUTPUT'}
	result = processing.run("native:pointsalonglines", params)
	return result

def fAddGeometryAttribs(layer):
	params = { 'INPUT' : layer, 'CALC_METHOD':0, 'OUTPUT' : 'memory:'}
	result = processing.run("qgis:exportaddgeometrycolumns", params)
	return result

def fAddCentroidPoint(layer):
	params = { 'ALL_PARTS' : True, 'INPUT' : layer, 'OUTPUT' : 'memory:'}
	result = processing.run("native:centroids", params)
	return result

# replaces def fAddMeterText(layer):
def fAddMeterCoordinate(layer,fieldName):
	params = { 'FIELD_NAME':'fieldName','FIELD_TYPE':2,'FIELD_LENGTH':100,'FIELD_PRECISION':0, 'FORMULA' : 'geomToWKT( transform( centroid($geometry), layer_property(@layer_id, \'crs\'), \'EPSG:3857\') )', 'INPUT' : layer, 'OUTPUT' : 'memory:'}
	result = processing.run("qgis:fieldcalculator", params)
	return result

# create spatial index
def fSpatialIndex(layer):
	params = { 'MIN_AREA':0, 'INPUT' : layer, 'OUTPUT' : 'memory:'}
	result = processing.run("native:createspatialindex", params)
	return result

# create spatial index
def fListUniqueVals(layer,list):
	params = { 'FIELDS':list, 'INPUT' : layer, 'OUTPUT' : 'memory:'}
	result = processing.run("qgis:listuniquevalues", params)
	return result

# convert geometry type
# type 0 - centroids, type 1 - nodes, type 2 - linestrings, type 3 - multilinestrings, type 4 - polygons
def fConvert(layer, type):
	params = { 'INPUT' : layer, 'TYPE':type, 'OUTPUT' : 'memory:'}
	result = processing.run("qgis:convertgeometrytype", params)
	return result

def fDeleteHoles(layer):
	params = { 'MIN_AREA':0, 'INPUT' : layer, 'OUTPUT' : 'memory:'}
	result = processing.run("qgis:deleteholes", params)
	return result

def fDifference(layer, layerBase):
	params = { 'INPUT' : layer, 'OVERLAY' : layerBase, 'OUTPUT' : 'memory:'}
	result = processing.run("qgis:difference", params)
	return result

def fFixGeometries(layer):
	params = { 'INPUT' : layer, 'OUTPUT' : 'memory:'}
	result = processing.run("qgis:fixgeometries", params)
	return result

def fReprojectLayer(layer, epsgCode='4326'):
		# layer = iface.activeLayer()
		epsg = 'EPSG:' + epsgCode # 'EPSG:4326'
		result = processing.run("native:reprojectlayer", 
				{'INPUT':layer, 
				'TARGET_CRS' : QgsCoordinateReferenceSystem(epsg), 
				'OUTPUT':'memory:'})
		return result

def fDuplicateLayer(original_layer: QgsMapLayer, new_layer_name: str) -> QgsMapLayer:
	duplicate = original_layer.clone()
	duplicate.setName(new_layer_name)
	QgsProject.instance().addMapLayer(duplicate)	
	return duplicate

def fDuplicateLayerinMemory(original_layer: QgsMapLayer, new_layer_name: str) -> QgsMapLayer:
	original_layer.selectAll()
	duplicate = processing.run("native:saveselectedfeatures", {'INPUT': original_layer, 'OUTPUT': 'memory:'})['OUTPUT']
	original_layer.removeSelection()
	duplicate.setName(new_layer_name)
	QgsProject.instance().addMapLayer(duplicate)
	return duplicate

def fGetVectorLayerType(layer):
	if layer.isValid() and layer.type() == QgsMapLayer.VectorLayer:
		geom_type = layer.geometryType()
		if geom_type == QgsWkbTypes.PointGeometry:
				# print("The layer is a Point layer.")
				type = "point"
		elif geom_type == QgsWkbTypes.LineGeometry:
				# print("The layer is a Line layer.")
				type = "line"
		elif geom_type == QgsWkbTypes.PolygonGeometry:
				# print("The layer is a Polygon layer.")
				type = "polygon"
		else:
				# print("Unknown geometry type.")
				type = "unknown"
	else:
		# print("Invalid layer or not a vector layer.")
		type = "not_vector"
	return type

