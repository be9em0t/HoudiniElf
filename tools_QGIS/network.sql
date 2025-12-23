
	WITH lines_geom AS (
SELECT *, ST_GeomFromWKT(geometry) AS geom
FROM pu_orbis_platform_prod_catalog.map_central_repository.lines
)
select
	orbis_id, 
	highway,
	railway, 
	bridge, tunnel,
	tags['navigability'] AS navigability,
	tags['routing_class'] AS routing_class,
	tags['maxspeed'] AS maxspeed,
	layer, 
	geometry
	FROM 
	lines_geom
	WHERE 
	("highway" is not null 
	or 
	tags['routing_class'] is not null
	)
	AND
	ST_XMin(geom) <= 16.641472425886608
	AND ST_XMax(geom) >= 16.628109003278404
	AND ST_YMin(geom) <= 49.1975372039437
	AND ST_YMax(geom) >= 49.18914234691329 
	AND 
	product = 'nexventura_25480.000'
	AND
	license_zone like '%CZE%' 
	