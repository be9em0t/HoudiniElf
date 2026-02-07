WITH
q AS (
  SELECT
    ST_GeomFromWKT('POLYGON((4.689851292704134 52.26897277133037, 4.689851292704134 52.43802048721305, 5.09170592463983 52.43802048721305, 5.09170592463983 52.26897277133037, 4.689851292704134 52.26897277133037))') AS qg,
    ST_Envelope(ST_GeomFromWKT('POLYGON((4.689851292704134 52.26897277133037, 4.689851292704134 52.43802048721305, 5.09170592463983 52.43802048721305, 5.09170592463983 52.26897277133037, 4.689851292704134 52.26897277133037))')) AS qenv
),
polys_pre AS (
  SELECT
    p.*,
    ST_GeomFromWKT(p.geometry) AS g
  FROM pu_orbis_platform_prod_catalog.map_central_repository.polygons p
  WHERE p.product = 'nexventura_26060.000'
    AND p.license_zone = 'NLD'
    AND p.tags['natural'] = 'water'
    AND p.element_type != 'RELATION'
    AND p.geom_type IN ('ST_POLYGON', 'ST_MULTIPOLYGON')
),
polys_spatial_filtered AS (
  SELECT
    'polygons' AS source,
    p.product,
    p.element_type,
    p.osm_identifier,
    p.license_zone,
    p.tags,
    p.g,
    ST_Envelope(p.g) AS env,
    p.geometry
  FROM polys_pre p
  CROSS JOIN q
  WHERE ST_Intersects(ST_Envelope(p.g), q.qenv)        -- cheap bbox prefilter
    AND ST_Intersects(q.qg, p.g)            -- final exact check
),
rels_pre AS (
  SELECT
    r.*,
    ST_GeomFromWKT(r.geometry) AS g
  FROM pu_orbis_platform_prod_catalog.map_central_repository.relations_geometries r
  WHERE r.product = 'nexventura_26060.000'
    AND r.license_zone = 'NLD'
    AND r.tags['natural'] = 'water'
    AND r.geom_type IN ('ST_POLYGON', 'ST_MULTIPOLYGON')
),
rels_spatial_filtered AS (
  SELECT
    'relations_geometries' AS source,
    r.product,
    r.element_type,
    r.osm_identifier,
    r.license_zone,
    r.tags,
    r.g,
    ST_Envelope(r.g) AS env,
    r.geometry
  FROM rels_pre r
  CROSS JOIN q
  WHERE ST_Intersects(ST_Envelope(r.g), q.qenv)
    AND ST_Intersects(q.qg, r.g)
),
combined_filtered AS (
  SELECT * FROM polys_spatial_filtered
  UNION ALL
  SELECT * FROM rels_spatial_filtered
)
SELECT 
  c.source,
  c.product,
  c.element_type,
  c.osm_identifier,
  c.license_zone,
  c.tags['natural'] AS natural,
  c.tags['water'] AS water,
  c.tags['intermittent'] AS intermittent,
  c.tags['bridge'] AS bridge,
  c.tags['tunnel'] AS tunnel,
  c.tags['name'] AS name,
  c.tags['alt_name'] AS alt_name,
  CAST(c.tags AS STRING) AS tags,
  c.geometry
FROM combined_filtered c
ORDER BY c.product, c.source, c.osm_identifier;