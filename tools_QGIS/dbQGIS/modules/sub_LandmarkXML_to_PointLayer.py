# Load TomTom 3DLandmark .xml file and create corresponding points on a new layer.
# Target CRS should be 3857 - the easiest way to convince QGIS is to start with TomTom Raster Layer selected.

from osgeo import ogr, osr

from qgis.core import *
from qgis.core import QgsDataSourceUri, QgsVectorLayer, QgsProject
from qgis.utils import *
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import (QWidget, QPushButton, QLineEdit, QInputDialog, QApplication, QLabel,QMessageBox)

import xml.etree.ElementTree as ET

# Spatial Reference System
inputEPSG = 4326	# WGS84 (lat="1.3504472" lon="103.848968")
outputEPSG = 3857 # WGS84 Pseudo Mercator (11560414.237166962, 150345.01556419468)

coordsInput = []
coordsOutput = []
parent=iface.mainWindow()

def main():
	fLoadLandmarkFile()



# FUNC: Convert a single coordinate tuple
def CRSconvert(coordX, coordY):
	pointX = coordX 
	pointY = coordY

	# create a geometry from coordinates
	point = ogr.Geometry(ogr.wkbPoint)
	point.AddPoint(pointX, pointY)

	# create coordinate transformation
	inSpatialRef = osr.SpatialReference()
	inSpatialRef.ImportFromEPSG(inputEPSG)

	outSpatialRef = osr.SpatialReference()
	outSpatialRef.ImportFromEPSG(outputEPSG)

	coordTransform = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)

	# transform point
	point.Transform(coordTransform)

	# # print/return point in output EPSG 
	# print (point.GetX(), point.GetY())
	return (point.GetX(), point.GetY())
	# return (pointX, pointY)

# FUNC: Process the list of coordinates
def mainCRSconvert(coordsInput):
	for c in coordsInput:
		coordsOutput.append( ( (CRSconvert(c[0],c[1]))[0], (CRSconvert(c[0],c[1]))[1], c[2] ) )


# FUNC: Create new vector layer if there are points to add
def createVectorLayer(coordsOutput):
	if len(coordsOutput) < 1:
		print ("Empty coordinate list!")
	else:
		print ("Vector layer time!")
		# print(coordsOutput)

		# Set up a new Vector Layer
		crs = QgsCoordinateReferenceSystem("EPSG:3857")
		vl = QgsVectorLayer("Point", "LM_Import", "memory")

		from qgis.PyQt.QtCore import QVariant
		pr = vl.dataProvider()
		pr.addAttributes([QgsField("LMID", QVariant.String)])
		vl.setCrs(crs)
		vl.updateFields() 

		# # add some point features
		for v in coordsOutput:
			print(v[0], " | ", v[1])
			f = QgsFeature()
			f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(v[0], v[1])))
			f.setAttributes([v[2]])
			pr.addFeature(f)
			vl.updateExtents() 
			QgsProject.instance().addMapLayer(vl)

def fLoadLandmarkFile():
		# ok = True
		# answer = functionString
		xmlIn = r'd:\Work\OneDrive - TomTom\3D_projects\QGIS\ParisMNR\HoudiniOrbis\landmarks\f20\fraf20_link.xml'
		answer , ok = QInputDialog.getText(parent, "pyQGIS", "Selected this function sequence:                       ",
							QLineEdit.Normal, xmlIn)
		if ok:
			xmlIn = answer
			print(xmlIn)
			root = ET.parse(xmlIn).getroot()
			for child in root:
					if child.tag == "Landmark":
							coordsInput.append((float(child.attrib['lat']), float(child.attrib['lon']), child.attrib['id']))

			mainCRSconvert(coordsInput)
			createVectorLayer(coordsOutput)
			
			print("=== Finished ===")

		else:
			print("=== Cancelled ===")

