-- H3-only candidate selection (minimal & fast)
-- Uses the bbox POLYGON defined below and the precomputed bbox H3 cells (inline from bbox_h3.csv)
-- This does an equality join on stored H3 index + resolution to avoid missing geometries.
-- If you later load the CSV into a table `tmp_bbox_h3`, use that table instead (see commented snippet).

WITH bbox AS (
    SELECT ST_GeomFromWKT('POLYGON((4.735068050022468 52.28356208446593, 4.735068050022468 52.444067788712985, 5.048224865164012 52.444067788712985, 5.048224865164012 52.28356208446593, 4.735068050022468 52.28356208446593))') AS geom
),

polygons_geom AS (
    SELECT
        *,
        ST_GeomFromWKT(geometry) AS g
    FROM pu_orbis_platform_prod_catalog.map_central_repository.polygons
),

relevant_polygons AS (
    SELECT *
    FROM polygons_geom p
    WHERE (p.tags['building'] = 'yes' OR p.tags['building'] IS NOT NULL OR p.tags['building:part'] IS NOT NULL)
      AND p.product = 'nexventura_26060.000'
      AND p.license_zone LIKE '%NLD%'
),

-- Inline bbox H3 cells (expanded with parents; generated from polygon WKT)
bbox_h3 AS (
    SELECT * FROM (VALUES
        -- <=====paste h3 tiles here=======>
        -- <=====generated with h3_python.py=======>

    ) AS t(h3, h3_resolution)
)

SELECT DISTINCT
    p.orbis_id,
    p.tags['layer'] as layer,
    p.tags['type'] as type,
    p.tags['building'] as building,
    p.tags['building:part'] as part,
    p.tags['height'] as height,
    p.tags['min_height'] as min_height,
    p.tags['building:levels'] as levels,
    p.tags['building:min_level'] as min_level,
    p.tags['location'] as location,
    p.tags['construction'] as construction,
    p.tags['zoomlevel_min'] as zoomlevel_min,
    p.geometry
FROM relevant_polygons p
JOIN bbox_h3 bh
  ON p.h3_index = bh.h3
  AND CAST(p.h3_resolution AS INT) = CAST(bh.h3_resolution AS INT)
ORDER BY p.orbis_id;

-- If you uploaded bbox_h3.csv into a Databricks table `tmp_bbox_h3`, use this instead of the inline CTE above:
-- bbox_h3 AS (SELECT h3, CAST(h3_resolution AS INT) AS h3_resolution FROM tmp_bbox_h3)

-- Optional safety refinement (recommended if you care about exact boundary behavior):
-- Wrap the SELECT above in a CTE `candidates` and then run:
-- SELECT * FROM candidates WHERE ST_Intersects(bbox.geom, ST_GeomFromWKT(candidates.geometry));

-- Notes:
-- • This H3-only join is extremely fast and should not MISS polygons whose stored h3_index + resolution match the bbox tiles.
-- • If polygons are stored at different resolutions (coarser/finer) than the bbox tiles, consider generating parent/child cells and adding them to `bbox_h3` to prevent misses.
