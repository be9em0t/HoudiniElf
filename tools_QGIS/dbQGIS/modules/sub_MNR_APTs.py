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
	newLayer = fLoadAnchorPoints(mnrServer,mnrSchema,extentCoords)
	# fSymbol(newLayer)
	newLayer = fLoadEntryPoints(mnrServer,mnrSchema,extentCoords)
	# fSymbol(newLayer)

# =======

def fLoadAnchorPoints(mnrServer,mnrSchema,extentCoords):

	# # === db MNR matview ===
	matViewPrefix = "b9view" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "apts"
	extentStr = "'" + extentCoords + "'"


	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	aptFields = b9PyQGIS.fFieldsFromString("apt.", "feat_type,geom") 	# feat_id,feat_type,geocoding_method,in_car_importance,geom

	entryFields = b9PyQGIS.fFieldsFromString("entry.", "apt_id,ep_type_main,ep_type_routing,ep_type_postal,ep_type_delivery,ep_type_pedestrian,ep_type_parking,ep_type_front_door") 	# apt_id,netw_id,chainage,line_side,gav,ep_type_main,ep_type_routing,ep_type_postal,ep_type_emergency,ep_type_delivery,ep_type_pedestrian,ep_type_authorized,ep_type_parking,ep_type_front_door,ep_type_other

	queryMNRLine =  "CREATE TABLE " + matViewResultTable + " as \nSELECT " + aptFields + "," + entryFields + " \nFROM " + mnrSchema + ".mnr_apt apt " + "\nJOIN " + mnrSchema + ".mnr_apt_entrypoint entry ON apt.feat_id=entry.apt_id" + " \nWHERE ST_Intersects(" + geomField + ",ST_GeomFromText(" + extentStr + ",4326)) ;"
	
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



def fLoadEntryPoints(mnrServer,mnrSchema,extentCoords):

	# # === db MNR matview ===
	matViewPrefix = "b9view" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "entrypoints"
	extentStr = "'" + extentCoords + "'"


	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	aptFields = b9PyQGIS.fFieldsFromString("apt.", "feat_id,geom") 	# feat_id,feat_type,geocoding_method,in_car_importance,geom

	entryFields = b9PyQGIS.fFieldsFromString("entry.", "apt_id,chainage,line_side") 	# apt_id,netw_id,chainage,line_side,gav,ep_type_main,ep_type_routing,ep_type_postal,ep_type_emergency,ep_type_delivery,ep_type_pedestrian,ep_type_authorized,ep_type_parking,ep_type_front_door,ep_type_other

	netwFields = b9PyQGIS.fFieldsFromString("netw.", "geom") # feat_id,ft_road_element,ft_ferry_element,ft_address_area_boundary_element,ft_railway_element,country_left,country_right,centimeters,positional_accuracy,ada_compliant,in_car_importance,geom

	routeFields = b9PyQGIS.fFieldsFromString("route.", "name") # feat_id,feat_type,name,lang_code,netw_geo_id,ferry_type,junction_id_from,junction_id_to,part_of_structure,urban,back_road,stubble,processing_status,transition,display_class,routing_class,form_of_way,freeway,freeway_connect,freeway_entrance_exit,ramp,carriageway_designator,road_condition,no_through_traffic,rough_road,plural_junction,restricted_access,lez_restriction,toll_restriction,construction_status,demolition_date,simple_traffic_direction,blocked_passage_start,blocked_passage_end,num_of_lanes,speed_category,speedmax_pos,speedmax_neg,speed_dynamic,speed_average_pos,speed_average_neg,average_travel_time_pos,average_travel_time_neg,tourist_route_scenic,tourist_route_national,tourist_route_regional,tourist_route_nature,tourist_route_cultural,no_pedestrian_passage,not_crossable_by_pedestrians,ownership,overtaking_lane,school_zone


	queryMNRLine =  "CREATE TABLE " + matViewResultTable + " as \nSELECT " + netwFields + "," + routeFields + "," + entryFields + " \nFROM " + mnrSchema + ".mnr_netw_geo_link netw " + "\nJOIN " + mnrSchema + ".mnr_netw_route_link route ON netw.feat_id=route.netw_geo_id" + "\nJOIN " + mnrSchema + ".mnr_apt_entrypoint entry ON route.feat_id=entry.netw_id" + " \nWHERE ST_Intersects(" + geomField + ",ST_GeomFromText(" + extentStr + ",4326)) ;"

	print("\n" + queryDropLine)
	print("\n" + queryMNRLine)

	b9PyQGIS.fPostGISexec(mnrServer, queryDropLine)
	b9PyQGIS.fPostGISexec(mnrServer, queryMNRLine)

	print("\nLoading postgres layer ... ")
	uri = QgsDataSourceUri()
	uri.setConnection(mnrServer, "5432", "mnr", "mnr_ro", "mnr_ro")
	uri.setDataSource("public", matViewResultTable, geomField, aKeyColumn="feat_id")
	newlayer = iface.addVectorLayer(uri.uri(False), matViewResultTable, "postgres")

	print("\nNow reproject layer to correct UTM Zone and \nadd points along patch (chainage).")
	print("\nMight need to delete extra points where chainage is diferent from offset.")
	return newlayer
