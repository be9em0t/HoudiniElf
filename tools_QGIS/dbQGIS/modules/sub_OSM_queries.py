# Add meter distance from ZeroIsland as text field

from qgis.core import *
from qgis.core import QgsDataSourceUri, QgsVectorLayer, QgsProject
from qgis.utils import *
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import *
# import processing

# from qgis.PyQt.QtWidgets import (QWidget, QPushButton, QLineEdit, QInputDialog, QApplication, QLabel,QMessageBox)


# manually append script folder 'cause fucking QGIS
import imp
sys.path.append('d:/Work/OneDrive/Dev/Python/TT_Qgis_Workspace/MNR_automation')
import b9PyQGIS
imp.reload(b9PyQGIS)
from b9PyQGIS import *


def main(svrURL, strStateSchema, clipLayer, extentCoords):
	mnrServer = svrURL
	mnrSchema = strStateSchema
	print ("server is {}\ntable is {}\n".format(mnrServer, mnrSchema))
	
	# newLayer = fLoadTableBuildings(mnrServer,mnrSchema,extentCoords)
	# fSymbol(newLayer)
	newLayer = fAddCoords()


def fGetOSMTrees(extent_layer):
	root = QgsProject.instance().layerTreeRoot()

	# layerGeoInit = iface.activeLayer() # get current layer
	layerGeoInit = extent_layer
	layerGeoId = layerGeoInit.id() # get current layer
	layerGeoBaseName = layerGeoInit.name()

	searchString = "extent"
	if searchString.lower() not in layerGeoBaseName.lower(): #test for extent
		print("Not a good Extent, trying the Active layer...")
		layerGeoInit = iface.activeLayer() # get current layer
		layerGeoId = layerGeoInit.id() # get current layer
		layerGeoBaseName = layerGeoInit.name()
		if searchString.lower() not in layerGeoBaseName.lower():
			print("Not a good Active layer. Pick an extent layer!\nCancelling.")
			return

	print(f"Using \'{layerGeoBaseName}\' as extent")

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
	xLonMaxE = max(newLayer.uniqueValues(idx))
	xLonMinW = min(newLayer.uniqueValues(idx))
	idx = newLayer.fields().indexOf('ycoord')
	print(newLayer.uniqueValues(idx))
	yLatMaxN = max(newLayer.uniqueValues(idx))
	yLatMinS = min(newLayer.uniqueValues(idx))

	# (south_latitude, west_longitude, north_latitude, east_longitude)
	sBboxOSM = str(yLatMinS) + "," + str(xLonMinW) + "," + str(yLatMaxN) + "," + str(xLonMaxE)
	print( "set length is {}, \nxMax is {}, xMin is {}, \nyMax is {}, yMin is {}".format(xLength, xLonMaxE,xLonMinW,yLatMaxN,yLatMinS) )
	print( "Coordinates to paste to Overpass Turbo are:\n{}".format(sBboxOSM) )
	QgsProject.instance().removeMapLayer(layerGeoId)

		# set active layer
	iface.setActiveLayer(layerGeoInit)

	# Buildings from Building Footprints (old style) - 
	overpassQuery = """
/*
This has been generated in Python.
The idea is to search for tree-related geometry
*/
[out:json]
[timeout:25][bbox:{extent}];
// gather results
(
	nwr["natural"="wood"];
	nwr["natural"="tree"];
	nwr["natural"="tree_row"];
	nwr["natural"="shrub"];
	nwr["barrier"="hedge"];
);
// print results
out geom;
	""".format(extent=sBboxOSM)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(overpassQuery)

	message = """\nThe query is on the clipboard.\nPaste and run it in OverpassTurbo.\nThen import the JSON as a vector layer to QGIS."""
	print(message + "\n======= clipboard! =======")
	qtMsgBox(message)

def fCleanupOSMTrees():
	layerGeo = iface.activeLayer() # get current layer
	layerGeoId = layerGeo.id() # get current layer
	layerGeoBaseName = layerGeo.name()

	aRetainFields = ['natural','leaf_cycle','leaf_type','name','height','denotation','species','start_date','genus']
	result = b9PyQGIS.fRetainFields(layerGeo, aRetainFields)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_Fields')
	# layerGeoId = newLayer.id()


def fGetExtentCoords_OFF():
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


def fAddCentroid_OFF():
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

def fGetUTMcentroid_OFF():
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


	# set active layer
	iface.setActiveLayer(layerGeoInit)

def fAddChainagePoints_OFF():
	layerGeoInit = iface.activeLayer() # get current layer
	layerGeoId = layerGeoInit.id() # get current layer
	layerGeoBaseName = layerGeoInit.name()

	result = b9PyQGIS.fPointsAlongLines(layerGeoId)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_chainage')


def fEPsFromMNR_OFF():
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



def fReprojectUTM_OFF():
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

	layerGeoId = result['OUTPUT']
	print(layerGeoId)
	newLayer = root.findLayer(layerGeoId)
	print(newLayer)
	newLayer.setName(layerGeoBaseName + '_reproject')
	# QgsProject.instance().removeMapLayer(layerGeoId)
	# layerGeoId = newLayer.id()



# 326 -> N + UTM
# 327 -> S + UTM