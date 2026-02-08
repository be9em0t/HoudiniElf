-- RUNT THIS FIRST - START HERE --
-- 1) Run the CREATE TEMP VIEW block below in a single editor execution (same session).
--    This will create `tmp_buildings_footprints` in your session and materialize
--    the parsed geometry and row numbers needed for safe paging and downloading.
-- 2) After the CREATE finishes, immediately run the verification SELECT to confirm
--    the view exists in your session: SELECT COUNT(*) FROM tmp_buildings_footprints;
-- FIRST - END --

CREATE OR REPLACE TEMP VIEW tmp_buildings_footprints AS
WITH
  q AS (
    SELECT
      ST_GeomFromWKT('POLYGON((4.8989181608163825 52.37447798249038, 4.8989181608163825 52.37745256399035, 4.904231380413285 52.37745256399035, 4.904231380413285 52.37447798249038, 4.8989181608163825 52.37447798249038))') AS qg,
      ST_Envelope(ST_GeomFromWKT('POLYGON((4.8989181608163825 52.37447798249038, 4.8989181608163825 52.37745256399035, 4.904231380413285 52.37745256399035, 4.904231380413285 52.37447798249038, 4.8989181608163825 52.37447798249038))')) AS qenv
  ),

  polys_src AS (
    SELECT orbis_id, product, license_zone, tags, building, geometry
    FROM pu_orbis_platform_prod_catalog.map_central_repository.polygons
    WHERE product = 'nexventura_26060.000'
      AND license_zone = 'NLD'
  ),

  polys_pre AS (
    SELECT
      p.orbis_id,
      p.product,
      p.license_zone,
      p.tags,
      p.building,
      ST_GeomFromWKT(p.geometry) AS g,
      ST_Envelope(ST_GeomFromWKT(p.geometry)) AS env
    FROM polys_src p
    WHERE (p.building = 'yes' OR p.tags['building'] IS NOT NULL OR p.tags['building:part'] IS NOT NULL)
      AND ST_Intersects((SELECT qenv FROM q), ST_Envelope(ST_GeomFromWKT(p.geometry)))
  ),

  polygons_out AS (
    SELECT
      NULL AS parent_relation_id,
      p.orbis_id AS orbis_id,
      p.tags AS tags,
      ST_ASTEXT(p.g) AS geometry,
      'outline' AS role,
      'polygons' AS source
    FROM polys_pre p
    WHERE p.building = 'yes'
  )

-- Create the TEMP VIEW with a stable row-number for safe paging (rn)
SELECT
  parent_relation_id,
  orbis_id,
  tags,
  geometry,
  role,
  source,
  row_number() OVER (ORDER BY orbis_id) AS rn
FROM polygons_out;

-- RUNT THIS SECOND - START HERE --
-- 1) Verify the TEMP VIEW exists in this session:
   SELECT COUNT(*) AS tmp_view_count FROM tmp_buildings_footprints;
-- 2) Paging / download flow (run these in the same session and export each result):
--    a) Check total rows: SELECT COUNT(*) FROM tmp_buildings_footprints;
--    b) First page (rows 1..10000): SELECT * FROM tmp_buildings_footprints WHERE rn > 0 AND rn <= 10000 ORDER BY rn;
--    c) Next page (rows 10001..20000): SELECT * FROM tmp_buildings_footprints WHERE rn > 10000 AND rn <= 20000 ORDER BY rn;
--    d) Repeat incrementing the rn ranges until a page returns zero rows.
-- 3) Optional cleanup: DROP VIEW tmp_buildings_footprints; when finished.
-- SECOND - END --

-- NOTE: The verification SELECT above (in the SECOND step) is the canonical executable check.
-- Run the entire script in one editor execution (same session) so the TEMP VIEW is available to verification and export steps.
-- =============================================================================
-- Paging / Download examples (use these after creating the temp view in the same session)
-- 1) Get total rows
--    SELECT COUNT(*) FROM tmp_buildings_footprints;
-- 2) First page (rows 1..10000)
--    SELECT * FROM tmp_buildings_footprints WHERE rn > 0 AND rn <= 10000 ORDER BY rn;
-- 3) Next page (rows 10001..20000)
--    SELECT * FROM tmp_buildings_footprints WHERE rn > 10000 AND rn <= 20000 ORDER BY rn;
-- 4) Continue incrementing the ranges until a page returns zero rows.
-- =============================================================================

-- DBeaver tips: run the CREATE VIEW and the page SELECTs in the same session. If you export from the result grid, use a small fetch size (Settings → Database → Result Sets → ResultSet fetch size = 2000) to avoid Thrift 404 errors.


-- RUNT THIS THIRD - START HERE --
-- EXPORT TEMP VIEW LOCALLY (DBeaver) — No storage write required.
-- This sequence assumes you have already created the TEMP VIEW above in the same session.
-- Use DBeaver's "Export Query" (streamed) to write results directly to a local CSV.

-- 1) Verify the view exists and size (optional):
SELECT COUNT(*) AS tmp_view_count FROM tmp_buildings_footprints;

-- 2) Download full contents (this is the query you should Export from DBeaver):
SELECT parent_relation_id, orbis_id, tags, geometry, role, source
FROM tmp_buildings_footprints
ORDER BY rn; -- ORDER BY rn ensures stable ordering for paging or reproducible exports

-- 3) DBeaver: Right-click the SQL editor -> Export query -> CSV -> choose file -> Start.
--    - Ensure you select the "Export query" (not export grid) or use the Export button in the result pane
--    - If you see a streaming or "Use SQL for data transfer" option, enable it (prevents loading all rows into the grid)
--    - If you hit fetch or Thrift errors retry with a smaller fetch size (Preferences → Database → Result Sets → ResultSet fetch size = 2000)

-- 4) OPTIONAL: If you prefer chunked export, use the rn paging queries described above and export each chunk separately.

-- THIRD - END --
  -- SELECT parent_relation_id, orbis_id, tags, geometry, role, source
  -- FROM tmp_buildings_footprints