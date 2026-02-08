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

  -- Footprints-only output: pick polygons with building='yes' and relations with building tag
  polygons_out AS (
    SELECT
      NULL AS parent_relation_id,
      p.orbis_id AS orbis_id,
      p.tags AS tags,
      p.mcr_tags AS mcr_tags,
      ST_ASTEXT(p.g) AS geometry,
      'outline' AS role,
      'polygons' AS source
    FROM polys_pre p
    WHERE p.building = 'yes'
  ),

  relations_out AS (
    SELECT
      rg.orbis_id AS parent_relation_id,
      rg.orbis_id AS orbis_id,
      rg.rg_tags AS tags,
      rg.rg_mcr_tags AS mcr_tags,
      ST_ASTEXT(rg.g) AS geometry,
      'outline' AS role,
      'relations_geometries' AS source
    FROM rg_pre rg
    WHERE rg.rg_tags['building'] IS NOT NULL
  )

-- Final output: footprints only (polygons with building='yes' and relation geometries with building tag)
SELECT * FROM polygons_out
UNION ALL
SELECT * FROM relations_out
ORDER BY source, parent_relation_id NULLS FIRST, orbis_id;