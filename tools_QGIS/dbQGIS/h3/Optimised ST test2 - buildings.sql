
	-- buildings with parts (OPTIMIZED - bbox computed once)
	-- no relations_geometry
WITH bbox AS (
	SELECT ST_GeomFromWKT('POLYGON((4.86331387739974 52.35322015495234, 4.86331387739974 52.39427120115568, 4.943944608245146 52.39427120115568, 4.943944608245146 52.35322015495234, 4.86331387739974 52.35322015495234))') AS geom
),

polygons_geom AS (
	SELECT
		orbis_id,
		building,
		tags,
		product,
		license_zone,
		geometry,
		ST_GeomFromWKT(geometry) AS g
	FROM pu_orbis_platform_prod_catalog.map_central_repository.polygons
)

SELECT 
	p.orbis_id,
	p.tags['layer'] as layer,
	p.tags['type'] as type,
	p.tags['building'] as building,
	p.tags['building:part'] as part,
	p.tags['height'] as height,
	p.tags['min_height'] as min_height,
	p.tags['building:levels'] as levels,
	p.tags['building:min_level'] as min_level,
	p.tags['location'] as location,
	p.tags['construction'] as construction,
	p.tags['zoomlevel_min'] as zoomlevel_min,
	p.geometry
FROM polygons_geom p
CROSS JOIN bbox b
WHERE 
	(p.building = 'yes'
	 OR p.tags['building'] IS NOT NULL
	 OR p.tags['building:part'] IS NOT NULL)
	AND ST_Intersects(b.geom, p.g)
	AND p.product = 'nexventura_26060.000'
	AND p.license_zone LIKE '%NLD%'
	