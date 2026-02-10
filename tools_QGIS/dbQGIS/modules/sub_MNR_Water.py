# Load Material View based on an Extent layer 

# To get ocean water
# extract natural:Costline (its a line feature)
# convert extent to lines
# merge both
# polygonize
# delete unnecessary part


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
	
	# fLoadTableWaterArea, fSymbolArea, fLoadTableWaterLine, fSymbolLine
	newLayer = fLoadTableWaterArea(mnrServer,mnrSchema,extentCoords)
	newLayer = fClipExtent(newLayer, clipLayer)
	fSymbolArea(newLayer)
	newLayer = fLoadTableWaterLine(mnrServer,mnrSchema,extentCoords)
	newLayer = fClipExtent(newLayer, clipLayer)
	fSymbolLine(newLayer)


def fLoadTableWaterArea(mnrServer,mnrSchema,extentCoords):

	# # === db MNR matview ===
	matViewPrefix = "b9" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "waterarea"
	extentStr = "'" + extentCoords + "'"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	waterFields = b9PyQGIS.fFieldsFromString("water.", "feat_id,geom") # feat_id,feat_type,feat_area,feat_perim,name,lang_code,water_type,display_class,label_class,in_car_importance,geom

	metaFields = b9PyQGIS.fFieldsFromString("meta.", "code_description as Type") # enum_value_id,enum_id,code,code_description

	metaCodeDescript = 'Water Element Type'

 
	queryMNRLine =  "CREATE TABLE " + matViewResultTable + " as" + \
		" SELECT " + waterFields + "," + metaFields +\
		" FROM " + mnrSchema + ".mnr_water_area  water" + \
		" LEFT JOIN (" + \
		"  SELECT code, code_description" + \
		"  FROM " + mnrSchema + ".mnr_meta_enum_value enumval" + \
		"    WHERE enumval.enum_id=(" + \
		"    SELECT enum_id FROM " + mnrSchema + ".mnr_meta_enum enum" + \
		"    WHERE enum.enum_description=\'" + metaCodeDescript + "\')" + \
		"  ORDER BY code_description" + \
		"  ) as meta" + \
		" ON water.water_type::varchar = meta.code" + \
		" WHERE " + \
		" ST_Intersects(water.geom,ST_GeomFromText(" + extentStr + ",4326)) ;"

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


def fLoadTableWaterLine(mnrServer,mnrSchema,extentCoords):

	# # === db MNR matview ===
	matViewPrefix = "b9" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "waterline"
	extentStr = "'" + extentCoords + "'"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	waterFields = b9PyQGIS.fFieldsFromString("water.", "geom") # feat_id,feat_type,feat_area,feat_perim,name,lang_code,water_type,display_class,label_class,in_car_importance,geom

	metaFields = b9PyQGIS.fFieldsFromString("meta.", "code_description as Type") # enum_value_id,enum_id,code,code_description

	metaCodeDescript = 'Water Element Type'
 
	queryMNRLine =  "CREATE TABLE " + matViewResultTable + " as" + \
		" SELECT " + waterFields + "," + metaFields +\
		" FROM " + mnrSchema + ".mnr_water_line  water" + \
		" LEFT JOIN (" + \
		"  SELECT code, code_description" + \
		"  FROM " + mnrSchema + ".mnr_meta_enum_value enumval" + \
		"    WHERE enumval.enum_id=(" + \
		"    SELECT enum_id FROM " + mnrSchema + ".mnr_meta_enum enum" + \
		"    WHERE enum.enum_description=\'" + metaCodeDescript + "\')" + \
		"  ORDER BY code_description" + \
		"  ) as meta" + \
		" ON water.water_type::varchar = meta.code" + \
		" WHERE " + \
		" ST_Intersects(water.geom,ST_GeomFromText(" + extentStr + ",4326)) ;"

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

def fSymbolArea(newLayer):

	symbol = QgsFillSymbol.createSimple({ 
		'border_width_map_unit_scale': '3x:0,0,0,0,0,0', 
		'color': '100,180,226,255', 
		'outline_color': '0,128,192,255', 'outline_style': 'solid', 'outline_width': '1', 
		'outline_width_unit': 'RenderMetersInMapUnits', 'style': 'solid',
		'joinstyle': 'bevel', 'offset': '0,0', 'offset_map_unit_scale': '3x:0,0,0,0,0,0', 'offset_unit': 'MM', 
		})

	newLayer.renderer().setSymbol(symbol)

	newLayer.triggerRepaint()
	iface.layerTreeView().refreshLayerSymbology(newLayer.id())

def fSymbolLine(newLayer):

	symbol = QgsLineSymbol.createSimple({'line_style': 'solid', 'color': '100,180,226,255'})

	# symbol = QgsFillSymbol.createSimple(
	# 	{'align_dash_pattern': '0', 'capstyle': 'square', 'customdash': '5;2', 
	# 	'customdash_map_unit_scale': '3x:0,0,0,0,0,0', 'customdash_unit': 'MM', 
	# 	'dash_pattern_offset': '0', 'dash_pattern_offset_map_unit_scale': '3x:0,0,0,0,0,0', 'dash_pattern_offset_unit': 'MM', 
	# 	'draw_inside_polygon': '0', 'joinstyle': 'bevel', 'line_color': '100,180,226,255', 
	# 	'line_style': 'solid', 'line_width': '0.5', 'line_width_unit': 'MM', 'offset': '0', 'offset_map_unit_scale': '3x:0,0,0,0,0,0', 'offset_unit': 'MM', 'ring_filter': '0', 'trim_distance_end': '0', 'trim_distance_end_map_unit_scale': '3x:0,0,0,0,0,0', 'trim_distance_end_unit': 'MM', 'trim_distance_start': '0', 'trim_distance_start_map_unit_scale': '3x:0,0,0,0,0,0', 'trim_distance_start_unit': 'MM', 'tweak_dash_pattern_on_corners': '0', 'use_custom_dash': '0', 'width_map_unit_scale': '3x:0,0,0,0,0,0'}
	# 	)

	newLayer.renderer().setSymbol(symbol)

	newLayer.triggerRepaint()
	iface.layerTreeView().refreshLayerSymbology(newLayer.id())
