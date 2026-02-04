
	-- buildings with parts 
	-- no relations_geometry
WITH polygons_geom AS (
	SELECT *, 
		ST_GeomFromWKT(geometry) AS g,
		ST_GeomFromWKT('POLYGON((4.689851292704134 52.26897277133037, 4.689851292704134 52.43802048721305, 5.09170592463983 52.43802048721305, 5.09170592463983 52.26897277133037, 4.689851292704134 52.26897277133037))') AS bbox
	FROM pu_orbis_platform_prod_catalog.map_central_repository.polygons
)
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
--	CAST(mcr_tags AS STRING) as mcr_string,
	--map_filter(mcr_tags, (key, value) -> NOT (key LIKE 'layer_id:%' OR key LIKE 'gers%' OR key LIKE 'license%' OR key LIKE 'maxspeed%' OR key LIKE 'oprod%' OR key LIKE 'source%' OR key LIKE 'supported%' OR key LIKE 'zoomlevel_min' OR key LIKE 'routing_class' OR key LIKE 'navigability' OR key LIKE 'postal_code%' OR key LIKE '%pronunciation%' )) AS mcr_clean,
	geometry
FROM 
	polygons_geom
WHERE 
	( building ='yes' or tags['building'] is not null or tags['building:part'] is not null)
	AND 
	ST_Intersects(bbox, g) 
	AND 
	product = 'nexventura_26060.000'
	AND
	license_zone like '%NLD%'
	