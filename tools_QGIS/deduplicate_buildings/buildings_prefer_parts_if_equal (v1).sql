-- Buildings extraction: prefer parts when they fully cover the outline
-- Policy: If the ST_Union of parts for a Building relation equals (or is very close to) the Building outline,
-- then return the individual parts (as rows). Otherwise return the outline geometry.
-- Parts are returned as individual rows with a parent_relation_id so downstream tools can choose.
--
-- NOTE: replace the bbox, product and license filters as required for your run.
-- EXPLAIN EXTENDED
WITH
  -- bbox/query geometry (replace the WKT with your extent)
  q AS (
    SELECT
      ST_GeomFromWKT('POLYGON((4.8989181608163825 52.37447798249038, 4.8989181608163825 52.37745256399035, 4.904231380413285 52.37745256399035, 4.904231380413285 52.37447798249038, 4.8989181608163825 52.37447798249038))') AS qg,
      ST_Envelope(ST_GeomFromWKT('POLYGON((4.8989181608163825 52.37447798249038, 4.8989181608163825 52.37745256399035, 4.904231380413285 52.37745256399035, 4.904231380413285 52.37447798249038, 4.8989181608163825 52.37447798249038))')) AS qenv
  ),

  -- Candidate polygons (building or building:part) parsed once
  polys_pre AS (
    SELECT
      p.orbis_id,
      p.product,
      p.license_zone,
      p.tags,
      p.mcr_tags,
      p.geometry,
      ST_GeomFromWKT(p.geometry) AS g,
      ST_Envelope(ST_GeomFromWKT(p.geometry)) AS env
    FROM pu_orbis_platform_prod_catalog.map_central_repository.polygons p
    WHERE (p.building = 'yes' OR p.tags['building'] IS NOT NULL OR p.tags['building:part'] IS NOT NULL)
      AND p.product = 'nexventura_26060.000'
      AND p.license_zone = 'NLD'
      -- only polygons within bbox envelope to avoid parsing everything
      AND ST_Intersects((SELECT qenv FROM q), ST_Envelope(ST_GeomFromWKT(p.geometry)))
  ),

  -- Candidate relation geometries (polygons/multipolygons) parsed once
  rg_pre AS (
    SELECT
      rg.orbis_id,
      rg.product,
      rg.license_zone,
      rg.tags AS rg_tags,
      rg.mcr_tags AS rg_mcr_tags,
      rg.geom_type,
      rg.geometry,
      ST_GeomFromWKT(regexp_replace(rg.geometry, '^SRID=[0-9]+;', '')) AS g,
      ST_Envelope(ST_GeomFromWKT(regexp_replace(rg.geometry, '^SRID=[0-9]+;', ''))) AS env
    FROM pu_orbis_platform_prod_catalog.map_central_repository.relations_geometries rg
    WHERE rg.geom_type IN ('ST_POLYGON','ST_MULTIPOLYGON')
      AND rg.product = 'nexventura_26060.000'
      AND rg.license_zone = 'NLD'
      AND (
        rg.tags['building'] IS NOT NULL
        OR rg.tags['building:part'] IS NOT NULL
      )
      AND ST_Intersects((SELECT qenv FROM q), ST_Envelope(ST_GeomFromWKT(regexp_replace(rg.geometry, '^SRID=[0-9]+;', ''))))
  ),

  -- Relations that look like buildings (by tags or members)
  rels_pre AS (
    SELECT
      r.orbis_id AS rel_id,
      r.tags,
      r.mcr_tags,
      r.members,
      r.product,
      r.license_zone
    FROM pu_orbis_platform_prod_catalog.map_central_repository.relations r
    WHERE (
      r.tags['building'] IS NOT NULL
      OR r.tags['building:part'] IS NOT NULL
      OR SIZE(FILTER(r.members, x -> x.role = 'outline')) > 0
      OR SIZE(FILTER(r.members, x -> x.role = 'part')) > 0
    )
    AND r.product = 'nexventura_26060.000'
    AND r.license_zone = 'NLD'
  ),

  -- Extract member ids per relation (outline id and part ids array)
  rel_members AS (
    SELECT
      rel_id,
      tags,
      mcr_tags,
      product,
      license_zone,
      -- outline member id (if any)
      CASE WHEN SIZE(FILTER(members, x -> x.role = 'outline')) > 0
        THEN (FILTER(members, x -> x.role = 'outline')[0]).id
        ELSE NULL
      END AS outline_member_id,
      -- array of member ids with role = 'part'
      TRANSFORM(FILTER(members, x -> x.role = 'part'), x -> x.id) AS part_ids
    FROM rels_pre
  ),

  -- Parts geometries per relation (join polygons by member id)
  parts_per_rel AS (
    SELECT
      rm.rel_id,
      p.orbis_id AS part_orbis_id,
      p.tags AS part_tags,
      p.mcr_tags AS part_mcr_tags,
      p.g AS part_g
    FROM rel_members rm
    JOIN polys_pre p
      ON array_contains(rm.part_ids, p.orbis_id)
  ),

  -- Outline geometry per relation: prefer explicit outline member polygon if present, else fall back to relations_geometries assembled geom
  outline_geom AS (
    SELECT
      rm.rel_id,
      -- outline from member polygon if present
      op.g AS outline_from_member,
      rg.g AS outline_from_relgeom,
      COALESCE(op.g, rg.g) AS outline_g
    FROM rel_members rm
    LEFT JOIN polys_pre op
      ON op.orbis_id = rm.outline_member_id
    LEFT JOIN rg_pre rg
      ON rg.orbis_id = rm.rel_id
  ),

  -- Aggregated parts geometry using available aggregate function `st_union_agg`.
  -- This is preferred when the DB supports it (more robust than area-sum heuristics).
  -- If `st_union_agg` is unavailable or permission-restricted, revert to the heuristic
  -- (parts_stats + containment checks) implemented previously.
  parts_union AS (
    SELECT
      rel_id,
      st_union_agg(part_g) AS parts_g
    FROM parts_per_rel
    GROUP BY rel_id
  ),

  -- Decision: prefer parts when their union equals (or area-diff small) the outline
  decision AS (
    SELECT
      o.rel_id,
      o.outline_g,
      pu.parts_g,
      CASE
        WHEN pu.parts_g IS NOT NULL AND o.outline_g IS NOT NULL AND (
          st_equals(pu.parts_g, o.outline_g)
          OR ABS(st_area(pu.parts_g) - st_area(o.outline_g)) / NULLIF(st_area(o.outline_g), 0) < 1e-6
        ) THEN TRUE
        ELSE FALSE
      END AS prefer_parts
    FROM outline_geom o
    LEFT JOIN parts_union pu ON pu.rel_id = o.rel_id
  ),

  -- Parts to emit (for relations where prefer_parts = TRUE)
  emit_parts AS (
    SELECT
      p.rel_id AS parent_relation_id,
      p.part_orbis_id AS orbis_id,
      p.part_tags AS tags,
      p.part_mcr_tags AS mcr_tags,
      ST_ASTEXT(p.part_g) AS geometry,
      'part' AS role,
      'polygons' AS source
    FROM parts_per_rel p
    JOIN decision d ON d.rel_id = p.rel_id AND d.prefer_parts = TRUE
  ),

  -- Outlines to emit (for relations where prefer_parts = FALSE)
  emit_outlines AS (
    SELECT
      d.rel_id AS relation_id,
      d.rel_id AS orbis_id,
      r.tags AS tags,
      r.mcr_tags AS mcr_tags,
      ST_ASTEXT(d.outline_g) AS geometry,
      'outline' AS role,
      'relations' AS source
    FROM decision d
    JOIN pu_orbis_platform_prod_catalog.map_central_repository.relations r
      ON r.orbis_id = d.rel_id
    WHERE d.prefer_parts = FALSE
  ),

  -- Polygons not covered by any building relation geometry (keep standalone polygons)
  polygons_pref AS (
    SELECT
      p.orbis_id,
      p.tags,
      p.mcr_tags,
      ST_ASTEXT(p.g) AS geometry,
      'outline' AS role,
      'polygons' AS source
    FROM polys_pre p
    WHERE NOT EXISTS (
      SELECT 1 FROM rg_pre rg WHERE ST_Intersects(p.g, rg.g)
    )
  )

-- Final output: parts (where preferred), outlines from relations (where parts not preferred), and standalone polygons
SELECT * FROM emit_parts
UNION ALL
SELECT
  relation_id AS parent_relation_id,
  orbis_id,
  tags,
  mcr_tags,
  geometry,
  role,
  source
FROM emit_outlines
UNION ALL
SELECT
  NULL AS parent_relation_id,
  orbis_id,
  tags,
  mcr_tags,
  geometry,
  role,
  source
FROM polygons_pref
ORDER BY source, parent_relation_id NULLS FIRST, orbis_id;