# Load Table based on an Extent layer 

from qgis.core import *
from qgis.core import QgsDataSourceUri, QgsVectorLayer, QgsProject
from qgis.utils import *
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import *
import geopandas as gpd
import re
import json

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
	matViewResultTable = matViewPrefix + "speedprof"
	extentStr = "'" + extentCoords + "'"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	geoFields = b9PyQGIS.fFieldsFromString("geo.", "feat_id,ft_road_element as road,ada_compliant,geom") # feat_id,ft_road_element,ft_ferry_element,ft_address_area_boundary_element,ft_railway_element,country_left,country_right,centimeters,positional_accuracy,ada_compliant,in_car_importance,geom

	routeFields = b9PyQGIS.fFieldsFromString("route.", "name,display_class,routing_class,form_of_way,simple_traffic_direction as direction,speed_category,speedmax_pos,speedmax_neg,speed_dynamic,speed_average_pos,speed_average_neg") 
					# feat_id,feat_type,name,lang_code,netw_geo_id,ferry_type,junction_id_from,junction_id_to,part_of_structure,urban,back_road,stubble,processing_status,transition,display_class,routing_class,form_of_way,freeway,freeway_connect,freeway_entrance_exit,ramp,carriageway_designator,road_condition,no_through_traffic,rough_road,plural_junction,restricted_access,lez_restriction,toll_restriction,construction_status,demolition_date,simple_traffic_direction,blocked_passage_start,blocked_passage_end,num_of_lanes,speed_category,speedmax_pos,speedmax_neg,speed_dynamic,speed_average_pos,speed_average_neg,average_travel_time_pos,average_travel_time_neg,tourist_route_scenic,tourist_route_national,tourist_route_regional,tourist_route_nature,tourist_route_cultural,no_pedestrian_passage,not_crossable_by_pedestrians,ownership,overtaking_lane,school_zone

	netw2speedFields = b9PyQGIS.fFieldsFromString("netw2speed.", "validity_direction") 

	speedprofileFields = b9PyQGIS.fFieldsFromString("spdpr.", "weekday_speed,weekend_speed,free_flow_speed") 

	fromFields = b9PyQGIS.fFieldsFromString("jfrom.", "z_level as fr_z_level") # jt_regular as fr_jt_regular,jt_bifurcation as fr_jt_bifurcation,jt_railway_crossing as fr_jt_railway_crossing,z_level as fr_z_level 

	toFields = b9PyQGIS.fFieldsFromString("jto.", "z_level as to_z_level") # jt_regular as fr_jt_regular,jt_bifurcation as fr_jt_bifurcation,jt_railway_crossing as fr_jt_railway_crossing,z_level as fr_z_level 

	metaFields = b9PyQGIS.fFieldsFromString("meta.", "code_description as fow_desc") # enum_value_id,enum_id,code,code_description

	metaCodeDescript = 'Form Of Way'

	queryMNRLine =  "CREATE TABLE " + matViewResultTable + " as \
		SELECT " + geoFields + "," + routeFields + "," + netw2speedFields + "," + speedprofileFields + \
		" FROM " + mnrSchema + ".mnr_netw_geo_link geo " + \
		" LEFT JOIN " + mnrSchema + ".mnr_netw_route_link route ON geo.feat_id = route.netw_geo_id" + \
		" LEFT JOIN " + mnrSchema + ".mnr_netw2speed_profile netw2speed ON route.feat_id=netw2speed.netw_id" + \
		" LEFT JOIN " + mnrSchema + ".mnr_speed_profile spdpr ON netw2speed.SPEED_PROFILE_ID = spdpr.speed_profile_id" + \
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


def fLoadSpeedProfile5minSlots(svrURL, strStateSchema, clipLayer, extentCoords):
	mnrServer = svrURL
	mnrSchema = strStateSchema
	print ("server is {}\ntable is {}\n".format(mnrServer, mnrSchema))
	# print("fLoadSpeedProfile5minSlots")

	# # === db MNR matview ===
	matViewPrefix = "b9view" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "speed_profiles"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	queryMNRLine = f"""
	CREATE TABLE {matViewResultTable} 
	AS 
	SELECT geo.feat_id,geo.ft_road_element as road, 
	CASE 
	WHEN netw2speed.validity_direction = 1 THEN 'In Both Directions'
	WHEN netw2speed.validity_direction = 2 THEN 'In Positive Direction'
	WHEN netw2speed.validity_direction = 3 THEN 'In Negative Direction'
	ELSE null
	END as validity_description,
	netw2speed.validity_direction,spdprofile.weekday_speed,spdprofile.weekend_speed,spdprofile.free_flow_speed,
	((timeslot.time_slot / 5)/60) as time, timeslot.time_slot, timeslot.relative_speed,
	geo.geom
	FROM {mnrSchema}.mnr_netw_geo_link geo  
	LEFT JOIN {mnrSchema}.mnr_netw_route_link route ON geo.feat_id = route.netw_geo_id 
	LEFT JOIN {mnrSchema}.mnr_netw2speed_profile netw2speed ON route.feat_id=netw2speed.netw_id 
	LEFT JOIN {mnrSchema}.mnr_speed_profile spdprofile ON netw2speed.SPEED_PROFILE_ID = spdprofile.speed_profile_id 
	LEFT JOIN {mnrSchema}.mnr_profile profile on  spdprofile.wednesday_profile_id = profile.profile_id 
	LEFT JOIN {mnrSchema}.mnr_profile2speed_per_time_slot profile2speed on profile.profile_id = profile2speed.profile_id 
	LEFT JOIN {mnrSchema}.mnr_speed_per_time_slot timeslot on profile2speed.speed_per_time_slot_id = timeslot.speed_per_time_slot_id 
	WHERE  
	"ft_road_element" = True 
	AND ST_Intersects(geo.geom, ST_GeomFromText('{extentCoords}', 4326));
	"""

	print("\n" + queryDropLine)
	print("\n" + queryMNRLine)

	b9PyQGIS.fPostGISexec(mnrServer, queryDropLine)
	b9PyQGIS.fPostGISexec(mnrServer, queryMNRLine)

	print("\nLoading postgres layer ... ")
	uri = QgsDataSourceUri()
	uri.setConnection(mnrServer, "5432", "mnr", "mnr_ro", "mnr_ro")
	uri.setDataSource("public", matViewResultTable, "geom", aKeyColumn="feat_type")
	newLayer = iface.addVectorLayer(uri.uri(False), matViewResultTable, "postgres")

	# newLayer = fClipExtent(newLayer, clipLayer)

	return newLayer


def fLoadSpeedProfile5minSlotsAggregateWednesday(svrURL, strStateSchema, clipLayer, extentCoords):
	mnrServer = svrURL
	mnrSchema = strStateSchema
	print ("server is {}\ntable is {}\n".format(mnrServer, mnrSchema))
	# print("fLoadSpeedProfile5minSlots")

	# # === db MNR matview ===
	matViewPrefix = "b9view" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "speed_profiles_array"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	queryMNRLine = f"""
	CREATE TABLE {matViewResultTable} 
	AS 
	SELECT geo.feat_id,route.display_class,
	CASE 
	WHEN netw2speed.validity_direction = 1 THEN 'Both Directions'
	WHEN netw2speed.validity_direction = 2 THEN 'Positive Direction'
	WHEN netw2speed.validity_direction = 3 THEN 'Negative Direction'
	ELSE null
	END AS validity_description,
	netw2speed.validity_direction, spdprofile.free_flow_speed, spdprofile.weekday_speed,spdprofile.weekend_speed,
	ARRAY_AGG(timeslot.time_slot::INTEGER ORDER BY timeslot.time_slot) AS time_slot_array,
	ARRAY_AGG(COALESCE(timeslot.relative_speed::INTEGER, -1) ORDER BY timeslot.time_slot) AS relative_speed_array,
	ARRAY_AGG(COALESCE(((timeslot.time_slot::INTEGER / 5)/60), -1) ORDER BY timeslot.time_slot) AS time_array,
	geo.geom
	FROM {mnrSchema}.mnr_netw_geo_link geo  
	LEFT JOIN {mnrSchema}.mnr_netw_route_link route ON geo.feat_id = route.netw_geo_id 
	LEFT JOIN {mnrSchema}.mnr_netw2speed_profile netw2speed ON route.feat_id=netw2speed.netw_id 
	LEFT JOIN {mnrSchema}.mnr_speed_profile spdprofile ON netw2speed.SPEED_PROFILE_ID = spdprofile.speed_profile_id 
	LEFT JOIN {mnrSchema}.mnr_profile profile on  spdprofile.wednesday_profile_id = profile.profile_id 
	LEFT JOIN {mnrSchema}.mnr_profile2speed_per_time_slot profile2speed on profile.profile_id = profile2speed.profile_id 
	LEFT JOIN {mnrSchema}.mnr_speed_per_time_slot timeslot on profile2speed.speed_per_time_slot_id = timeslot.speed_per_time_slot_id 
	WHERE  
	"ft_road_element" = True 
	AND route.display_class <= 70
	AND ST_Intersects(geo.geom, ST_GeomFromText('{extentCoords}', 4326))
	GROUP BY geo.feat_id, netw2speed.validity_direction, spdprofile.free_flow_speed, spdprofile.weekday_speed,spdprofile.weekend_speed,route.display_class;
	"""

	print("\n" + queryDropLine)
	print("\n" + queryMNRLine)

	b9PyQGIS.fPostGISexec(mnrServer, queryDropLine)
	b9PyQGIS.fPostGISexec(mnrServer, queryMNRLine)

	print("\nLoading postgres layer ... ")
	uri = QgsDataSourceUri()
	uri.setConnection(mnrServer, "5432", "mnr", "mnr_ro", "mnr_ro")
	uri.setDataSource("public", matViewResultTable, "geom", aKeyColumn="feat_type")
	newLayer = iface.addVectorLayer(uri.uri(False), matViewResultTable, "postgres")

	# newLayer = fClipExtent(newLayer, clipLayer)

	return newLayer

def fLoadSpeedProfile5minSlotsAggregateDaySelect(svrURL, strStateSchema, clipLayer, extentCoords):
	mnrServer = svrURL
	mnrSchema = strStateSchema
	print ("server is {}\ntable is {}\n".format(mnrServer, mnrSchema))
	# print("fLoadSpeedProfile5minSlots")

	parent=iface.mainWindow()
	# Input item from drop down list

	# speed_profile_id,weekday_speed,weekend_speed,free_flow_speed,monday_profile_id,tuesday_profile_id,wednesday_profile_id,thursday_profile_id,friday_profile_id,saturday_profile_id,sunday_profile_id

	myoptions=["monday","tuesday","wednesday","thursday","friday","saturday","sunday"] 
	weekday, ok = QInputDialog.getItem(parent, "Select:", "Day of week:", myoptions, 2, False)
	print(weekday)


	# # === db MNR matview ===
	matViewPrefix = "b9view" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + weekday + "_speed_profiles_array"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	queryMNRLine = f"""
CREATE TABLE {matViewResultTable} 
AS 


WITH filtered_geo AS (
	SELECT feat_id, geom
	FROM {mnrSchema}.mnr_netw_geo_link
	WHERE ft_road_element = True 
 	AND ST_Intersects(geom, ST_GeomFromText('{extentCoords}', 4326))
),
filtered_route AS (
	SELECT feat_type, netw_geo_id, display_class, form_of_way
	FROM {mnrSchema}.mnr_netw_route_link
	WHERE display_class <= 70 AND 
	display_class is not null AND 
	feat_type = 4110
)
SELECT geo.feat_id, route.display_class, route.form_of_way,
	CASE 
		WHEN netw2speed.validity_direction = 1 THEN 'Both Directions'
		WHEN netw2speed.validity_direction = 2 THEN 'Positive Direction'
		WHEN netw2speed.validity_direction = 3 THEN 'Negative Direction'
		ELSE null
	END AS validity_description,
	netw2speed.validity_direction, spdprofile.free_flow_speed, spdprofile.weekday_speed, spdprofile.weekend_speed,
	ARRAY_TO_STRING(ARRAY_AGG(timeslot.time_slot::INTEGER ORDER BY timeslot.time_slot), ',') AS time_slot_array,
	ARRAY_TO_STRING(ARRAY_AGG(COALESCE(timeslot.relative_speed::INTEGER, -1) ORDER BY timeslot.time_slot), ',') AS {weekday}_speed_array,
	ARRAY_TO_STRING(ARRAY_AGG(COALESCE(((timeslot.time_slot::INTEGER / 5) / 60), -1) ORDER BY timeslot.time_slot), ',') AS time_array,
	geo.geom
FROM filtered_geo geo
JOIN filtered_route route ON geo.feat_id = route.netw_geo_id
LEFT JOIN {mnrSchema}.mnr_netw2speed_profile netw2speed ON route.netw_geo_id = netw2speed.netw_id
LEFT JOIN {mnrSchema}.mnr_speed_profile spdprofile ON netw2speed.speed_profile_id = spdprofile.speed_profile_id
LEFT JOIN {mnrSchema}.mnr_profile profile ON spdprofile.{weekday}_profile_id = profile.profile_id
LEFT JOIN {mnrSchema}.mnr_profile2speed_per_time_slot profile2speed ON profile.profile_id = profile2speed.profile_id
LEFT JOIN {mnrSchema}.mnr_speed_per_time_slot timeslot ON profile2speed.speed_per_time_slot_id = timeslot.speed_per_time_slot_id
where timeslot.relative_speed is not null
GROUP BY geo.feat_id, geo.geom, netw2speed.validity_direction, spdprofile.free_flow_speed, spdprofile.weekday_speed, spdprofile.weekend_speed, route.display_class, route.form_of_way;
"""
	
	print("\n" + queryDropLine)
	print("\n" + queryMNRLine)

	# Ask Yes/No question
	res=QMessageBox.question(parent,'Question', 'Run query? \n(Otherwise put query on the clipboard)' )

	if res==QMessageBox.Yes:
			# QMessageBox.information(parent,'Your decision',"Run Query")
			b9PyQGIS.fPostGISexec(mnrServer, queryDropLine)
			b9PyQGIS.fPostGISexec(mnrServer, queryMNRLine)

			print("\nLoading postgres layer ... ")
			uri = QgsDataSourceUri()
			uri.setConnection(mnrServer, "5432", "mnr", "mnr_ro", "mnr_ro")
			uri.setDataSource("public", matViewResultTable, "geom", aKeyColumn="feat_type")
			newLayer = iface.addVectorLayer(uri.uri(False), matViewResultTable, "postgres")
			return newLayer

	if res==QMessageBox.No:
			# QMessageBox.information(parent,'Your decision',"Copy to clipboard")
			# Put query on the clipboard
			clipboard = QgsApplication.clipboard()
			clipboard.setText(queryMNRLine)

			message = """\nThe query is on the clipboard.\nPaste and run it from DBeaver (or similar).\nThen import the CSV as a vector layer to QGIS."""
			print(message + "\n======= clipboard! =======")
			qtMsgBox(message)




def fLoadSpeedProfile5minSlotsAggregateExtra(svrURL, strStateSchema, clipLayer, extentCoords):
	mnrServer = svrURL
	mnrSchema = strStateSchema
	print ("server is {}\ntable is {}\n".format(mnrServer, mnrSchema))
	# print("fLoadSpeedProfile5minSlots")

	# # === db MNR matview ===
	matViewPrefix = "b9view" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "speed_profiles_array"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	queryMNRLine = f"""
	CREATE TABLE {matViewResultTable} 
	AS 
	SELECT geo.feat_id, route.display_class,route.speed_average_pos,route.speed_average_neg,
	CASE 
	WHEN netw2speed.validity_direction = 1 THEN 'Both Directions'
	WHEN netw2speed.validity_direction = 2 THEN 'Positive Direction'
	WHEN netw2speed.validity_direction = 3 THEN 'Negative Direction'
	ELSE null
	END AS validity_description,
	netw2speed.validity_direction, spdprofile.free_flow_speed, spdprofile.weekday_speed,spdprofile.weekend_speed,
	ARRAY_AGG(timeslot.time_slot::INTEGER ORDER BY timeslot.time_slot) AS time_slot_array,
	ARRAY_AGG(COALESCE(timeslot.relative_speed::INTEGER, -1) ORDER BY timeslot.time_slot) AS relative_speed_array,
	ARRAY_AGG(COALESCE(((timeslot.time_slot::INTEGER / 5)/60), -1) ORDER BY timeslot.time_slot) AS time_array,
	geo.geom
	FROM {mnrSchema}.mnr_netw_geo_link geo  
	LEFT JOIN {mnrSchema}.mnr_netw_route_link route ON geo.feat_id = route.netw_geo_id 
	LEFT JOIN {mnrSchema}.mnr_netw2speed_profile netw2speed ON route.feat_id=netw2speed.netw_id 
	LEFT JOIN {mnrSchema}.mnr_speed_profile spdprofile ON netw2speed.SPEED_PROFILE_ID = spdprofile.speed_profile_id 
	LEFT JOIN {mnrSchema}.mnr_profile profile on  spdprofile.wednesday_profile_id = profile.profile_id 
	LEFT JOIN {mnrSchema}.mnr_profile2speed_per_time_slot profile2speed on profile.profile_id = profile2speed.profile_id 
	LEFT JOIN {mnrSchema}.mnr_speed_per_time_slot timeslot on profile2speed.speed_per_time_slot_id = timeslot.speed_per_time_slot_id 
	WHERE  
	"ft_road_element" = True 
	AND route.display_class <= 70
	AND ST_Intersects(geo.geom, ST_GeomFromText('{extentCoords}', 4326))
	GROUP BY geo.feat_id, netw2speed.validity_direction, spdprofile.free_flow_speed, spdprofile.weekday_speed,spdprofile.weekend_speed,route.display_class,route.speed_average_pos,route.speed_average_neg;
	"""

	print("\n" + queryDropLine)
	print("\n" + queryMNRLine)

	b9PyQGIS.fPostGISexec(mnrServer, queryDropLine)
	b9PyQGIS.fPostGISexec(mnrServer, queryMNRLine)

	print("\nLoading postgres layer ... ")
	uri = QgsDataSourceUri()
	uri.setConnection(mnrServer, "5432", "mnr", "mnr_ro", "mnr_ro")
	uri.setDataSource("public", matViewResultTable, "geom", aKeyColumn="feat_type")
	newLayer = iface.addVectorLayer(uri.uri(False), matViewResultTable, "postgres")

	# newLayer = fClipExtent(newLayer, clipLayer)

	return newLayer


def fFindColumn():
	print('Combining positive and negative direction arrays...')

	layer = iface.activeLayer()
	layerGeoId = layer.id()
	layerGeoBaseName = layer.name()
	print(layerGeoBaseName)

	# layer = QgsProject.instance().mapLayer(layerGeoId)
	listFields = layer.fields().names()
	print("Fields are: {}".format(listFields))

	# # Assuming you have already loaded your layer
	# layer = iface.activeLayer()

	# Define the pattern to match the weekday_speed_array field
	pattern = re.compile(r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday)_speed_array', re.IGNORECASE)

	# Find the field that matches the pattern
	weekday_speed_field = next((field.name() for field in layer.fields() if pattern.match(field.name())), None)

	if not weekday_speed_field:
		raise ValueError("No field matching the pattern {weekday}_speed_array found.")
	else:
		print(f"Found field: {weekday_speed_field}")

	# Start an edit session
	with edit(layer):
		# Check if 'speed_array' field exists
		field_names = [field.name() for field in layer.fields()]
		print(field_names)

		if 'speed_array' in field_names:
			# Get the index of the 'speed_array' field
			speed_array_idx = layer.fields().indexOf('speed_array')
			# Remove the 'speed_array' field
			layer.dataProvider().deleteAttributes([speed_array_idx])
			layer.updateFields()
		
		# Add a new field 'speed_array' to the attribute table
		layer.dataProvider().addAttributes([QgsField('speed_array', QVariant.String)])
		layer.updateFields()
		
		# Index of the new field
		speed_array_idx = layer.fields().indexOf('speed_array')
		free_flow_speed_idx = layer.fields().indexOf('free_flow_speed')
		weekday_speed_array_idx = layer.fields().indexOf(weekday_speed_field)
		
		# Iterate over features to calculate speed_array values
		featnum = 0
		for feature in layer.getFeatures():
			free_flow_speed = feature[free_flow_speed_idx]
			try:
				# Convert free_flow_speed to float using str conversion
				free_flow_speed = float(str(free_flow_speed))
			except (TypeError, ValueError):
				# Handle NULL or invalid values by assigning 0.0
				free_flow_speed = 0.0
			# print(free_flow_speed)
			featnum += 1

			relative_speed_array = feature[weekday_speed_array_idx]
			relative_speed_array = list(map(int, relative_speed_array.split(',')))


			# Calculate speed_array and convert each element to string
			# speed_array = [str(free_flow_speed * (float(rel_speed) / 1000)) for rel_speed in relative_speed_array]
			speed_array = [round(free_flow_speed * (rel_speed / 1000), 2) for rel_speed in relative_speed_array]
			print(f"{featnum} row, Free flow speed {free_flow_speed} -> Speed {speed_array[0]} promille {relative_speed_array[0]}\n{speed_array}")
	 
			# # Join the speed_array as a single string with comma separators
			# speed_array_str = ','.join(speed_array)
			speed_array_str = ','.join(map(str, speed_array))
			
			# Update the feature's 'speed_array' field
			feature.setAttribute(speed_array_idx, speed_array_str)
			layer.updateFeature(feature)


def fCombinePosNegSingleValue():
	print('Combining positive and negative direction arrays...')

	original_layer = iface.activeLayer()
	duplicated_layer_name = f"{original_layer.name()}_01"
	layer = fDuplicateLayer(original_layer, duplicated_layer_name)

	layerGeoBaseName = layer.name()
	print(layerGeoBaseName)

	from collections import defaultdict

	def calculate_values_by_feat_id(layer):
		# Dictionary to store sum and count of values for each feat_id
		feat_id_values = defaultdict(lambda: {'sum': 0, 'count': 0})

		# Iterate over features to calculate sum and count for each feat_id
		for feature in layer.getFeatures():
			feat_id = str(feature['feat_id'])  # Convert feat_id to string
			validity_direction = feature['validity_direction']
			value = feature['value']

			if validity_direction in (2, 3):
				feat_id_values[feat_id]['sum'] += value
				feat_id_values[feat_id]['count'] += 1

		# Calculate average for each feat_id
		feat_id_averages = {feat_id: values['sum'] / values['count'] for feat_id, values in feat_id_values.items() if values['count'] > 0}
		print("Calculated averages:", feat_id_averages)

		# Start an edit session
		with edit(layer):
			# Add a new field 'avg_value' to the attribute table if it doesn't exist
			if 'avg_value' not in [field.name() for field in layer.fields()]:
				layer.dataProvider().addAttributes([QgsField('avg_value', QVariant.Double)])
				layer.updateFields()

			avg_value_idx = layer.fields().indexOf('avg_value')

			# Update features with the calculated averages
			for feature in layer.getFeatures():
				feat_id = feature['feat_id']
				if feat_id in feat_id_averages:
					feature.setAttribute(avg_value_idx, feat_id_averages[feat_id])
					layer.updateFeature(feature)

	# Assuming 'layer' is your loaded QGIS layer
	layer = iface.activeLayer()
	calculate_values_by_feat_id(layer)


# Function to convert a GeoDataFrame to a QGIS vector layer
def gdf_to_qgs_layer(gdf, layer_name='New Geopandas Layer'):
		# Determine the geometry type from the GeoDataFrame
		geom_type = gdf.geom_type.iloc[0].lower()
		qgs_geom_type = "Point" if "point" in geom_type else "LineString" if "line" in geom_type else "Polygon"
		
		# Create an empty memory layer
		layer = QgsVectorLayer(f"{qgs_geom_type}?crs={gdf.crs.to_wkt()}", layer_name, "memory")
		provider = layer.dataProvider()
		
		# Add fields to the layer based on GeoDataFrame columns
		fields = []
		for col in gdf.columns:
				if col != 'geometry':
						dtype = QVariant.String if gdf[col].dtype == object else QVariant.Double
						fields.append(QgsField(col, dtype))
		provider.addAttributes(fields)
		layer.updateFields()
		
		# Add features to the layer
		for _, row in gdf.iterrows():
				feature = QgsFeature()
				attrs = [row[col] for col in gdf.columns if col != 'geometry']
				feature.setAttributes(attrs)
				feature.setGeometry(QgsGeometry.fromWkt(row['geometry'].wkt))
				provider.addFeature(feature)


		layer.updateExtents()
		return layer


def fKeepUniqueByIDField(layer):
	# Load the existing layer by name
	layer_name = layer.name()  # Replace with your layer's name
	# layer = QgsProject.instance().mapLayersByName(layer_name)[0]

	# Collect the data into a list of features
	features = [feature for feature in layer.getFeatures()]

	# Convert the features to GeoDataFrame
	# This assumes the layer's CRS is well-known and compatible with GeoPandas
	gdf = gpd.GeoDataFrame.from_features(features)

	# Set the CRS to match the layer’s CRS
	gdf.set_crs(layer.crs().authid(), inplace=True)

	# selected_field = fSelectLayerField()
	selected_field = 'feat_id'

	# Assuming 'gdf' is your GeoDataFrame and 'id' is the column name
	gdf_unique = gdf.drop_duplicates(subset=selected_field, keep='first')

	# Convert the GeoDataFrame 'gdf_unique' to a new QGIS layer
	new_layer = gdf_to_qgs_layer(gdf_unique, layer_name=layer_name + '_Distinct')
	# Add the new layer to the QGIS project
	QgsProject.instance().addMapLayer(new_layer)

def fCombinePosNeg():
	print('Combining positive and negative direction arrays...')

	original_layer = iface.activeLayer()
	duplicated_layer_name = f"{original_layer.name()}_01"
	layer = fDuplicateLayerinMemory(original_layer, duplicated_layer_name)

	layerGeoBaseName = layer.name()
	print(layerGeoBaseName)

	listFields = layer.fields().names()
	print("Fields are: {}".format(listFields))

	# Define the pattern to match the weekday_speed_array field
	pattern = re.compile(r'(monday|tuesday|wednesday|thursday|friday|saturday|sunday)_speed_array', re.IGNORECASE)
	# Find the field that matches the pattern
	weekday_speed_field = next((field.name() for field in layer.fields() if pattern.match(field.name())), None)
	if not weekday_speed_field:
		raise ValueError("No field matching the pattern {weekday}_speed_array found.")
	else:
		print(f"Found field: {weekday_speed_field}")
		match = pattern.match(weekday_speed_field)
		if match:
				day_of_week = match.group(1)
				print(f"Day of the week found: {day_of_week}")

	# # Define weekday and weekend speeds (example values)
	# weekday_speed = 50
	# weekend_speed = 60
	
	# # Determine the speed to use based on the day of the week
	# speed_to_use = weekend_speed if day_of_week in ['saturday', 'sunday'] else weekday_speed

	from collections import defaultdict

	def sum_array_fields_by_feat_id(layer):
		# Dictionary to store sum and count of values for each feat_id
		list_288_zeros = [0] * 288
		feat_id_values = defaultdict(lambda: {'sum_list': list_288_zeros, 'count': 0, 'base_speed': 0})

		# Iterate over features to calculate sum and count for each feat_id
		for feature in layer.getFeatures():
			feat_id = str(feature['feat_id'])  # Convert feat_id to string
			validity_direction = feature['validity_direction']
			weekday_speed = feature['weekday_speed']
			weekend_speed = feature['weekend_speed']
			value_string = feature[weekday_speed_field]
			value_list = [int(x) for x in value_string.split(',')]

			if validity_direction in (2, 3):
				# Sum the lists positionally
				summed_list = [a + b for a, b in zip(feat_id_values[feat_id]['sum_list'], value_list)]
				feat_id_values[feat_id]['sum_list'] = summed_list
				feat_id_values[feat_id]['count'] += 1
				if day_of_week in ['saturday', 'sunday']:
					feat_id_values[feat_id]['base_speed'] += weekend_speed
				else:
					feat_id_values[feat_id]['base_speed'] += weekday_speed
			else:
				feat_id_values[feat_id]['sum_list'] = value_list
				feat_id_values[feat_id]['count'] = 1
				if day_of_week in ['saturday', 'sunday']:
					feat_id_values[feat_id]['base_speed'] += weekend_speed
				else:
					feat_id_values[feat_id]['base_speed'] += weekday_speed

		# # Calculate average promille
		# feat_id_combined = {
		# 	feat_id: ','.join(
		# 		map(str, 
		# 			[round(element / values['count']) for element in values['sum_list']] 
		# 			if values['count'] > 1 
		# 			else values['sum_list']
		# 		)
		# 	)
		# 	for feat_id, values in feat_id_values.items()
		# }


		# Calculate the speed in kph for each element in the 'sum_list' and convert to string
		feat_id_combined = {
				feat_id: ','.join(
						map(str,
								[round((element / values['count']) * ((values['base_speed'] / values['count']) / 1000)) for element in values['sum_list']]
								if values['count'] > 1
								# else values['sum_list']
								else [round((element) * ((values['base_speed']) / 1000)) for element in values['sum_list']]
						)
				)
				for feat_id, values in feat_id_values.items()
		}

		# Start an edit session
		with edit(layer):
			# Add a new field 'sum_speed_array' to the attribute table if it doesn't exist
			if 'combined_speed' not in [field.name() for field in layer.fields()]:
				layer.dataProvider().addAttributes([QgsField('combined_speed', QVariant.String)])
				layer.updateFields()

			avg_value_idx = layer.fields().indexOf('combined_speed')

			# Update features with the calculated averages
			for feature in layer.getFeatures():
				feat_id = str(feature['feat_id'])
				# print(feat_id_combined['values'])
				if feat_id in feat_id_combined:
					feature.setAttribute(avg_value_idx, feat_id_combined[feat_id])
					layer.updateFeature(feature)

	# Assuming 'layer' is your loaded QGIS layer
	sum_array_fields_by_feat_id(layer)
	# fKeepUniqueByIDField(layer) # this can be done manually
