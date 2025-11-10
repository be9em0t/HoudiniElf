
	-- buildings with parts (deduplicated)
	-- Strategy:
	-- 1) collect relation-based assembled geometries that represent buildings (rg_buildings)
	-- 2) select polygons that represent buildings but do NOT intersect any relation-based building geometry (polygons_pref)
	-- 3) union polygons_pref with relation geometries (prefer relation-level tags)
	WITH
		bbox AS (
			SELECT ST_GEOMFROMWKT('POLYGON((13.366338302455723 52.496137642548184, 13.366338302455723 52.515559037181255, 13.398245676220093 52.515559037181255, 13.398245676220093 52.496137642548184, 13.366338302455723 52.496137642548184))') AS geom
		),

		-- relation geometries that look like polygons/multipolygons and intersect the bbox
		rg_buildings AS (
			SELECT
				orbis_id,
				tags,
				mcr_tags,
				geom_type,
				-- clean SRID prefix if present and parse once here
				ST_GEOMFROMWKT(regexp_replace(geometry, '^SRID=[0-9]+;', '')) AS geom
			FROM pu_orbis_platform_prod_catalog.map_central_repository.relations_geometries
			WHERE geom_type IN ('ST_POLYGON','ST_MULTIPOLYGON')
				AND product = 'nexventura_25430.000'
				AND license_zone LIKE '%DEU%'
				AND (
					UPPER(geometry) LIKE 'POLYGON(%' OR
					UPPER(geometry) LIKE 'MULTIPOLYGON(%' OR
					UPPER(geometry) LIKE 'SRID=%POLYGON(%' OR
					UPPER(geometry) LIKE 'SRID=%MULTIPOLYGON(%'
				)
				AND ST_Intersects((SELECT geom FROM bbox), ST_GEOMFROMWKT(regexp_replace(geometry, '^SRID=[0-9]+;','')))
		),

		-- polygons that are buildings but do not intersect any relation-based building geometry
		polygons_pref AS (
			SELECT
				p.orbis_id,
				p.tags,
				p.mcr_tags,
				ST_GEOMFROMWKT(p.geometry) AS geom
			FROM pu_orbis_platform_prod_catalog.map_central_repository.polygons p
			WHERE (p.building = 'yes' OR p.tags['building'] IS NOT NULL OR p.tags['building:part'] IS NOT NULL)
				AND p.product = 'nexventura_25430.000'
				AND p.license_zone LIKE '%DEU%'
				AND ST_Intersects((SELECT geom FROM bbox), ST_GEOMFROMWKT(p.geometry))
				-- exclude polygons that intersect any relation-based building geometry (we prefer relation geometries)
				AND NOT EXISTS (
					SELECT 1 FROM rg_buildings rg
					WHERE ST_Intersects(ST_GEOMFROMWKT(p.geometry), rg.geom)
				)
		)

	-- final output: polygons that aren't covered by relations, plus relation geometries (prefer relation tags)
	SELECT
		orbis_id,
		tags['layer'] AS layer,
		tags['type'] AS type,
		tags['building'] AS building,
		tags['building:part'] AS part,
		tags['height'] AS height,
		tags['min_height'] AS min_height,
		tags['building:levels'] AS levels,
		tags['building:min_level'] AS min_level,
		tags['location'] AS location,
		tags['construction'] AS construction,
		tags['zoomlevel_min'] AS zoomlevel_min,
		CAST(mcr_tags AS STRING) AS mcr_string,
		-- return WKT geometry so downstream tools expect the same shape as before
		ST_ASTEXT(geom) AS geometry
	FROM polygons_pref

	UNION ALL

	SELECT
		rg.orbis_id,
		rg.tags['layer'] AS layer,
		rg.tags['type'] AS type,
		rg.tags['building'] AS building,
		rg.tags['building:part'] AS part,
		rg.tags['height'] AS height,
		rg.tags['min_height'] AS min_height,
		rg.tags['building:levels'] AS levels,
		rg.tags['building:min_level'] AS min_level,
		rg.tags['location'] AS location,
		rg.tags['construction'] AS construction,
		rg.tags['zoomlevel_min'] AS zoomlevel_min,
		CAST(rg.mcr_tags AS STRING) AS mcr_string,
		ST_ASTEXT(rg.geom) AS geometry
	FROM rg_buildings rg

UNION

-- Prefer relation-level tags, but include relations that have member roles 'outline' or 'part'
SELECT
r.orbis_id,
COALESCE(r.tags['layer'], rg.tags['layer']) AS layer,
COALESCE(r.tags['type'], rg.tags['type']) AS type,
COALESCE(r.tags['building'], rg.tags['building']) AS building,
COALESCE(r.tags['building:part'], rg.tags['building:part']) AS part,
COALESCE(r.tags['height'], rg.tags['height']) AS height,
COALESCE(r.tags['min_height'], rg.tags['min_height']) AS min_height,
COALESCE(r.tags['building:levels'], rg.tags['building:levels']) AS levels,
COALESCE(r.tags['building:min_level'], rg.tags['building:min_level']) AS min_level,
COALESCE(r.tags['location'], rg.tags['location']) AS location,
COALESCE(r.tags['construction'], rg.tags['construction']) AS construction,
COALESCE(r.tags['zoomlevel_min'], rg.tags['zoomlevel_min']) AS zoomlevel_min,
CAST(COALESCE(r.mcr_tags, rg.mcr_tags) AS STRING) as mcr_string,
rg.geometry
FROM pu_orbis_platform_prod_catalog.map_central_repository.relations r
JOIN pu_orbis_platform_prod_catalog.map_central_repository.relations_geometries rg
	ON r.orbis_id = rg.orbis_id
WHERE
	(
		r.tags['building'] IS NOT NULL
		OR r.tags['building:part'] IS NOT NULL
		OR SIZE(FILTER(r.members, x -> x.role = 'outline')) > 0
		OR SIZE(FILTER(r.members, x -> x.role = 'part')) > 0
	)
AND rg.geom_type in ("ST_POLYGON","ST_MULTIPOLYGON")
AND ST_Intersects(ST_GEOMFROMWKT('POLYGON((13.366338302455723 52.496137642548184, 13.366338302455723 52.515559037181255, 13.398245676220093 52.515559037181255, 13.398245676220093 52.496137642548184, 13.366338302455723 52.496137642548184))'), ST_GEOMFROMWKT(rg.geometry))
AND r.product = 'nexventura_25430.000'
AND r.license_zone like '%DEU%'