# Load Material View based on an Extent layer 

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

	#  fLoadTableLandUse, fSymbol' 	
	newLayer = fLoadTableLandUse(mnrServer,mnrSchema,extentCoords)
	newLayer = fClipExtent(newLayer, clipLayer)
	fSymbol(newLayer)


def fLoadTableLandUse(mnrServer,mnrSchema,extentCoords):

	# # === db MNR matview ===
	matViewPrefix = "b9" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "land_use"
	extentStr = "'" + extentCoords + "'"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	landGeoFields = b9PyQGIS.fFieldsFromString("land.","feat_id,feat_type,drawing_order as draw_order,geom") # feat_id,feat_type,name,lang_code,feat_area,feat_perim,drawing_order,airport_code,importance,park_type,park_classification,building_class,publicly_accessible,quality_mark,military_service_branch,forest_type,sand_area_type,university_classification,company_ground_type,playing_field_type,surface_type,mixed_green_type,in_car_importance,geom
	metaFields = b9PyQGIS.fFieldsFromString("meta.", "code_description as Type") # enum_value_id,enum_id,code,code_description

	metaCodeDescript = 'Feature Type Landcover And Use'

	metaCodeDescriptSelect = "(\'Airport Ground\',\'Airport Runway\',\'Amusement Park Ground\',\'Beach Dune And Sand Plain\',\'Camping Site Ground\',\'Cemetery Ground\',\'Forest\',\'Golf Course Ground\',\'Hippodrome Ground\',\'Holiday Area Ground\',\'Island\',\'Military Cemetery Ground\',\'Mixed Green\',\'Moor And Heathland\',\'Nature Reserve Ground\',\'Other Land Use\',\'Parking Area Ground\',\'Park Or Garden\',\'Playing Field\',\'Recreational Area Ground\',\'Sports Hall Ground\',\'Stadium Ground\',\'Walking Terrain Ground\',\'Zoo Ground\')"
	
	# "Abbey Ground,Address Area,Airport Ground,Airport Runway,Amusement Park Ground,Arts Center Ground,Beach Dune And Sand Plain,Building Area,Camping Site Ground,Car Racetrack Ground,Castle Not To Visit Ground,Castle To Visit Ground,Cemetery Ground,Church Ground,City Hall Ground,Company Ground,Courthouse Ground,Fire Station Ground,Forest,Fortress Ground,Freeport Ground,Golf Course Ground,Government Building Ground,Hippodrome Ground,Holiday Area Ground,Hospital Ground,Hotel Or Motel Ground,Industrial Area,Industrial Harbor Area,Institutions,Island,Library Ground,Light House Ground,Military Cemetery Ground,Military Territory,Mixed Green,Monastery Ground,Monument Ground,Moor And Heathland,Museum Ground,Nature Reserve Ground,Other Land Use,Parking Area Ground,Park Or Garden,Petrol Station Ground,Place Of Interest Building Ground,Playing Field,Police Office Ground,Post Office Ground,Prison Ground,Railway Station Ground,Recreational Area Ground,Rest Area Ground,Restaurant Ground,Rocks Ground,School Ground,Shopping Center Ground,Sports Hall Ground,Stadium Ground,State Police Office Ground,Theater Ground,University Or College Ground,View Ground,Walking Terrain Ground,Water Mill Ground,Windmill Ground,Zoo Ground"

	queryMNRLine =  "CREATE TABLE " + matViewResultTable + " as" +\
	" SELECT " + landGeoFields + "," + metaFields +\
		" FROM " + mnrSchema + ".mnr_land_use_cover  land" +\
		" JOIN (" +\
		"   SELECT * from " + mnrSchema + ".mnr_meta_enum  enu" +\
		"   JOIN " + mnrSchema + ".mnr_meta_enum_value  val" +\
		"   ON enu.enum_id = val.enum_id" +\
		"   WHERE enu.enum_description=\'" + metaCodeDescript + "\'" +\
		"   ORDER by val.code_description" +\
		"   ) meta" +\
		" ON land.feat_type::varchar = meta.code" +\
		" WHERE meta.code_description in " + metaCodeDescriptSelect + " AND" +\
		" ST_Intersects(land.geom,ST_GeomFromText(" + extentStr + ",4326)) ;"

	print("\n" + queryDropLine)
	print("\n" + queryMNRLine)

	b9PyQGIS.fPostGISexec(mnrServer, queryDropLine)
	b9PyQGIS.fPostGISexec(mnrServer, queryMNRLine)

	print("\nLoading postgres layer ... ")
	uri = QgsDataSourceUri()
	uri.setConnection(mnrServer, "5432", "mnr", "mnr_ro", "mnr_ro")
	uri.setDataSource("public", matViewResultTable, "geom", aKeyColumn="feat_type")
	newLayer = iface.addVectorLayer(uri.uri(False), matViewResultTable, "postgres")
	layerGeoId = newLayer.id()
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
	layerGeoId = newLayer.id() 
	# global newLayer

	symbol = QgsFillSymbol.createSimple({ 
		'border_width_map_unit_scale': '3x:0,0,0,0,0,0', 
		'color': '#00AE7D', 
		'outline_color': '0,128,192,255', 'outline_style': 'solid', 'outline_width': '1', 
		'outline_width_unit': 'RenderMetersInMapUnits', 'style': 'solid',
		'joinstyle': 'bevel', 'offset': '0,0', 'offset_map_unit_scale': '3x:0,0,0,0,0,0', 'offset_unit': 'MM', 
		})
	# symbol = QgsFillSymbol.createSimple({'color': '#00AE7D' })

	newLayer.renderer().setSymbol(symbol)

	newLayer.triggerRepaint()
	iface.layerTreeView().refreshLayerSymbology(layerGeoId)
