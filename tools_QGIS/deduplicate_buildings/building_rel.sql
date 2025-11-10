
	-- Simpler: follow spec guidance to prefer relation-member geometry over non-relation geometry
	-- without heavy geometry subtraction. We annotate each polygon with a simple relation-member
	-- flag (based on tags or mcr_tags text) and then drop non-relation polygons that overlap
	-- any relation-member polygon. This avoids expensive ST_Union/ST_Difference operations.

	WITH bbox AS (
		SELECT ST_GEOMFROMWKT('POLYGON((-122.67972065432046 37.23185671657168, -122.67972065432046 37.89752375717992, -121.74739582907726 37.89752375717992, -121.74739582907726 37.23185671657168, -122.67972065432046 37.23185671657168))') AS geom
	),
	raw AS (
		SELECT 
			orbis_id,
			tags,
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
			geometry,
			ST_GEOMFROMWKT(geometry) AS geom
		FROM pu_orbis_platform_prod_catalog.map_central_repository.polygons
		WHERE ( tags['building'] IS NOT NULL OR tags['building:part'] IS NOT NULL OR building = 'yes' )
		  AND ST_Intersects((SELECT geom FROM bbox), ST_GEOMFROMWKT(geometry))
		AND product = 'nexventura_25430.000'
		AND license_zone like '%USA%'
	),
	annotated AS (
		-- Mark which polygons are explicitly building parts and which appear to be relation-member geometry.
		-- Relation membership detection is conservative: check for an explicit tag or appearance in mcr_tags text.
		SELECT
			orbis_id,
			tags,
			layer,
			type,
			building,
			part,
			height,
			min_height,
			levels,
			min_level,
			location,
			construction,
			zoomlevel_min,
			mcr_string,
			geometry,
			geom,
			(part IS NOT NULL) AS is_part,
			(
				tags['relation'] IS NOT NULL
				OR tags['member'] IS NOT NULL
				OR lower(mcr_string) LIKE '%relation%'
				OR lower(mcr_string) LIKE '%relid%'
			) AS is_relation_member
		FROM raw
	),
	-- Precompute relation-member geometries (should be small) and use anti-join to drop
	-- non-relation polygons that intersect any relation-member polygon. This avoids
	-- a correlated EXISTS and repeated ST_Intersects evaluations which are expensive.
	relation_geoms AS (
		SELECT orbis_id AS rel_orbis_id, geom
		FROM annotated
		WHERE is_relation_member = true
	),

	filtered_relation AS (
		-- keep all relation-member polygons
		SELECT * FROM annotated WHERE is_relation_member = true
	),

	filtered_nonrelation AS (
		-- keep non-relation polygons that do NOT intersect any relation-member polygon
		SELECT a.*
		FROM annotated a
		LEFT ANTI JOIN relation_geoms r
		  ON ST_Intersects(a.geom, r.geom)
		WHERE a.is_relation_member = false
	),

	filtered AS (
		SELECT * FROM filtered_relation
		UNION ALL
		SELECT * FROM filtered_nonrelation
	)

	-- Final output: everything left after filtering. Downstream consumers can use `is_part` and `is_relation_member`.
	SELECT
		orbis_id,
		tags,
		layer,
		type,
		building,
		part,
		height,
		min_height,
		levels,
		min_level,
		location,
		construction,
		zoomlevel_min,
		mcr_string,
		is_part,
		is_relation_member,
		geometry
	FROM filtered
	LIMIT 10;
	