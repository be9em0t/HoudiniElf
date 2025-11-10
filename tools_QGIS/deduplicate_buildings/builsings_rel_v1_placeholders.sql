
	-- buildings with parts 
	-- include relation geometries too (relations_geometries contains assembled relation polygons/multipolygons)
	SELECT 
	orbis_id,
	tags['layer'] as layer,
	tags['type'] as type,
	tags['building'] as building,
	tags['building:part'] as part,
	tags['height'] as height,
	tags['min_height'] as min_height,
	tags['building:levels'] as levels,
	tags['building:min_level'] as min_level,
	tags['location'] as location,
	tags['construction'] as construction,
	tags['zoomlevel_min'] as zoomlevel_min,
	CAST(mcr_tags AS STRING) as mcr_string,
	--map_filter(mcr_tags, (key, value) -> NOT (key LIKE 'layer_id:%' OR key LIKE 'gers%' OR key LIKE 'license%' OR key LIKE 'maxspeed%' OR key LIKE 'oprod%' OR key LIKE 'source%' OR key LIKE 'supported%' OR key LIKE 'zoomlevel_min' OR key LIKE 'routing_class' OR key LIKE 'navigability' OR key LIKE 'postal_code%' OR key LIKE '%pronunciation%' )) AS mcr_clean,
	geometry
	FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.polygons
	WHERE 
	--( building ='yes' or tags['building'] is not null)
	( building ='yes' or tags['building'] is not null or tags['building:part'] is not null)
	AND 
	ST_Intersects(ST_GEOMFROMWKT({extent}), ST_GEOMFROMWKT(geometry)) 
	AND 
	product = '{product_version}'
	AND
	license_zone like '%{license_zone}%'

UNION

-- buildings coming from relation geometries (assembled multipolygons / polygons)
SELECT 
orbis_id,
tags['layer'] as layer,
tags['type'] as type,
tags['building'] as building,
tags['building:part'] as part,
tags['height'] as height,
tags['min_height'] as min_height,
tags['building:levels'] as levels,
tags['building:min_level'] as min_level,
tags['location'] as location,
tags['construction'] as construction,
tags['zoomlevel_min'] as zoomlevel_min,
CAST(mcr_tags AS STRING) as mcr_string,
geometry
FROM 
pu_orbis_platform_prod_catalog.map_central_repository.relations_geometries
WHERE 
-- pick only polygonal relation geometries that represent buildings
( tags['building'] is not null OR tags['building:part'] is not null )
AND
geom_type in ("ST_POLYGON","ST_MULTIPOLYGON")
AND 
ST_Intersects(ST_GEOMFROMWKT({extent}), ST_GEOMFROMWKT(geometry)) 
AND 
product = '{product_version}'
AND
license_zone like '%{license_zone}%'
	