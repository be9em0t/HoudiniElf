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


def main(svrURL, strStateSchema, clipLayer, extentCoords):
	mnrServer = svrURL
	mnrSchema = strStateSchema
	print ("server is {}\ntable is {}\n".format(mnrServer, mnrSchema))
	
	newLayer = fLoadNetworkZ(mnrServer,mnrSchema,extentCoords)
	newLayer = fClipExtent(newLayer, clipLayer)
	# fSymbol(newLayer)

def fLoadNetworkZ(mnrServer,mnrSchema,extentCoords):

	# # === db MNR matview ===
	matViewPrefix = "b9" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "speedprofz"
	extentStr = "'" + extentCoords + "'"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	geoFields = b9PyQGIS.fFieldsFromString("geo.", "feat_id,ft_road_element as road,ada_compliant,geom") # feat_id,ft_road_element,ft_ferry_element,ft_address_area_boundary_element,ft_railway_element,country_left,country_right,centimeters,positional_accuracy,ada_compliant,in_car_importance,geom

	routeFields = b9PyQGIS.fFieldsFromString("route.", "name,display_class,routing_class,form_of_way,simple_traffic_direction as road_direction,speed_category,speedmax_pos,speedmax_neg,speed_dynamic,speed_average_pos,speed_average_neg") 
					# feat_id,feat_type,name,lang_code,netw_geo_id,ferry_type,junction_id_from,junction_id_to,part_of_structure,urban,back_road,stubble,processing_status,transition,display_class,routing_class,form_of_way,freeway,freeway_connect,freeway_entrance_exit,ramp,carriageway_designator,road_condition,no_through_traffic,rough_road,plural_junction,restricted_access,lez_restriction,toll_restriction,construction_status,demolition_date,simple_traffic_direction,blocked_passage_start,blocked_passage_end,num_of_lanes,speed_category,speedmax_pos,speedmax_neg,speed_dynamic,speed_average_pos,speed_average_neg,average_travel_time_pos,average_travel_time_neg,tourist_route_scenic,tourist_route_national,tourist_route_regional,tourist_route_nature,tourist_route_cultural,no_pedestrian_passage,not_crossable_by_pedestrians,ownership,overtaking_lane,school_zone

	netw2speedFields = b9PyQGIS.fFieldsFromString("netw2speed.", "validity_direction as speed_direction") 

	speedprofileFields = b9PyQGIS.fFieldsFromString("spdpr.", "weekday_speed,weekend_speed,free_flow_speed") 

	fromFields = b9PyQGIS.fFieldsFromString("jfrom.", "z_level as fr_z_level") # jt_regular as fr_jt_regular,jt_bifurcation as fr_jt_bifurcation,jt_railway_crossing as fr_jt_railway_crossing,z_level as fr_z_level 

	toFields = b9PyQGIS.fFieldsFromString("jto.", "z_level as to_z_level") # jt_regular as fr_jt_regular,jt_bifurcation as fr_jt_bifurcation,jt_railway_crossing as fr_jt_railway_crossing,z_level as fr_z_level 

	metaFields = b9PyQGIS.fFieldsFromString("meta.", "code_description as fow_desc") # enum_value_id,enum_id,code,code_description

	metaCodeDescript = 'Form Of Way'

	queryMNRLine =  "CREATE TABLE " + matViewResultTable + " as \
		SELECT " + geoFields + "," + routeFields + "," + netw2speedFields + "," + speedprofileFields + "," + fromFields + "," + toFields + \
		" FROM " + mnrSchema + ".mnr_netw_geo_link geo " + \
		" LEFT JOIN " + mnrSchema + ".mnr_netw_route_link route ON geo.feat_id = route.netw_geo_id" + \
		" LEFT JOIN " + mnrSchema + ".mnr_netw2speed_profile netw2speed ON route.feat_id=netw2speed.netw_id" + \
		" LEFT JOIN " + mnrSchema + ".mnr_speed_profile spdpr ON netw2speed.SPEED_PROFILE_ID = spdpr.speed_profile_id" + \
		" LEFT JOIN " + mnrSchema + ".mnr_junction jfrom ON route.junction_id_from=jfrom.feat_id" + \
		" LEFT JOIN " + mnrSchema + ".mnr_junction jto ON route.junction_id_to=jto.feat_id" + \
		" WHERE " + \
		" \"ft_address_area_boundary_element\" != True AND" + \
		" \"ft_road_element\" = True AND" + \
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
	newLayer.setName(layer.name() + '_Clip')
	# layer.setName(layer.name() + '_Org')
	QgsProject.instance().removeMapLayer(layer)
	return newLayer
