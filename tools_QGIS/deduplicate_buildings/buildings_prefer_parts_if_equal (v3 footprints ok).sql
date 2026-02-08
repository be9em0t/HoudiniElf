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
      p.building,
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
  )

-- Final output: footprints only (polygons with building='yes')
SELECT * FROM polygons_out
ORDER BY source, parent_relation_id NULLS FIRST, orbis_id;