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
	# matViewPrefix = "b9" + mnrSchema[0:8] + "_"
	# matViewPrefix = "b9" + mnrSchema + "_"
	# matViewResultTable = matViewPrefix + "ev"
	matViewResultTable = "b9_ev" + mnrSchema
	extentStr = "'" + extentCoords + "'"

	# queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"
	queryDropLine = """DROP TABLE IF EXISTS {} CASCADE;""".format(matViewResultTable)

	poiFields = b9PyQGIS.fFieldsFromString("poi.", "feat_id,feat_type,feat_sub_type,service_group,name,geom") 	# feat_id,feat_type,feat_sub_type,service_group,gav,name,lang_code,telephone_num,fax_num,email,internet,poi_address_id,in_car_importance,geom
	
	metaFields = b9PyQGIS.fFieldsFromString("meta.", "code_description as POI_type") # enum_value_id,enum_id,code,code_description

	metaFieldsType = b9PyQGIS.fFieldsFromString("metaType.", "code_description as POI_type") # enum_value_id,enum_id,code,code_description

	metaFieldsSubType = b9PyQGIS.fFieldsFromString("metaSubType.", "code_description as POI_subtype") # enum_value_id,enum_id,code,code_description

	metaCodeDescriptSelect = "(\'Electric Vehicle Station\')"

	metaCodeDescriptType = 'Feature Type POI'
	metaCodeDescriptSubType = 'Feature Sub Type POI'

	poi2attrFields = b9PyQGIS.fFieldsFromString("poi2attr.", "poi_id,attribute_id")
	
	attrFields = b9PyQGIS.fFieldsFromString("attr.", "attribute_id,parent_attribute_id,attribute_type,value_type,enum_id,nameset_id,value_varchar,value_integer,value_boolean,value_text") # attribute_id,parent_attribute_id,attribute_type,value_type,enum_id,nameset_id,value_varchar,value_integer,value_boolean,value_text


	queryMNRLine =  """
CREATE TABLE {table} as (
SELECT poi.feat_id as poi_feat_id
  ,poi.name as poi_name,poi.geom
  , meta0.code_description as meta0_code_description
  , attr0.attribute_type as attr0_attr_type 
  , meta1.code_description as meta1_code_description
  , attr1.attribute_type as attr1_attr_type,attr1.value_integer as attr1_integer,attr1.value_boolean as attr1_bool 
  , meta2.code_description as meta2_code_description
  , attr2.attribute_type as attr2_attr_type,attr2.value_varchar as attr2_varchar,attr2.value_integer as attr2_integer,attr2.value_boolean as attr2_bool 
  , enumval3.code_description as restriction
  , enumval4.code_description as power_supply
  , enumval5.code_description as charging_receptacle
  , enumval6.code_description as charging_services
  , enumval7.code_description as charging_facilities
  , enumval8.code_description as ev_level

FROM ( 
  SELECT * FROM {schema}.mnr_poi poi  
  WHERE poi.feat_type = 7309
  AND ST_Intersects(poi.geom,ST_GeomFromText({extent},4326)) 
  ) poi 

LEFT JOIN {schema}.mnr_poi2attribute  poi2attr0 
  ON poi.feat_id = poi2attr0.poi_id 

INNER JOIN {schema}.mnr_attribute  attr0 
  ON poi2attr0.attribute_id = attr0.attribute_id

LEFT JOIN (   
  SELECT * from {schema}.mnr_meta_enum  enu
  JOIN {schema}.mnr_meta_enum_value  val  ON enu.enum_id = val.enum_id
  ) meta0 
  ON attr0.attribute_type::varchar = meta0.code

LEFT JOIN {schema}.mnr_attribute  attr1 
  ON attr0.attribute_id = attr1.parent_attribute_id 

LEFT JOIN (   
  SELECT * from {schema}.mnr_meta_enum  enu   
  JOIN {schema}.mnr_meta_enum_value  val  ON enu.enum_id = val.enum_id
  ) meta1 
  ON attr1.attribute_type::varchar = meta1.code 

LEFT JOIN {schema}.mnr_attribute  attr2 
  ON attr1.attribute_id = attr2.parent_attribute_id 

LEFT JOIN (   
  SELECT * from {schema}.mnr_meta_enum  enu
  JOIN {schema}.mnr_meta_enum_value  val  ON enu.enum_id = val.enum_id
  ) meta2
  ON attr2.attribute_type::varchar = meta2.code 

LEFT JOIN (
  SELECT * from {schema}.mnr_meta_enum  enu
  JOIN {schema}.mnr_meta_enum_value  val
  ON enu.enum_id = val.enum_id AND enu.enum_description='Special Restriction' 
  ) enumval3
  ON attr1.attribute_type='SR' AND  attr1.value_integer::varchar = enumval3.code

LEFT JOIN (
  SELECT * from {schema}.mnr_meta_enum  enu   
  JOIN {schema}.mnr_meta_enum_value  val   
  ON enu.enum_id = val.enum_id AND enu.enum_description='EV Power Supply' 
  ) enumval4
  ON attr2.attribute_type='Z0' AND  attr2.value_integer::varchar = enumval4.code

LEFT JOIN (
  SELECT * from {schema}.mnr_meta_enum  enu   
  JOIN {schema}.mnr_meta_enum_value  val   
  ON enu.enum_id = val.enum_id AND enu.enum_description='EV Charging Receptacle' 
  ) enumval5
  ON attr2.attribute_type='EY' AND  attr2.value_integer::varchar = enumval5.code

LEFT JOIN (
  SELECT * from {schema}.mnr_meta_enum  enu   
  JOIN {schema}.mnr_meta_enum_value  val   
  ON enu.enum_id = val.enum_id AND enu.enum_description='Charging Spot Service' 
  ) enumval6
  ON attr2.attribute_type='EZ' AND  attr2.value_integer::varchar = enumval6.code

LEFT JOIN (
  SELECT * from {schema}.mnr_meta_enum  enu   
  JOIN {schema}.mnr_meta_enum_value  val   
  ON enu.enum_id = val.enum_id AND enu.enum_description='EV Charging Facilities' 
  ) enumval7
  ON attr2.attribute_type='EE' AND  attr2.value_integer::varchar = enumval7.code

LEFT JOIN (
  SELECT * from {schema}.mnr_meta_enum  enu   
  JOIN {schema}.mnr_meta_enum_value  val   
  ON enu.enum_id = val.enum_id AND enu.enum_description='EV Level' 
  ) enumval8
  ON attr1.attribute_type='W8' AND  attr1.value_integer::varchar = enumval8.code
); """.format(table = matViewResultTable, schema = mnrSchema, extent = extentStr)

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

