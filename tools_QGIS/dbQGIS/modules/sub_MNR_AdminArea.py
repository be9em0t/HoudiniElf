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
	
	newLayer = fLoadAABrute(mnrServer,mnrSchema,extentCoords)
	newLayer = fClipExtent(newLayer, clipLayer)
	# newLayer2 = fLoadCityCenters(mnrServer,mnrSchema,extentCoords)
	fSymbol(newLayer)

def fLoadAdminAreasBrute(svrURL, strStateSchema, clipLayer, extentCoords):
	mnrServer = svrURL
	mnrSchema = strStateSchema
	print ("server is {}\ntable is {}\n".format(mnrServer, mnrSchema))
	
	newLayer = fLoadAABrute(mnrServer,mnrSchema,extentCoords)
	newLayer = fClipExtent(newLayer, clipLayer)
	# newLayer2 = fLoadCityCenters(mnrServer,mnrSchema,extentCoords)
	fSymbol(newLayer)

def fLoadAdminAreasFast(svrURL, strStateSchema, clipLayer, extentCoords):
	mnrServer = svrURL
	mnrSchema = strStateSchema
	print ("server is {}\ntable is {}\n".format(mnrServer, mnrSchema))
	
	newLayer = fLoadAAFast(mnrServer,mnrSchema,extentCoords)
	newLayer = fClipExtent(newLayer, clipLayer)
	# newLayer2 = fLoadCityCenters(mnrServer,mnrSchema,extentCoords)
	fSymbol(newLayer)

def fLoadAdminAreasPopulation(svrURL, strStateSchema, clipLayer, extentCoords):
	mnrServer = svrURL
	mnrSchema = strStateSchema
	print ("server is {}\ntable is {}\n".format(mnrServer, mnrSchema))
	
	newLayer = fLoadAAPopulation(mnrServer,mnrSchema,extentCoords)
	newLayer = fClipExtent(newLayer, clipLayer)
	# newLayer2 = fLoadCityCenters(mnrServer,mnrSchema,extentCoords)
	fSymbol(newLayer)

# # =======

def fLoadAAFast(mnrServer,mnrSchema,extentCoords):
	# # === db MNR matview ===
	matViewPrefix = "b9view" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "adm"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	queryMNRLine = f"""
CREATE TABLE {matViewResultTable} 
AS 
WITH filtered_geo AS (
	SELECT feat_id, feat_type, standard_lang, geom
	FROM {mnrSchema}.mnr_admin_area 
	WHERE  
	feat_type != 1111 AND
	ST_Intersects(geom, ST_GeomFromText('{extentCoords}', 4326))
),
filtered_mnr_name AS (
	SELECT name_id, original_name_id, "name", iso_script, iso_lang_code, nc_body, nc_prefix, nc_suffix 
	FROM {mnrSchema}.mnr_name
)
SELECT distinct geo.feat_id, geo.feat_type, geo.geom, name.name, name.iso_script, name.iso_lang_code, name.nc_body, name.nc_prefix, name.nc_suffix
,
	attr1.attribute_type,
	enumval2.code_description,
	CASE 
		WHEN attr1.value_type = 3 THEN CAST(attr1.VALUE_INTEGER as text)
		WHEN attr1.value_type = 5 THEN CAST(attr1.VALUE_BOOLEAN AS text)
		ELSE NULL
	END AS value,
	enumdescript.code_description as aa_description
FROM filtered_geo geo
LEFT JOIN {mnrSchema}.mnr_admin_area2nameset aa2ns ON geo.feat_id = aa2ns.admin_area_id 
LEFT JOIN 
	{mnrSchema}.mnr_nameset ns ON aa2ns.nameset_id = ns.nameset_id 
LEFT JOIN 
	{mnrSchema}.mnr_nameset2name ns2n ON ns.nameset_id = ns2n.nameset_id 
LEFT JOIN 
	filtered_mnr_name name ON ns2n.name_id = name.name_id 
LEFT JOIN 
	{mnrSchema}.mnr_admin_area2attribute aa2a ON geo.feat_id = aa2a.admin_area_id 
LEFT JOIN 
	{mnrSchema}.mnr_attribute attr1 ON aa2a.attribute_id = attr1.attribute_id 
LEFT JOIN 
	{mnrSchema}.mnr_meta_enum_value enumval ON geo.feat_type::varchar = enumval.code 
LEFT JOIN 
	{mnrSchema}.mnr_meta_enum enum ON enum.enum_id = enumval.enum_id 
LEFT JOIN 
	{mnrSchema}.mnr_meta_enum_value enumval2 ON attr1.attribute_type = enumval2.code 
LEFT JOIN 
	{mnrSchema}.mnr_meta_enum_value enumdescript ON CAST(geo.feat_type AS TEXT) = enumdescript.code
WHERE
	(name.iso_lang_code=geo.standard_lang or name.iso_lang_code='ENG') and
	(enumval2.code_description = 'Population Figure' OR enumval2.code_description IS null)
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
	return newLayer

def fLoadAAPopulation(mnrServer,mnrSchema,extentCoords):
	# # === db MNR matview ===
	matViewPrefix = "b9view" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "admin_population"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	queryMNRLine = f"""
CREATE TABLE {matViewResultTable} 
AS 
WITH filtered_geo AS (
	SELECT feat_id, feat_type, standard_lang, geom
	FROM {mnrSchema}.mnr_admin_area 
	WHERE  
	feat_type != 1111 AND
	ST_Intersects(geom, ST_GeomFromText('{extentCoords}', 4326))
),
filtered_mnr_name AS (
	SELECT name_id, original_name_id, "name", iso_script, iso_lang_code, nc_body, nc_prefix, nc_suffix 
	FROM {mnrSchema}.mnr_name
)
SELECT distinct geo.feat_id, geo.feat_type, geo.geom, name.name, name.iso_script, name.iso_lang_code, name.nc_body, name.nc_prefix, name.nc_suffix
,
	attr1.attribute_type,
	enumval2.code_description,
	attr1.VALUE_INTEGER as population_size,
	enumdescript.code_description as aa_description
FROM filtered_geo geo
LEFT JOIN {mnrSchema}.mnr_admin_area2nameset aa2ns ON geo.feat_id = aa2ns.admin_area_id 
LEFT JOIN 
	{mnrSchema}.mnr_nameset ns ON aa2ns.nameset_id = ns.nameset_id 
LEFT JOIN 
	{mnrSchema}.mnr_nameset2name ns2n ON ns.nameset_id = ns2n.nameset_id 
LEFT JOIN 
	filtered_mnr_name name ON ns2n.name_id = name.name_id 
LEFT JOIN 
	{mnrSchema}.mnr_admin_area2attribute aa2a ON geo.feat_id = aa2a.admin_area_id 
LEFT JOIN 
	{mnrSchema}.mnr_attribute attr1 ON aa2a.attribute_id = attr1.attribute_id 
LEFT JOIN 
	{mnrSchema}.mnr_meta_enum_value enumval ON geo.feat_type::varchar = enumval.code 
LEFT JOIN 
	{mnrSchema}.mnr_meta_enum enum ON enum.enum_id = enumval.enum_id 
LEFT JOIN 
	{mnrSchema}.mnr_meta_enum_value enumval2 ON attr1.attribute_type = enumval2.code 
LEFT JOIN 
	{mnrSchema}.mnr_meta_enum_value enumdescript ON CAST(geo.feat_type AS TEXT) = enumdescript.code
WHERE
	(name.iso_lang_code=geo.standard_lang or name.iso_lang_code='ENG') and
	(enumval2.code_description = 'Population Figure' OR enumval2.code_description IS null)
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
	return newLayer

def fLoadAABrute(mnrServer,mnrSchema,extentCoords):
	# # === db MNR matview ===
	matViewPrefix = "b9view" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "adm"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	queryMNRLine = f"""
CREATE TABLE {matViewResultTable} 
AS 
SELECT DISTINCT
		adm.feat_id,
		adm.feat_type,
		enumval.code_description AS area_description,
		name.iso_lang_code,
		name."name",
		attr1.attribute_type,
		enumval2.code_description,
		CASE 
				WHEN attr1.value_type = 3 THEN CAST(attr1.VALUE_INTEGER AS text)
				WHEN attr1.value_type = 5 THEN CAST(attr1.VALUE_BOOLEAN AS text)
				ELSE NULL
		END AS value,
		adm.geom
FROM 
		{mnrSchema}.mnr_admin_area adm  
LEFT JOIN 
		{mnrSchema}.mnr_admin_area2nameset aa2ns ON adm.feat_id = aa2ns.admin_area_id 
LEFT JOIN 
		{mnrSchema}.mnr_nameset ns ON aa2ns.nameset_id = ns.nameset_id 
LEFT JOIN 
		{mnrSchema}.mnr_nameset2name ns2n ON ns.nameset_id = ns2n.nameset_id 
LEFT JOIN 
		{mnrSchema}.mnr_name name ON ns2n.name_id = name.name_id 
LEFT JOIN 
		{mnrSchema}.mnr_admin_area2attribute aa2a ON adm.feat_id = aa2a.admin_area_id 
LEFT JOIN 
		{mnrSchema}.mnr_attribute attr1 ON aa2a.attribute_id = attr1.attribute_id 
LEFT JOIN 
		{mnrSchema}.mnr_meta_enum_value enumval ON adm.feat_type::varchar = enumval.code 
LEFT JOIN 
		{mnrSchema}.mnr_meta_enum enum ON enum.enum_id = enumval.enum_id 
LEFT JOIN 
		{mnrSchema}.mnr_meta_enum_value enumval2 ON attr1.attribute_type = enumval2.code 
WHERE 
		adm.feat_type != 1111
		AND (attr1.attribute_type IS NOT NULL OR name.lang_code = 'ENG')
		AND (attr1.value_type IN (2, 3, 4, 5, 15) OR attr1.value_type IS NULL)
		AND ST_Intersects(adm.geom, ST_GeomFromText('{extentCoords}', 4326));
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
	return newLayer


def fLoadAdminAreasBasic(mnrServer,mnrSchema,extentCoords):

	# # === db MNR matview ===
	matViewPrefix = "b9view" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "adm"
	extentStr = "'" + extentCoords + "'"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	admFields = b9PyQGIS.fFieldsFromString("adm.", "feat_type,name,citycenter_id,geom") 	# feat_id,feat_type,name,lang_code,feat_area,feat_perim,country_id,country_code_char3,a1_admin_id,a1_admin_code,a2_admin_id,a2_admin_code,a3_admin_id,a3_admin_code,a4_admin_id,a4_admin_code,a5_admin_id,a5_admin_code,a6_admin_id,a6_admin_code,a7_admin_id,a7_admin_code,a8_admin_id,a8_admin_code,a9_admin_id,a9_admin_code,artificial,standard_lang,citycenter_id,geom

	enumvalFields = b9PyQGIS.fFieldsFromString("enumval.", "code_description") # enum_value_id,enum_id,code,code_description

	enumFields = b9PyQGIS.fFieldsFromString("enum.", "code_description") # enum_id,enum_description

	queryMNRLine =  "CREATE TABLE " + matViewResultTable + \
		" as SELECT " + admFields + "," + enumvalFields + \
		" FROM " + mnrSchema + ".mnr_admin_area adm " + \
		" JOIN " + mnrSchema + ".mnr_meta_enum_value enumval ON adm.feat_type::varchar = enumval.code" + \
		" JOIN " + mnrSchema + ".mnr_meta_enum enum ON enum.enum_id = enumval.enum_id" + \
		" WHERE enum.enum_description='Feature Type Admin Area' AND" + \
		" ST_Intersects(adm.geom,ST_GeomFromText(" + extentStr + ",4326)) ;"
	
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

