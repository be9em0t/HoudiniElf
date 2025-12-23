WITH lines AS (
  SELECT *, ST_GeomFromWKT(geometry) AS g FROM lines_table
)
SELECT *
FROM lines
WHERE ST_Area(g) > 1000