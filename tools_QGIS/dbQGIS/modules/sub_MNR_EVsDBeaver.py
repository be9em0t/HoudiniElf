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
	# print ("New EVs")
	# fSymbol(newLayer)

def fLoadPOIs_EV(mnrServer,mnrSchema,extentCoords):

	# # === db MNR matview ===
	# matViewPrefix = "b9" + mnrSchema[0:8] + "_"
	# matViewPrefix = "b9" + mnrSchema + "_"
	# matViewResultTable = matViewPrefix + "ev"
	matViewResultTable = "b9_ev" + mnrSchema
	extentStr = "'" + extentCoords + "'"


	queryMNRLine =  """
SET search_path TO {schema},public;
-- SHOW search_path;

drop table if exists meta_enum_table;
CREATE TEMP TABLE meta_enum_table as
SELECT 
	mnr_meta_enum.enum_id,
	mnr_meta_enum.enum_description,
	mnr_meta_enum_value.enum_value_id,
	mnr_meta_enum_value.code,
	mnr_meta_enum_value.code_description 
	FROM mnr_meta_enum
	JOIN mnr_meta_enum_value ON mnr_meta_enum.enum_id = mnr_meta_enum_value.enum_id
	order by mnr_meta_enum.enum_description
;

--SELECT * 
--from meta_enum_table

drop table if exists meta_info_table;
CREATE TEMP TABLE meta_info_table as

SELECT DISTINCT
    mnr_meta_table.table_name,
    mnr_meta_field.field_name,
    mnr_meta_enum_value.code,
    mnr_meta_enum_value.code_description
FROM
    mnr_meta_table,
    mnr_meta_table2field,
    mnr_meta_field,
    mnr_meta_enum_value
WHERE mnr_meta_table.table_id = mnr_meta_table2field.table_id AND mnr_meta_table2field.field_id = mnr_meta_field.field_id AND mnr_meta_field.enum_id = mnr_meta_enum_value.enum_id
ORDER BY mnr_meta_table.table_name, mnr_meta_field.field_name, mnr_meta_enum_value.code
;

--select *
--from meta_info_table
--where table_name ilike 'MNR_POI'
----where table_name = 'MNR_Hierarchy' and field_name = 'FEAT_TYPE'
--;

--value_decimal,parent_attribute_id,value_integer,value_boolean,attribute_id,value_type,enum_id,nameset_id,attribute_type,value_text,value_varchar
--- NEW MAIN query ---
select 
mnr_poi.feat_id AS poi_id , mnr_poi.name AS poi_name, --mnr_poi.feat_type AS feat_type , 

mnr_poi_address.hsn as addr_house_nr,
mnr_name_sn.name as addr_street_name,
mnr_name_pn.name as addr_place_name,
mnr_postal_point.postal_code as addr_postal_code,

parent.attribute_type as attribute_type_parent, 
metaParent.code_description as attribute_type_parent_descript, 
parent.value_type as value_type_parent, 
parent.value_varchar as parent_value_varchar,

child1.attribute_type as attribute_type_child1, 
metaChild1.code_description as attribute_type_child1_descript, 
child1.value_type as value_type_child1, 
child1.value_varchar as value_varchar_child1,
child1.value_integer as value_integer_child1,
(Case 
When child1.value_boolean = False Then 'False'
When child1.value_boolean = True Then 'True'
Else NULL End) as value_bool_child1,
metaChild1enum.code_description as enum_descript_child1,

child2.attribute_type as attribute_type_child2, 
metaChild2.code_description as attribute_type_child2_descript, 
child2.value_type as value_type_child2, 
child2.value_varchar as value_varchar_child2,
child2.value_integer as value_integer_child2,
(Case 
When child2.value_boolean = False Then 'False'
When child2.value_boolean = True Then 'True'
Else NULL End) as value_bool_child2,
metaChild2enum.code_description as enum_descript_child2,

mnr_poi.geom
--*
from mnr_poi
left outer join mnr_poi2attribute on mnr_poi.feat_id = mnr_poi2attribute.poi_id
inner join mnr_attribute as parent 
	on mnr_poi2attribute.attribute_id = parent.attribute_id 

LEFT JOIN meta_info_table metaParent --using temp table
	ON parent.attribute_type::varchar = metaParent.code
	
left outer join mnr_attribute as child1 
	on child1.parent_attribute_id = parent.attribute_id 
	and parent.value_type=11

LEFT JOIN meta_info_table metaChild1 --using temp table
	ON child1.attribute_type::varchar = metaChild1.code
	
left outer join mnr_attribute as child2 
	on child2.parent_attribute_id = child1.attribute_id 
	and child1.value_type=11

LEFT JOIN meta_enum_table metaChild1enum --using temp table
	ON child1.enum_id = metaChild1enum.enum_id
	AND child1.value_integer::varchar = metaChild1enum.code
	
LEFT JOIN meta_info_table metaChild2 --using temp table
	ON child2.attribute_type::varchar = metaChild2.code

LEFT JOIN meta_enum_table metaChild2enum --using temp table
	ON child2.enum_id = metaChild2enum.enum_id
	AND child2.value_integer::varchar = metaChild2enum.code

left outer join mnr_poi_address  
	on mnr_poi.poi_address_id = mnr_poi_address.poi_address_id 
--	and parent.attribute_type in ('CHPT', 'CCST', 'CCSP')
left outer join mnr_postal_point on mnr_poi_address.postal_point_id     = mnr_postal_point.feat_id
left outer join mnr_nameset2name as mnr_nameset2name_sn on mnr_poi_address.street_nameset_id   = mnr_nameset2name_sn.nameset_id
left outer join mnr_name         as mnr_name_sn on mnr_nameset2name_sn.name_id = mnr_name_sn.name_id
left outer join mnr_nameset2name as mnr_nameset2name_pn on mnr_poi_address.place_nameset_id = mnr_nameset2name_pn.nameset_id
left outer join mnr_name         as mnr_name_pn on mnr_nameset2name_pn.name_id = mnr_name_pn.name_id

where 
	mnr_poi.feat_type = 7309
	AND ST_Intersects(mnr_poi.geom,ST_GeomFromText({extent},4326)) 
order by mnr_poi.feat_id, child1.attribute_type
	; """.format(schema = mnrSchema, extent = extentStr)


	# print("\n" + queryDropLine)
	print("\n" + extentStr)
	print("\n" + queryMNRLine)
	clipboard = QgsApplication.clipboard()
	clipboard.setText(queryMNRLine)



	message = "Query is on the Clipboard\nRun it from dBeaver or similar and load result into QGIS"
	qtMsgBox(message)

	print("\nQuery is on the Clipboard\nRun it from dBeaver or similar and load result in QGIS")

	# b9PyQGIS.fPostGISexec(mnrServer, queryMNRLine)
	# uri = QgsDataSourceUri()
	# uri.setConnection(mnrServer, "5432", "mnr", "mnr_ro", "mnr_ro")
	# # uri.setDataSource("public", matViewResultTable, "geom", aKeyColumn="feat_type")
	# uri.setDataSource("public", matViewResultTable, "geom", aKeyColumn="id")
	# vlayer = iface.addVectorLayer(uri.uri(False), matViewResultTable, "postgres")

