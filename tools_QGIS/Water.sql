
	-- inland water (natural=water)
	-- old is 2.55 : new is 1.45
WITH bbox AS (
	SELECT ST_GEOMFROMWKT('POLYGON((16.468759861054814 49.119446246499095, 16.468759861054814 49.272903955515325, 16.776842039257453 49.272903955515325, 16.776842039257453 49.119446246499095, 16.468759861054814 49.119446246499095))') AS g
)

SELECT 
	orbis_id,
	intermittent,
	geometry 
FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.polygons,
	bbox
WHERE 
	natural = 'water' 
	AND ST_Intersects(bbox.g, ST_GEOMFROMWKT(geometry))
	AND product = 'nexventura_25480.000'
	AND license_zone LIKE '%CZE%' 

UNION 

SELECT 
	orbis_id,
	tags['intermittent'] AS intermittent,
	geometry 
FROM 
	pu_orbis_platform_prod_catalog.map_central_repository.relations_geometries,
	bbox
WHERE 
	tags['natural'] = 'water'
	AND geom_type IN ("ST_POLYGON","ST_MULTIPOLYGON")
	AND ST_Intersects(bbox.g, ST_GEOMFROMWKT(geometry))
	AND product = 'nexventura_25480.000'
	AND license_zone LIKE '%CZE%';