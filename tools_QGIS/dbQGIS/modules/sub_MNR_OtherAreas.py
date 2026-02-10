# Load Material View based on an Extent layer 

from qgis.core import *
from qgis.core import QgsDataSourceUri, QgsVectorLayer, QgsProject
from qgis.utils import *
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import *

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
	
	newLayer = fLoadOtherAreas(mnrServer,mnrSchema,extentCoords)
	newLayer = fClipExtent(newLayer, clipLayer)
	# newLayer2 = fLoadCityCenters(mnrServer,mnrSchema,extentCoords)
	fSymbol(newLayer)

# # =======

def fLoadOtherAreas(mnrServer,mnrSchema,extentCoords):

	# # === db MNR matview ===
	matViewPrefix = "b9view" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "other"
	extentStr = "'" + extentCoords + "'"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	otherFields = b9PyQGIS.fFieldsFromString("other.", "feat_type,name,geom") 	# feat_id,feat_type,name,lang_code,feat_area,feat_perim,traffic_regulation_id,in_car_importance,geopolitical,geom

	enumvalFields = b9PyQGIS.fFieldsFromString("enumval.", "code_description") # enum_value_id,enum_id,code,code_description

	enumFields = b9PyQGIS.fFieldsFromString("enum.", "code_description") # enum_id,enum_description

	# queryMNRLine =  "CREATE TABLE " + matViewResultTable + \
	# 	" as SELECT " + admFields + "," + enumvalFields + \
	# 	" FROM " + mnrSchema + ".mnr_admin_area adm " + \
	# 	" JOIN " + mnrSchema + ".mnr_meta_enum_value enumval ON adm.feat_type::varchar = enumval.code" + \
	# 	" JOIN " + mnrSchema + ".mnr_meta_enum enum ON enum.enum_id = enumval.enum_id" + \
	# 	" WHERE enum.enum_description='Feature Type Admin Area' AND" + \
	# 	" ST_Intersects(adm.geom,ST_GeomFromText(" + extentStr + ",4326)) ;"
	
	queryMNRLine =  "CREATE TABLE " + matViewResultTable + \
		" as SELECT " + otherFields + "," + enumvalFields + \
		" FROM " + mnrSchema + ".mnr_other_display_area other " + \
		" JOIN " + mnrSchema + ".mnr_meta_enum_value enumval ON other.feat_type::varchar = enumval.code" + \
		" JOIN " + mnrSchema + ".mnr_meta_enum enum ON enum.enum_id = enumval.enum_id" + \
		" WHERE enum.enum_description='Feature Type Other Display Area' AND" + \
		" ST_Intersects(other.geom,ST_GeomFromText(" + extentStr + ",4326)) ;"
	
	print("\n" + queryDropLine)
	print("\n" + queryMNRLine)

	b9PyQGIS.fPostGISexec(mnrServer, queryDropLine)
	b9PyQGIS.fPostGISexec(mnrServer, queryMNRLine)

	print("\nLoading postgres layer ... ")
	uri = QgsDataSourceUri()
	uri.setConnection(mnrServer, "5432", "mnr", "mnr_ro", "mnr_ro")
	uri.setDataSource("public", matViewResultTable, "geom", aKeyColumn="feat_type")
	newLayer = iface.addVectorLayer(uri.uri(False), matViewResultTable, "postgres")
	return newLayer


def fLoadCityCentersWIP(mnrServer,mnrSchema,extentCoords):

	# # === db MNR matview ===
	matViewPrefix = "b9view" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "entrypoints"
	extentStr = "'" + extentCoords + "'"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	cyticFields = b9PyQGIS.fFieldsFromString("cytic.", "feat_id,feat_type,geom") 	


	queryMNRLine =  "CREATE TABLE " + matViewResultTable + " as \nSELECT " + netwFields + "," + routeFields + "," + entryFields + " \nFROM " + mnrSchema + ".MNR_CityCenter cytic " + "\nJOIN " + mnrSchema + ".mnr_netw_route_link route ON netw.feat_id=route.netw_geo_id" + "\nJOIN " + mnrSchema + ".mnr_apt_entrypoint entry ON route.feat_id=entry.netw_id" + " \nWHERE ST_Intersects(" + geomField + ",ST_GeomFromText(" + extentStr + ",4326)) ;"
	
	# AND \"feat_type\" = 4110

	print("\n" + queryDropLine)
	print("\n" + queryMNRLine)

	b9PyQGIS.fPostGISexec(mnrServer, queryDropLine)
	b9PyQGIS.fPostGISexec(mnrServer, queryMNRLine)

	print("\nLoading postgres layer ... ")
	uri = QgsDataSourceUri()
	uri.setConnection(mnrServer, "5432", "mnr", "mnr_ro", "mnr_ro")
	uri.setDataSource("public", matViewResultTable, "geom", aKeyColumn="feat_id")
	vlayer = iface.addVectorLayer(uri.uri(False), matViewResultTable, "postgres")

	print("\nNow reproject layer to correct UTM Zone and \nadd points along patch (chainage).")
	print("\nMight need to delete extra points where chainage is diferent from offset.")

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

	symbol = QgsFillSymbol.createSimple({'border_width_map_unit_scale': '3x:0,0,0,0,0,0', 'color': '255,199,91,55', 'joinstyle': 'bevel', 'offset': '0,0', 'offset_map_unit_scale': '3x:0,0,0,0,0,0', 'offset_unit': 'MM', 'outline_color': '196,77,7,255', 'outline_style': 'solid', 'outline_width': '1', 'outline_width_unit': 'RenderMetersInMapUnits', 'style': 'solid'})

	newLayer.renderer().setSymbol(symbol)

	newLayer.triggerRepaint()
	iface.layerTreeView().refreshLayerSymbology(layerGeoId)

