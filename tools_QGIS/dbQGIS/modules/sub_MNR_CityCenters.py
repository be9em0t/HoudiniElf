# Load Material View based on an Extent layer 

# TO DO
# Select reprojection UTM
# Join feat_type descriptions 
# Reproject Entrypoint layer
# Create Chainage points on Entrypoint layer (points along geometry, Start offset = chainage/100, Distance = 1000 (to make sure theres only 1 point generated per chainage))
# From ADP layer use only 801009 - Building Centroid
# Export them separately to Houdini and build the connectors there

from qgis.core import *
from qgis.core import QgsDataSourceUri, QgsVectorLayer, QgsProject
from qgis.utils import *
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import *
# from qgis.PyQt.QtWidgets import (QWidget, QPushButton, QLineEdit, QInputDialog, QApplication, QLabel,QMessageBox)


# manually append script folder 'cause fucking QGIS
import imp
sys.path.append('d:/Work/OneDrive/Dev/Python/TT_Qgis_Workspace/MNR_automation')
import b9PyQGIS
imp.reload(b9PyQGIS)
from b9PyQGIS import *

geomField = "geom"


def main(svrURL, strStateSchema, clipLayer, extentCoords):
	mnrServer = svrURL
	mnrSchema = strStateSchema
	print ("server is {}\ntable is {}\n".format(mnrServer, mnrSchema))
	
# fLoadAnchorPoints, fLoadEntryPoints
	newLayer = fLoadCityCenters(mnrServer,mnrSchema,extentCoords)
	# fSymbol(newLayer)

# =======

def fLoadCityCenters(mnrServer,mnrSchema,extentCoords):

	# # === db MNR matview ===
	matViewPrefix = "b9view" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "cc"
	extentStr = "'" + extentCoords + "'"


	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	ccFields = b9PyQGIS.fFieldsFromString("cc.", "feat_type,name,admin_class,type_admin_area,type_admin_place,type_neighborhood,geom")
	queryMNRLine =  "CREATE TABLE " + matViewResultTable + " as \nSELECT " + ccFields + " \nFROM " + mnrSchema + ".mnr_citycenter cc " + " \nWHERE ST_Intersects(" + geomField + ",ST_GeomFromText(" + extentStr + ",4326)) ;"
	
	print("\n" + queryDropLine)
	print("\n" + queryMNRLine)

	b9PyQGIS.fPostGISexec(mnrServer, queryDropLine)
	b9PyQGIS.fPostGISexec(mnrServer, queryMNRLine)

	print("\nLoading postgres layer ... ")
	uri = QgsDataSourceUri()
	uri.setConnection(mnrServer, "5432", "mnr", "mnr_ro", "mnr_ro")
	uri.setDataSource("public", matViewResultTable, geomField, aKeyColumn="feat_id")
	newlayer = iface.addVectorLayer(uri.uri(False), matViewResultTable, "postgres")
	return newlayer

