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
	
	newLayer = fLoadPOIs_EV(mnrServer,mnrSchema,extentCoords)
	# fSymbol(newLayer)

def fLoadPOIs_EV(mnrServer,mnrSchema,extentCoords):

	# # === db MNR matview ===
	matViewPrefix = "b9" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "ev"
	extentStr = "'" + extentCoords + "'"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	poiFields = b9PyQGIS.fFieldsFromString("poi.", "feat_id,feat_type,feat_sub_type,service_group,name,geom") 	# feat_id,feat_type,feat_sub_type,service_group,gav,name,lang_code,telephone_num,fax_num,email,internet,poi_address_id,in_car_importance,geom
	
	metaFields = b9PyQGIS.fFieldsFromString("meta.", "code_description as POI_type") # enum_value_id,enum_id,code,code_description

	metaFieldsType = b9PyQGIS.fFieldsFromString("metaType.", "code_description as POI_type") # enum_value_id,enum_id,code,code_description

	metaFieldsSubType = b9PyQGIS.fFieldsFromString("metaSubType.", "code_description as POI_subtype") # enum_value_id,enum_id,code,code_description

	metaCodeDescriptSelect = "(\'Electric Vehicle Station\')"

	metaCodeDescriptType = 'Feature Type POI'
	metaCodeDescriptSubType = 'Feature Sub Type POI'

	poi2attrFields = b9PyQGIS.fFieldsFromString("poi2attr.", "poi_id,attribute_id")
	
	attrFields = b9PyQGIS.fFieldsFromString("attr.", "attribute_id,parent_attribute_id,attribute_type,value_type,enum_id,nameset_id,value_varchar,value_integer,value_boolean,value_text") # attribute_id,parent_attribute_id,attribute_type,value_type,enum_id,nameset_id,value_varchar,value_integer,value_boolean,value_text

	# queryMNRLine =  "CREATE TABLE " + matViewResultTable + " as" +\
	# " SELECT " + poiFields + "," + attrFields +\
	# 	" FROM (" +\
	# 	" SELECT * FROM " + mnrSchema + ".mnr_poi poi " +\
	# 	" WHERE poi.feat_type = 7309 AND" +\
	# 	" ST_Intersects(poi.geom,ST_GeomFromText(" + extentStr + ",4326))" +\
	# 	" ) poi" +\
	# 	" LEFT JOIN " + mnrSchema + ".mnr_poi2attribute  poi2attr" +\
	# 	" ON poi.feat_id = poi2attr.poi_id" +\
	# 	" INNER JOIN " + mnrSchema + ".mnr_attribute  attr" +\
	# 	" ON poi2attr.attribute_id = attr.attribute_id" +\
	# 	" ;"

	# SELECT poi.feat_id,poi.feat_type,poi.feat_sub_type,poi.service_group,poi.name,poi.geom,attr.attribute_type 
	# FROM (
	# SELECT * FROM 
	#  _2022_09_000_eur_deu_deu.mnr_poi
	#  WHERE _2022_09_000_eur_deu_deu.mnr_poi.feat_type = 7309
	#  AND ST_Intersects(_2022_09_000_eur_deu_deu.mnr_poi.geom,ST_GeomFromText('Polygon ((13.37601585 52.49709663, 13.41094353 52.49709663, 13.41094353 52.51606549, 13.37601585 52.51606549, 13.37601585 52.49709663))',4326))
	#  ) poi
	# LEFT JOIN _2022_09_000_eur_deu_deu.mnr_poi2attribute  poi2attr ON poi.feat_id = poi2attr.poi_id 
	# LEFT JOIN _2022_09_000_eur_deu_deu.mnr_attribute  attr 
	# 	ON poi2attr.attribute_id = attr.attribute_id 
	# 	order by attr.attribute_type 
	# 	AND attr.attribute_type = 'W8'

	queryMNRLine =  "CREATE TABLE " + matViewResultTable + " as" +\
	" SELECT " + poiFields + "," + metaFieldsType + "," + metaFieldsSubType +\
		" FROM " + mnrSchema + ".mnr_poi poi " +\
		" JOIN (" +\
		"   SELECT * from " + mnrSchema + ".mnr_meta_enum  enu" +\
		"   JOIN " + mnrSchema + ".mnr_meta_enum_value  val" +\
		"   ON enu.enum_id = val.enum_id" +\
		"   WHERE enu.enum_description=\'" + metaCodeDescriptType + "\'" +\
		"   ORDER by val.code_description" +\
		"   ) metaType" +\
		" ON poi.feat_type::varchar = metaType.code" +\
		" LEFT JOIN (" +\
		"   SELECT * from " + mnrSchema + ".mnr_meta_enum  enu" +\
		"   JOIN " + mnrSchema + ".mnr_meta_enum_value  val" +\
		"   ON enu.enum_id = val.enum_id" +\
		"   WHERE enu.enum_description=\'" + metaCodeDescriptSubType + "\'" +\
		"   ORDER by val.code_description" +\
		"   ) metaSubType" +\
		" ON poi.feat_sub_type::varchar = metaSubType.code" +\
		" WHERE metaType.code_description in " + metaCodeDescriptSelect + " AND" +\
		" ST_Intersects(poi.geom,ST_GeomFromText(" + extentStr + ",4326)) ;"


	print("\n" + queryDropLine)
	print("\n" + extentStr)
	print("\n" + queryMNRLine)

	b9PyQGIS.fPostGISexec(mnrServer, queryDropLine)
	b9PyQGIS.fPostGISexec(mnrServer, queryMNRLine)

	print("\nLoading postgres layer ... ")
	uri = QgsDataSourceUri()
	uri.setConnection(mnrServer, "5432", "mnr", "mnr_ro", "mnr_ro")
	uri.setDataSource("public", matViewResultTable, "geom", aKeyColumn="feat_type")
	vlayer = iface.addVectorLayer(uri.uri(False), matViewResultTable, "postgres")

