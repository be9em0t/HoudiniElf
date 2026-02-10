# Load table based on an Extent layer 

from http import client
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


def main(svrURL, strStateSchema, clipLayer, extentCoords):
	mnrServer = svrURL
	mnrSchema = strStateSchema
	print ("server is {}\ntable is {}\n".format(mnrServer, mnrSchema))
	
	newLayer = fLoadTableBuildings(mnrServer,mnrSchema,extentCoords)
	newLayer = fClipExtent(newLayer, clipLayer)
	# fSymbol(newLayer)


def fLoadTableBuildings(mnrServer,mnrSchema,extentCoords):

	# # === db MNR matview ===
	matViewPrefix = "b9" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "build"
	extentStr = "'" + extentCoords + "'"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	footprintFields = b9PyQGIS.fFieldsFromString("footprint.", "feat_id,building_height,ground_height,building_type,is_on_top,geom") # feat_id,feat_type,building_height,ground_height,building_type,is_on_top,simplified_building_cluster_id,in_car_importance,geom

	attrEnumXO = b9PyQGIS.fFieldsFromString("attrEnumXO.", "value_varchar as LM") # attribute_id,building_footprint_id,attribute_type,value_varchar

	attrEnumX3 = b9PyQGIS.fFieldsFromString("attrEnumX3.", "value_varchar as Color_Wall") # attribute_id,building_footprint_id,attribute_type,value_varchar

	attrEnumX4 = b9PyQGIS.fFieldsFromString("attrEnumX4.", "value_varchar as Color_Roof") # attribute_id,building_footprint_id,attribute_type,value_varchar

	queryMNRLine =  "CREATE TABLE " + matViewResultTable + " as" + \
		" SELECT " + footprintFields + "," + attrEnumXO + "," + attrEnumX3 + "," + attrEnumX4 +\
		" FROM " + mnrSchema + ".mnr_building_footprint  footprint" + \
		" LEFT JOIN " + mnrSchema + ".mnr_building_footprint_attribute  attrEnumXO" + \
		" ON footprint.feat_id = attrEnumXO.building_footprint_id AND attrEnumXO.attribute_type = 'XO'" + \
		" LEFT JOIN " + mnrSchema + ".mnr_building_footprint_attribute  attrEnumX3" + \
		" ON footprint.feat_id = attrEnumX3.building_footprint_id AND attrEnumX3.attribute_type = 'X3'" + \
		" LEFT JOIN " + mnrSchema + ".mnr_building_footprint_attribute  attrEnumX4" + \
		" ON footprint.feat_id = attrEnumX4.building_footprint_id AND attrEnumX4.attribute_type = 'X4'" + \
		" WHERE " + \
		" \"feat_type\" = 1900 AND" + \
		" ST_Intersects(footprint.geom,ST_GeomFromText(" + extentStr + ",4326)) ;"

	print("\n" + queryDropLine)
	print("\n" + queryMNRLine)

	b9PyQGIS.fPostGISexec(mnrServer, queryDropLine)
	b9PyQGIS.fPostGISexec(mnrServer, queryMNRLine)

	print("\nLoading postgres layer ... ")
	uri = QgsDataSourceUri()
	uri.setConnection(mnrServer, "5432", "mnr", "mnr_ro", "mnr_ro")
	uri.setDataSource("public", matViewResultTable, "geom", aKeyColumn="feat_type")
	newLayer = iface.addVectorLayer(uri.uri(False), matViewResultTable, "postgres")
	# layerGeoId = newLayer.id()
	return newLayer

def fClipExtent(layer,extentLayer):
	print ("Clip by Extent...")
	result = b9PyQGIS.fExtractByExtent(layer, extentLayer)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layer.name() + '_Clip')
	# layer.setName(layer.name() + '_Org')
	QgsProject.instance().removeMapLayer(layer)
	return newLayer

def fSymbol(newLayer):
	# global newLayer
	layerGeoId = newLayer.id()

	symbol = QgsFillSymbol.createSimple({'border_width_map_unit_scale': '3x:0,0,0,0,0,0', 'color': '188,220,245,255', 'joinstyle': 'bevel', 'offset': '0,0', 'offset_map_unit_scale': '3x:0,0,0,0,0,0', 'offset_unit': 'MM', 'outline_color': '97,173,224,255', 'outline_style': 'solid', 'outline_width': '1', 'outline_width_unit': 'RenderMetersInMapUnits', 'style': 'solid'})

	newLayer.renderer().setSymbol(symbol)

	newLayer.triggerRepaint()
	iface.layerTreeView().refreshLayerSymbology(layerGeoId)

