# Load Table based on an Extent layer 

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


def main(mnrServer, mnrSchema, clipLayer, extentCoords):
	print("New style netwrkZ with GSC - select function")
	
	# mnrServer = svrURL
	# mnrSchema = strStateSchema
	# print ("server is {}\ntable is {}\n".format(mnrServer, mnrSchema))
	
	# newLayer = fLoadNetworkZ(mnrServer,mnrSchema,extentCoords)
	# newLayer = fMNRNetworkGSCLines(mnrServer,mnrSchema,extentCoords)
	# newLayer = fClipExtent(newLayer, clipLayer)

def fMNRNetworkGSCPoints_main(mnrServer, mnrSchema, clipLayer, extentCoords):
	# print("GSC junction points")
	newLayer = fMNRNetworkGSCPoints(mnrServer,mnrSchema,extentCoords)
	# newLayer = fClipExtent(newLayer, clipLayer)

def fMNRNetworkGSCLines_main(mnrServer, mnrSchema, clipLayer, extentCoords):
	# print("GSC network lines")
	newLayer = fMNRNetworkGSCLines(mnrServer,mnrSchema,extentCoords)
	newLayer = fClipExtent(newLayer, clipLayer)


def fMNRNetworkGSCLines(mnrServer,mnrSchema,extentCoords):
	matViewPrefix = "b9" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "netw_gsc"
	extentStr = "'" + extentCoords + "'"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	sql = f"""
	SELECT 
		geo.feat_id, geo.ft_road_element, geo.ft_ferry_element ,geo.ft_railway_element, geo.geom,
		route.name, route.part_of_structure, route.display_class, route.routing_class, route.form_of_way, route.num_of_lanes, route.overtaking_lane, route.simple_traffic_direction as direction, route.junction_id_from, route.junction_id_to,
		jfrom.z_level as fr_z_level, jto.z_level as to_z_level
	FROM {mnrSchema}.mnr_netw_geo_link geo  
	LEFT JOIN {mnrSchema}.mnr_netw_route_link route ON geo.feat_id = route.netw_geo_id 
	LEFT JOIN {mnrSchema}.mnr_junction jfrom ON route.junction_id_from=jfrom.feat_id 
	LEFT JOIN {mnrSchema}.mnr_junction jto ON route.junction_id_to=jto.feat_id 
	WHERE  "ft_address_area_boundary_element" != True 
	AND ST_Intersects(geo.geom,ST_GeomFromText({extentStr}, 4326));"""
	## geo.ada_compliant,
	## route.transition, route.freeway, route.freeway_connect, route.freeway_entrance_exit, route.ramp, route.carriageway_designator, 
	## jfrom.jt_regular as fr_jt_regular, jfrom.jt_bifurcation as fr_jt_bifurcation, jfrom.jt_railway_crossing as fr_jt_railway_crossing,
	## jto.jt_regular as to_jt_regular, jto.jt_bifurcation as to_jt_bifurcation, jto.jt_railway_crossing as to_jt_railway_crossing
	## jfrom.geom as fr_geom, jto.geom as to_geom

	queryMNRLine = f"""CREATE TABLE {matViewResultTable} as {sql}"""

	# print("\n" + queryDropLine)
	# print("\n" + queryMNRLine)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	# Ask Yes/No question
	parent=iface.mainWindow()
	message = """\nThe query is on the clipboard.\nDo you want to run it in QGIS?"""
	responce=QMessageBox.question(parent,'MNR Query Question', message)

	if responce==QMessageBox.Yes:
		# QMessageBox.information(parent,'Your decision',"Let's go")
				
		b9PyQGIS.fPostGISexec(mnrServer, queryDropLine)
		b9PyQGIS.fPostGISexec(mnrServer, queryMNRLine)

		print("\nLoading postgres layer ... ")
		uri = QgsDataSourceUri()
		uri.setConnection(mnrServer, "5432", "mnr", "mnr_ro", "mnr_ro")
		uri.setDataSource("public", matViewResultTable, "geom", aKeyColumn="feat_type")
		newLayer = iface.addVectorLayer(uri.uri(False), matViewResultTable, "postgres")
		return newLayer
	else:
		return "Cancel"

def fMNRNetworkGSCPoints(mnrServer,mnrSchema,extentCoords):
	# # === db MNR matview ===
	matViewPrefix = "b9" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "gsc"
	extentStr = "'" + extentCoords + "'"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	sql = f"""
	SELECT 
	gsc_el.gsc_id, gsc_el.seq_num, gsc_el.netw_id, gsc_el.junction_id, gsc_el.railway_id, gsc_el.water_area_id, gsc_el.water_line_id, gsc_el.z_level,
	gsc.feat_id, gsc.feat_type, gsc.merging_reference, gsc.geom
	from {mnrSchema}.mnr_gsc_element gsc_el
	join {mnrSchema}.mnr_gsc gsc on gsc_el.gsc_id = gsc.feat_id
	WHERE
	ST_Intersects(gsc.geom,ST_GeomFromText({extentStr}, 4326))
	;"""

	queryMNRLine = f"""CREATE TABLE {matViewResultTable} as {sql}"""

	# print("\n" + queryDropLine)
	# print("\n" + queryMNRLine)

	# Put query on the clipboard
	clipboard = QgsApplication.clipboard()
	clipboard.setText(sql)

	# Ask Yes/No question
	parent=iface.mainWindow()
	message = """\nThe query is on the clipboard.\nDo you want to run it in QGIS?"""
	responce=QMessageBox.question(parent,'MNR Query Question', message)

	if responce==QMessageBox.Yes:
		# QMessageBox.information(parent,'Your decision',"Let's go")
				
		b9PyQGIS.fPostGISexec(mnrServer, queryDropLine)
		b9PyQGIS.fPostGISexec(mnrServer, queryMNRLine)

		print("\nLoading postgres layer ... ")
		uri = QgsDataSourceUri()
		uri.setConnection(mnrServer, "5432", "mnr", "mnr_ro", "mnr_ro")
		uri.setDataSource("public", matViewResultTable, "geom", aKeyColumn="feat_type")
		newLayer = iface.addVectorLayer(uri.uri(False), matViewResultTable, "postgres")
		return newLayer
	else:
		return "Cancel"


def fLoadNetworkZ(mnrServer,mnrSchema,extentCoords):

	# # === db MNR matview ===
	matViewPrefix = "b9" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "netw"
	extentStr = "'" + extentCoords + "'"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	geoFields = b9PyQGIS.fFieldsFromString("geo.", "feat_id,ft_road_element as road,ft_ferry_element as ferry,ft_railway_element as rail,ada_compliant,geom") # feat_id,ft_road_element,ft_ferry_element,ft_address_area_boundary_element,ft_railway_element,country_left,country_right,centimeters,positional_accuracy,ada_compliant,in_car_importance,geom

	routeFields = b9PyQGIS.fFieldsFromString("route.", "name,part_of_structure as structure,display_class,routing_class,form_of_way,num_of_lanes as lanes,transition,freeway,freeway_connect,freeway_entrance_exit,ramp,carriageway_designator as carriageway,overtaking_lane,simple_traffic_direction as direction") # feat_id,feat_type,name,lang_code,netw_geo_id,ferry_type,junction_id_from,junction_id_to,part_of_structure,urban,back_road,stubble,processing_status,transition,display_class,routing_class,form_of_way,freeway,freeway_connect,freeway_entrance_exit,ramp,carriageway_designator,road_condition,no_through_traffic,rough_road,plural_junction,restricted_access,lez_restriction,toll_restriction,construction_status,demolition_date,simple_traffic_direction,blocked_passage_start,blocked_passage_end,num_of_lanes,speed_category,speedmax_pos,speedmax_neg,speed_dynamic,speed_average_pos,speed_average_neg,average_travel_time_pos,average_travel_time_neg,tourist_route_scenic,tourist_route_national,tourist_route_regional,tourist_route_nature,tourist_route_cultural,no_pedestrian_passage,not_crossable_by_pedestrians,ownership,overtaking_lane,school_zone

	fromFields = b9PyQGIS.fFieldsFromString("jfrom.", "z_level as fr_z_level") # jt_regular as fr_jt_regular,jt_bifurcation as fr_jt_bifurcation,jt_railway_crossing as fr_jt_railway_crossing,z_level as fr_z_level 

	toFields = b9PyQGIS.fFieldsFromString("jto.", "z_level as to_z_level") # jt_regular as fr_jt_regular,jt_bifurcation as fr_jt_bifurcation,jt_railway_crossing as fr_jt_railway_crossing,z_level as fr_z_level 

	metaFields = b9PyQGIS.fFieldsFromString("meta.", "code_description as fow_desc") # enum_value_id,enum_id,code,code_description

	metaCodeDescript = 'Form Of Way'

	queryMNRLine =  "CREATE TABLE " + matViewResultTable + " as \
		SELECT " + geoFields + "," + routeFields + "," + fromFields + "," + toFields + "," + metaFields + \
		" FROM " + mnrSchema + ".mnr_netw_geo_link geo " + \
		" LEFT JOIN " + mnrSchema + ".mnr_netw_route_link route ON geo.feat_id = route.netw_geo_id" + \
		" LEFT JOIN " + mnrSchema + ".mnr_junction jfrom ON route.junction_id_from=jfrom.feat_id" + \
		" LEFT JOIN " + mnrSchema + ".mnr_junction jto ON route.junction_id_to=jto.feat_id" + \
		" LEFT JOIN (" + \
		"  SELECT code, code_description" + \
		"  FROM " + mnrSchema + ".mnr_meta_enum_value enumval" + \
		"    WHERE enumval.enum_id=(" + \
		"    SELECT enum_id FROM " + mnrSchema + ".mnr_meta_enum enum" + \
		"    WHERE enum.enum_description=\'" + metaCodeDescript + "\')" + \
		"  ORDER BY code_description" + \
		"  ) as meta" + \
		" ON route.form_of_way::varchar = meta.code" + \
		" WHERE " + \
		" \"ft_address_area_boundary_element\" != True AND" + \
		" ST_Intersects(geo.geom,ST_GeomFromText(" + extentStr + ",4326)) ;"

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


def fClipExtent(layer,extentLayer):
	print ("Clip by Extent...")
	result = b9PyQGIS.fExtractByExtent(layer, extentLayer)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layer.name() + '_Clip_UUID')
	# layer.setName(layer.name() + '_Org')
	QgsProject.instance().removeMapLayer(layer)
	return newLayer
