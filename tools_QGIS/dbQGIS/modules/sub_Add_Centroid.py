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

def fAddChainagePoints():
	print("Make sure to reproject layer to screen coord system, otherwise distance is expected in degrees")
	layerGeoInit = iface.activeLayer() # get current layer
	layerGeoId = layerGeoInit.id() # get current layer
	layerGeoBaseName = layerGeoInit.name()

		# print('Reproject layer...')
	# epsgString = '4326'
	epsgString = '3857'
	newLayer = b9PyQGIS.fReprojectLayer(layerGeoId, epsgString)
	wgs_Layer = QgsProject.instance().addMapLayer(newLayer['OUTPUT'])
	wgs_Layer.setName(layerGeoBaseName + '_' + epsgString)
	layerGeoId = wgs_Layer.id()

	result = b9PyQGIS.fPointsAlongLines(layerGeoId)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layerGeoBaseName + '_chainage')
	QgsProject.instance().removeMapLayer(layerGeoId)


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

#convet back to WGS84
def fConvertToWGS84(selected_location):
	from pyproj import Transformer

	# read config file
	iniFile = os.path.dirname( imp.find_module('b9PyQGIS')[1] ) + "/" + 'b9QGISdata.ini'
	config = configparser.ConfigParser()
	config.read(iniFile)
	coords = config['locations'][selected_location].split(",")

	# Initialize the transformer
	transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

	# location,coords = fGetExportLocation(selected_location)
	print(f"Selected location name is {selected_location} with coords\n{coords}")
	offsetXm = float(coords[0])
	offsetYm = float(coords[1])

	# Coordinate in EPSG:3857 (e.g., Web Mercator)
	# x, y = -8236274.21961, 4984069.73941  # Example coordinates
	x, y = offsetXm, offsetYm 

	# Perform transformation to EPSG:4326
	longitude, latitude = transformer.transform(x, y)

	print(f"Converted to EPSG:4326: \nLong, Lat = {longitude}, {latitude}")

