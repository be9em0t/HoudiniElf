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
	
	# fLoadManeuverPts, fLoadManeuverArrow
	newLayer = fLoadManeuverPts(mnrServer,mnrSchema,extentCoords)
	newLayer = fLoadManeuverArrow(mnrServer,mnrSchema,extentCoords)
	# fSymbol(newLayer)


def fLoadManeuverArrow(mnrServer,mnrSchema,extentCoords):

	# # === db MNR matview ===
	matViewPrefix = "b9" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "maneuver_arrow"
	extentStr = "'" + extentCoords + "'"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	manFields = b9PyQGIS.fFieldsFromString("man.", "maneuver_id,maneuver_seq,geom") # maneuver_id,maneuver_seq,feat_type,geom

	metaFields = b9PyQGIS.fFieldsFromString("meta.", "code_description as maneuver_desc") # enum_value_id,enum_id,code,code_description

	metaCodeDescript = 'Feature Type Maneuvers'

	queryMNRLine =  "CREATE TABLE " + matViewResultTable + " as \
		SELECT " + manFields + "," + metaFields +\
		" FROM " + mnrSchema + ".mnr_maneuver_arrow man " +\
	" LEFT JOIN (" + \
		"  SELECT code, code_description" + \
		"  FROM " + mnrSchema + ".mnr_meta_enum_value enumval" + \
		"    WHERE enumval.enum_id=(" + \
		"    SELECT enum_id FROM " + mnrSchema + ".mnr_meta_enum enum" + \
		"    WHERE enum.enum_description=\'" + metaCodeDescript + "\')" + \
		"  ORDER BY code_description" + \
		"  ) as meta" + \
		" ON man.feat_type::varchar = meta.code" + \
		" WHERE " +\
		" ST_Intersects(man.geom,ST_GeomFromText(" + extentStr + ",4326)) ;"

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

def fLoadManeuverPts(mnrServer,mnrSchema,extentCoords):

	# # === db MNR matview ===
	matViewPrefix = "b9" + mnrSchema[0:8] + "_"
	matViewResultTable = matViewPrefix + "maneuver_pts"
	extentStr = "'" + extentCoords + "'"

	queryDropLine = "DROP TABLE IF EXISTS " + matViewResultTable + " CASCADE;"

	manPtFields = b9PyQGIS.fFieldsFromString("manpt.", "feat_id,geom") # feat_id,feat_type,junction_id,bifurcation_type,signpost_color_palette_id,geom

	signFields = b9PyQGIS.fFieldsFromString("sign.", "destination_set,destination_seq,ambiguous,place_name_id,exit_name_id,exit_num,street_name_id,other_dest_name_id,routeset_id") # maneuver_id,destination_set,destination_seq,ambiguous,pictogram,place_name_id,exit_name_id,exit_num,street_name_id,other_dest_name_id,connection,routeset_id

	metaFieldsPictogram = b9PyQGIS.fFieldsFromString("metapic.", "code_description as pictogram") # enum_value_id,enum_id,code,code_description
	metaDescPictogram = 'Pictogram'

	metaFieldsConn = b9PyQGIS.fFieldsFromString("metaconn.", "code_description as connection") # enum_value_id,enum_id,code,code_description
	metaDescConnect = 'Connection Info'

	metaFieldsType = b9PyQGIS.fFieldsFromString("metatype.", "code_description as maneuver_desc") # enum_value_id,enum_id,code,code_description
	metaDescriptType = 'Feature Type Maneuvers'

	queryMNRLine =  "CREATE TABLE " + matViewResultTable + " as \
		SELECT " + manPtFields + "," + metaFieldsType + "," + metaFieldsPictogram + "," + metaFieldsConn +\
		" FROM " + mnrSchema + ".mnr_maneuver manpt " +\
		" LEFT JOIN " + mnrSchema + ".mnr_signpost_info sign" +\
		"  ON manpt.feat_id = sign.maneuver_id" +\
		"  AND sign.pictogram is not null" +\
		" LEFT JOIN (" + \
		"  SELECT code, code_description" + \
		"  FROM " + mnrSchema + ".mnr_meta_enum_value enumval" + \
		"    WHERE enumval.enum_id=(" + \
		"    SELECT enum_id FROM " + mnrSchema + ".mnr_meta_enum enum" + \
		"    WHERE enum.enum_description=\'" + metaDescriptType + "\')" + \
		"  ORDER BY code_description" + \
		"  ) as metatype" +\
		" ON manpt.feat_type::varchar = metatype.code" +\
		" LEFT JOIN (" + \
		"  SELECT code, code_description" + \
		"  FROM " + mnrSchema + ".mnr_meta_enum_value enumval" + \
		"    WHERE enumval.enum_id=(" + \
		"    SELECT enum_id FROM " + mnrSchema + ".mnr_meta_enum enum" + \
		"    WHERE enum.enum_description=\'" + metaDescPictogram + "\')" + \
		"  ORDER BY code_description" + \
		"  ) as metapic" + \
		" ON sign.pictogram::varchar = metapic.code" + \
		" LEFT JOIN (" + \
		"  SELECT code, code_description" + \
		"  FROM " + mnrSchema + ".mnr_meta_enum_value enumval" + \
		"    WHERE enumval.enum_id=(" + \
		"    SELECT enum_id FROM " + mnrSchema + ".mnr_meta_enum enum" + \
		"    WHERE enum.enum_description=\'" + metaDescConnect + "\')" + \
		"  ORDER BY code_description" + \
		"  ) as metaconn" + \
		" ON sign.connection::varchar = metaconn.code" + \
		" WHERE " +\
		" ST_Intersects(manpt.geom,ST_GeomFromText(" + extentStr + ",4326)) ;"
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
