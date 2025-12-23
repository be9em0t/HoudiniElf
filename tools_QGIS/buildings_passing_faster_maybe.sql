
	-- buildings with parts 
	-- no relations_geometry
WITH polygons_filtered AS (
	SELECT *
	FROM pu_orbis_platform_prod_catalog.map_central_repository.polygons
	WHERE 
		product = 'nexventura_25480.000'
		AND license_zone like '%CZE%'
		AND ( building ='yes' or tags['building'] is not null or tags['building:part'] is not null)
),
polygons_geom AS (
	SELECT *, 
		ST_GeomFromWKT(geometry) AS g,
		ST_GeomFromWKT('POLYGON((16.468759861054814 49.119446246499095, 16.468759861054814 49.272903955515325, 16.776842039257453 49.272903955515325, 16.776842039257453 49.119446246499095, 16.468759861054814 49.119446246499095))') AS bbox
	FROM polygons_filtered
),
polygons_bounds AS (
	SELECT *,
		ST_XMin(g) as xmin,
		ST_XMax(g) as xmax,
		ST_YMin(g) as ymin,
		ST_YMax(g) as ymax
	FROM polygons_geom
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
	polygons_bounds
WHERE 
	xmin <= 16.776842039257453
	AND xmax >= 16.468759861054814
	AND ymin <= 49.272903955515325
	AND ymax >= 49.119446246499095
	AND ST_Intersects(bbox, g)
	