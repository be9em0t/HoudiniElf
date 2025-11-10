
-- VARIANT: prefer relation-level tags
-- This returns the geometry from relations_geometries but uses tags from the relation
-- Optimized variant: filter relation geometries first, then join to relations
-- Rationale: relations_geometries is usually much smaller once constrained by geom_type/bbox/product/license; this avoids scanning the full relations table or running heavy geometry ops over all rows.
WITH
	bbox AS (
		SELECT ST_GEOMFROMWKT('POLYGON((13.366338302455723 52.496137642548184, 13.366338302455723 52.515559037181255, 13.398245676220093 52.515559037181255, 13.398245676220093 52.496137642548184, 13.366338302455723 52.496137642548184))') AS geom
	),

	bbox_swapped AS (
		-- alternative bbox with X/Y swapped in case stored geometries use lat/lon order instead of lon/lat
		SELECT ST_GEOMFROMWKT('POLYGON((52.496137642548184 13.366338302455723, 52.515559037181255 13.366338302455723, 52.515559037181255 13.398245676220093, 52.496137642548184 13.398245676220093, 52.496137642548184 13.366338302455723))') AS geom
	),

	rg_filtered AS (
		-- Only attempt to parse WKT for rows that look like polygon/multipolygon WKT (or have SRID prefixes)
		-- This avoids parsing arbitrary strings that cause the WKT_PARSE_ERROR on the server.
		SELECT
		  orbis_id,
		  geometry,
		  tags AS rg_tags,
		  mcr_tags AS rg_mcr_tags
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
		  -- now safely parse the cleaned WKT for the spatial intersection test (strip SRID=...; prefix first)
					-- intersection test against either the normal bbox or a swapped-order bbox
					AND (
						ST_Intersects(
							(SELECT geom FROM bbox),
							ST_GEOMFROMWKT(regexp_replace(geometry, '^SRID=[0-9]+;', ''))
						)
						OR
						ST_Intersects(
							(SELECT geom FROM bbox_swapped),
							ST_GEOMFROMWKT(regexp_replace(geometry, '^SRID=[0-9]+;', ''))
						)
					)
	)

SELECT
	r.orbis_id,
	-- prefer relation-level tag, fall back to relation_geometry tag if missing
	COALESCE(r.tags['layer'], rg.rg_tags['layer']) AS layer,
	COALESCE(r.tags['type'], rg.rg_tags['type']) AS type,
	COALESCE(r.tags['building'], rg.rg_tags['building']) AS building,
	COALESCE(r.tags['building:part'], rg.rg_tags['building:part']) AS part,
	COALESCE(r.tags['height'], rg.rg_tags['height']) AS height,
	COALESCE(r.tags['min_height'], rg.rg_tags['min_height']) AS min_height,
	COALESCE(r.tags['building:levels'], rg.rg_tags['building:levels']) AS levels,
	COALESCE(r.tags['building:min_level'], rg.rg_tags['building:min_level']) AS min_level,
	COALESCE(r.tags['location'], rg.rg_tags['location']) AS location,
	COALESCE(r.tags['construction'], rg.rg_tags['construction']) AS construction,
	COALESCE(r.tags['zoomlevel_min'], rg.rg_tags['zoomlevel_min']) AS zoomlevel_min,
	-- prefer relation mcr_tags, fall back to rg's mcr_tags
	CAST(COALESCE(r.mcr_tags, rg.rg_mcr_tags) AS STRING) AS mcr_string,
	rg.geometry
FROM rg_filtered rg
JOIN pu_orbis_platform_prod_catalog.map_central_repository.relations r
	ON r.orbis_id = rg.orbis_id
WHERE
	-- keep only relations that explicitly indicate they are buildings or parts
	( r.tags['building'] IS NOT NULL OR r.tags['building:part'] IS NOT NULL )
	-- additional guard: ensure product/license also match on relation row (fast equality checks)
	AND r.product = 'nexventura_25430.000'
	AND r.license_zone LIKE '%DEU%'
;
