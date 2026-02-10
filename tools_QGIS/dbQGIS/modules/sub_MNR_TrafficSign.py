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

	print("Traffic Signs Sub")	
	# # fLoadSignPoints, fLoadManeuverArrow
	newLayer = fLoadSignPoints(mnrServer,mnrSchema,extentCoords)
	# newLayer = fLoadManeuverPts(mnrServer,mnrSchema,extentCoords)
	# newLayer = fLoadManeuverArrow(mnrServer,mnrSchema,extentCoords)
	# # fSymbol(newLayer)

def fLoadSignPoints(mnrServer,mnrSchema,extentCoords):

	# # === db MNR matview ===
	matViewPrefix = "b9" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "traffic_signs"
	extentStr = "'" + extentCoords + "'"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	signPtFields = b9PyQGIS.fFieldsFromString("trsignpt.", "feat_type,value_on_sign,unit,line_side,geom") 

	metaFieldsType = b9PyQGIS.fFieldsFromString("metatype.", "code_description as sign_desc") # enum_value_id,enum_id,code,code_description
	metaDescriptType = 'Feature Type Road Furniture'

	metaUnit = b9PyQGIS.fFieldsFromString("metaunit.", "code_description as unit_desc") # enum_value_id,enum_id,code,code_description
	metaDescriptUnit = 'Unit Of Speed Restriction'

	metaRoadSide = b9PyQGIS.fFieldsFromString("metaside.", "code_description as side_desc") # enum_value_id,enum_id,code,code_description
	metaDescriptSide = 'Side Of Line And On'


	queryMNRLine =  "CREATE TABLE " + matViewResultTable + " as \
		SELECT " + signPtFields + "," + metaFieldsType + "," + metaUnit + "," + metaRoadSide +\
		" FROM " + mnrSchema + ".mnr_road_furniture trsignpt " +\
		" LEFT JOIN (" + \
		"  SELECT code, code_description" + \
		"  FROM " + mnrSchema + ".mnr_meta_enum_value enumval" + \
		"    WHERE enumval.enum_id=(" + \
		"    SELECT enum_id FROM " + mnrSchema + ".mnr_meta_enum enum" + \
		"    WHERE enum.enum_description=\'" + metaDescriptType + "\')" + \
		"  ORDER BY code_description" + \
		"  ) as metatype" +\
		" ON trsignpt.feat_type::varchar = metatype.code" +\
		" LEFT JOIN (" + \
		"  SELECT code, code_description" + \
		"  FROM " + mnrSchema + ".mnr_meta_enum_value enumval" + \
		"    WHERE enumval.enum_id=(" + \
		"    SELECT enum_id FROM " + mnrSchema + ".mnr_meta_enum enum" + \
		"    WHERE enum.enum_description=\'" + metaDescriptUnit + "\')" + \
		"  ORDER BY code_description" + \
		"  ) as metaunit" +\
		" ON trsignpt.unit::varchar = metaunit.code" +\
		" LEFT JOIN (" + \
		"  SELECT code, code_description" + \
		"  FROM " + mnrSchema + ".mnr_meta_enum_value enumval" + \
		"    WHERE enumval.enum_id=(" + \
		"    SELECT enum_id FROM " + mnrSchema + ".mnr_meta_enum enum" + \
		"    WHERE enum.enum_description=\'" + metaDescriptSide + "\')" + \
		"  ORDER BY code_description" + \
		"  ) as metaside" +\
		" ON trsignpt.line_side::varchar = metaside.code" +\
		" WHERE " +\
		" ST_Intersects(trsignpt.geom,ST_GeomFromText(" + extentStr + ",4326)) ;" +\
		" ALTER TABLE " + "public." + matViewResultTable +\
		" DROP COLUMN " +  "unit," +\
		" DROP COLUMN " +  "line_side" + ";" #unit,line_side
		# " (sign.pictogram is not null OR sign.connection is not null) AND" +\

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
