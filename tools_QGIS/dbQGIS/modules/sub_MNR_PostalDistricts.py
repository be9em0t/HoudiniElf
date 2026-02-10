# Load Table based on an Extent layer 

from qgis.core import *
from qgis.core import QgsDataSourceUri, QgsVectorLayer, QgsProject
from qgis.utils import *
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import *
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


def fClipExtent(layer,extentLayer):
	print ("Clip by Extent...")
	result = b9PyQGIS.fExtractByExtent(layer, extentLayer)
	newLayer = QgsProject.instance().addMapLayer(result['OUTPUT'])
	newLayer.setName(layer.name() + '_Clip')
	# layer.setName(layer.name() + '_Org')
	QgsProject.instance().removeMapLayer(layer)
	return newLayer


def fLoadCensusAreas(svrURL, strStateSchema, clipLayer, extentCoords):
	mnrServer = svrURL
	mnrSchema = strStateSchema
	print ("server is {}\ntable is {}\n".format(mnrServer, mnrSchema))

	# parent=iface.mainWindow()

	# # === db MNR matview ===
	matViewPrefix = "b9view" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "_census_areas"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	queryMNRLine = f"""
	CREATE TABLE {matViewResultTable} 
	AS 
	WITH filtered_geo AS (
		SELECT feat_id, feat_type, country, name, lang_code, feat_area, census_code, urban, geom
		FROM {mnrSchema}.mnr_census_district
		WHERE  
		ST_Intersects(geom, ST_GeomFromText('{extentCoords}', 4326))
	)
	SELECT distinct geo.feat_id, geo.feat_type, geo.country, geo.name, geo.lang_code, geo.feat_area, geo.census_code, geo.urban, geo.geom,
	enumdescript.code_description
	FROM filtered_geo geo
	LEFT JOIN {mnrSchema}.mnr_meta_enum_value enumdescript ON CAST(geo.feat_type AS TEXT) = enumdescript.code
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
	newLayer = fClipExtent(newLayer, clipLayer)

	return newLayer


def fLoadPostalDistrictNames(svrURL, strStateSchema, clipLayer, extentCoords):
	mnrServer = svrURL
	mnrSchema = strStateSchema
	print ("server is {}\ntable is {}\n".format(mnrServer, mnrSchema))
	# print("Load Postal Districts")

	# parent=iface.mainWindow()

	# # === db MNR matview ===
	matViewPrefix = "b9view" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "_postal_district_names"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	queryMNRLine = f"""
CREATE TABLE {matViewResultTable} 
AS 
WITH filtered_geo AS (
	SELECT feat_id, feat_type, country, postal_code, feat_area, postal_point_id, geom
	FROM {mnrSchema}.mnr_postal_district
	WHERE  
	ST_Intersects(geom, ST_GeomFromText('{extentCoords}', 4326))
)
SELECT distinct geo.feat_id, geo.feat_type, geo.country, geo.postal_code, geo.feat_area, geo.geom,
	ARRAY_TO_STRING(ARRAY_AGG(COALESCE(citycenter.name, NULL)), ',') AS name
FROM filtered_geo geo
LEFT JOIN {mnrSchema}.mnr_postal_point postalpoint ON geo.postal_point_id = postalpoint.feat_id
LEFT JOIN {mnrSchema}.mnr_citycenter citycenter ON postalpoint.feat_id = citycenter.postal_point_id
group by geo.feat_id, geo.feat_type, geo.country, geo.postal_code, geo.feat_area, geo.geom
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
	newLayer = fClipExtent(newLayer, clipLayer)

	return newLayer


def fLoadPostalDistricts(svrURL, strStateSchema, clipLayer, extentCoords):
	mnrServer = svrURL
	mnrSchema = strStateSchema
	print ("server is {}\ntable is {}\n".format(mnrServer, mnrSchema))
	# print("Load Postal Districts")

	# parent=iface.mainWindow()

	# # === db MNR matview ===
	matViewPrefix = "b9view" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "_postal_districts"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	queryMNRLine = f"""
CREATE TABLE {matViewResultTable} 
AS 
WITH filtered_geo AS (
	SELECT feat_id, feat_type, country, postal_code, feat_area, postal_point_id, geom
	FROM {mnrSchema}.mnr_postal_district
	WHERE  
	ST_Intersects(geom, ST_GeomFromText('{extentCoords}', 4326))
)
SELECT distinct geo.feat_id, geo.feat_type, geo.country, geo.postal_code, geo.feat_area, geo.geom
FROM filtered_geo geo
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
	newLayer = fClipExtent(newLayer, clipLayer)

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
	SELECT netw_geo_id, display_class
	FROM {mnrSchema}.mnr_netw_route_link
	WHERE display_class <= 70
)
SELECT geo.feat_id, route.display_class,
	CASE 
		WHEN netw2speed.validity_direction = 1 THEN 'Both Directions'
		WHEN netw2speed.validity_direction = 2 THEN 'Positive Direction'
		WHEN netw2speed.validity_direction = 3 THEN 'Negative Direction'
		ELSE null
	END AS validity_description,
	netw2speed.validity_direction, spdprofile.free_flow_speed, spdprofile.weekday_speed, spdprofile.weekend_speed,
	ARRAY_TO_STRING(ARRAY_AGG(timeslot.time_slot::INTEGER ORDER BY timeslot.time_slot), ',') AS time_slot_array,
	ARRAY_TO_STRING(ARRAY_AGG(COALESCE(timeslot.relative_speed::INTEGER, -1) ORDER BY timeslot.time_slot), ',') AS wednesday_speed_array,
	ARRAY_TO_STRING(ARRAY_AGG(COALESCE(((timeslot.time_slot::INTEGER / 5) / 60), -1) ORDER BY timeslot.time_slot), ',') AS time_array,
	geo.geom
FROM filtered_geo geo
LEFT JOIN filtered_route route ON geo.feat_id = route.netw_geo_id
LEFT JOIN {mnrSchema}.mnr_netw2speed_profile netw2speed ON route.netw_geo_id = netw2speed.netw_id
LEFT JOIN {mnrSchema}.mnr_speed_profile spdprofile ON netw2speed.speed_profile_id = spdprofile.speed_profile_id
LEFT JOIN {mnrSchema}.mnr_profile profile ON spdprofile.{weekday}_profile_id = profile.profile_id
LEFT JOIN {mnrSchema}.mnr_profile2speed_per_time_slot profile2speed ON profile.profile_id = profile2speed.profile_id
LEFT JOIN {mnrSchema}.mnr_speed_per_time_slot timeslot ON profile2speed.speed_per_time_slot_id = timeslot.speed_per_time_slot_id
GROUP BY geo.feat_id, geo.geom, netw2speed.validity_direction, spdprofile.free_flow_speed, spdprofile.weekday_speed, spdprofile.weekend_speed, route.display_class;
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


def fCombinePosNeg():
	print('Combining positive and negative direction arrays...')

	layer = iface.activeLayer()
	layerGeoId = layer.id()
	layerGeoBaseName = layer.name()
	print(layerGeoBaseName)

	# Create a new memory layer with the same geometry type as the source layer
	geometry_type = layer.geometryType()
	crs = layer.crs().authid()
	new_layer = QgsVectorLayer(f"{geometry_type}?crs={crs}", "New Layer", "memory")
	new_layer_data_provider = new_layer.dataProvider()

	# Copy fields from the source layer to the new layer
	new_layer_data_provider.addAttributes(layer.fields())
	new_layer.updateFields()

	# Add features with the calculated averages to the new layer
	for feature in layer.getFeatures():
		new_feature = QgsFeature()
		new_feature.setGeometry(feature.geometry())
		new_feature.setAttributes(feature.attributes())
		feat_id = str(feature['feat_id'])  # Convert feat_id to string
		# if feat_id in feat_id_averages:
		# 	# new_feature.setAttribute(avg_value_idx, feat_id_averages[feat_id])
		# 	pass
		# else:
		# 	print(f"feat_id {feat_id} not found in feat_id_averages")
		new_layer_data_provider.addFeature(new_feature)


	# Add the new layer to the project
	QgsProject.instance().addMapLayer(new_layer)

def OFF():
	# layer = QgsProject.instance().mapLayer(layerGeoId)
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

	# # Start an edit session
	# with edit(layer):
	# 	# Check if 'speed_array' field exists
	# 	field_names = [field.name() for field in layer.fields()]
	# 	print(field_names)

	# 	if 'speed_array' in field_names:
	# 		# Get the index of the 'speed_array' field
	# 		speed_array_idx = layer.fields().indexOf('speed_array')
	# 		# Remove the 'speed_array' field
	# 		layer.dataProvider().deleteAttributes([speed_array_idx])
	# 		layer.updateFields()
		
	# 	# Add a new field 'speed_array' to the attribute table
	# 	layer.dataProvider().addAttributes([QgsField('speed_array', QVariant.String)])
	# 	layer.updateFields()
		
	# 	# Index of the new field
	# 	speed_array_idx = layer.fields().indexOf('speed_array')
	# 	free_flow_speed_idx = layer.fields().indexOf('free_flow_speed')
	# 	weekday_speed_array_idx = layer.fields().indexOf(weekday_speed_field)
		
	# 	# Iterate over features to calculate speed_array values
	# 	featnum = 0
	# 	for feature in layer.getFeatures():
	# 		free_flow_speed = feature[free_flow_speed_idx]
	# 		try:
	# 			# Convert free_flow_speed to float using str conversion
	# 			free_flow_speed = float(str(free_flow_speed))
	# 		except (TypeError, ValueError):
	# 			# Handle NULL or invalid values by assigning 0.0
	# 			free_flow_speed = 0.0
	# 		# print(free_flow_speed)
	# 		featnum += 1

	# 		relative_speed_array = feature[weekday_speed_array_idx]
	# 		relative_speed_array = list(map(int, relative_speed_array.split(',')))


	# 		# Calculate speed_array and convert each element to string
	# 		# speed_array = [str(free_flow_speed * (float(rel_speed) / 1000)) for rel_speed in relative_speed_array]
	# 		speed_array = [round(free_flow_speed * (rel_speed / 1000), 2) for rel_speed in relative_speed_array]
	# 		print(f"{featnum} row, Free flow speed {free_flow_speed} -> Speed {speed_array[0]} promille {relative_speed_array[0]}\n{speed_array}")
	 
	# 		# # Join the speed_array as a single string with comma separators
	# 		# speed_array_str = ','.join(speed_array)
	# 		speed_array_str = ','.join(map(str, speed_array))
			
	# 		# Update the feature's 'speed_array' field
	# 		feature.setAttribute(speed_array_idx, speed_array_str)
	# 		layer.updateFeature(feature)
