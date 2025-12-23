
WITH polygons_geom AS (
	SELECT *, 
		ST_GeomFromWKT(geometry) AS g,
		ST_GeomFromWKT('POLYGON((16.468759861054814 49.119446246499095, 16.468759861054814 49.272903955515325, 16.776842039257453 49.272903955515325, 16.776842039257453 49.119446246499095, 16.468759861054814 49.119446246499095))') AS bbox
	FROM pu_orbis_platform_prod_catalog.map_central_repository.polygons
)

SELECT 
orbis_id,
place,
name,
-- mcr_tags,
geometry

FROM 
polygons_geom 

WHERE 
place is not null
AND 
product = 'nexventura_25480.000'
AND
license_zone like '%CZE%'
AND
ST_Intersects(g, bbox)
