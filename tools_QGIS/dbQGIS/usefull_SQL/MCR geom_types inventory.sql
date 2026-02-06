-- Inventory of geometry types across MCR tables
-- This helps determine which geom_type values to filter on for optimization

SELECT 
    'polygons' AS table_name,
    geom_type,
    COUNT(*) AS count
FROM pu_orbis_platform_prod_catalog.map_central_repository.polygons
WHERE product = 'nexventura_26060.000'
  AND license_zone = 'AND'
GROUP BY geom_type

UNION ALL

SELECT 
    'relations_geometries' AS table_name,
    geom_type,
    COUNT(*) AS count
FROM pu_orbis_platform_prod_catalog.map_central_repository.relations_geometries
WHERE product = 'nexventura_26060.000'
  AND license_zone = 'AND'
GROUP BY geom_type

UNION ALL

SELECT 
    'lines' AS table_name,
    geom_type,
    COUNT(*) AS count
FROM pu_orbis_platform_prod_catalog.map_central_repository.lines
WHERE product = 'nexventura_26060.000'
  AND license_zone = 'AND'
GROUP BY geom_type

UNION ALL

SELECT 
    'points' AS table_name,
    geom_type,
    COUNT(*) AS count
FROM pu_orbis_platform_prod_catalog.map_central_repository.points
WHERE product = 'nexventura_26060.000'
  AND license_zone = 'AND'
GROUP BY geom_type

UNION ALL

SELECT 
    'relations' AS table_name,
    geom_type,
    COUNT(*) AS count
FROM pu_orbis_platform_prod_catalog.map_central_repository.relations
WHERE product = 'nexventura_26060.000'
  AND license_zone = 'AND'
GROUP BY geom_type

ORDER BY table_name, geom_type;
