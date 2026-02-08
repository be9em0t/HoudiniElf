-- buildings_TempView Tools
-- Utilities for paging / downloading a TEMP VIEW named `tmp_buildings_footprints` in chunks.
-- Replace `tmp_buildings_footprints` with your view name if different.

-- 1) Get total number of rows (cheap)
-- Run this once to see how many pages you need:
SELECT COUNT(*) AS total_rows
FROM tmp_buildings_footprints;

-- 2) Download first N rows (page size = 10000)
-- Export the resultset from your client (DBeaver) to CSV.
SELECT *
FROM tmp_buildings_footprints
ORDER BY orbis_id
LIMIT 10000;

-- 3) Download subsequent pages using the last orbis_id from the previous page
-- After downloading page 1, take the last_orbis_id from the last row and paste it below.
-- Repeat until a page returns zero rows.
-- Example (replace 'LAST_ORBIS_ID' with the actual value):
SELECT *
FROM tmp_buildings_footprints
WHERE orbis_id > 'LAST_ORBIS_ID'
ORDER BY orbis_id
LIMIT 10000;

-- 4) Alternative: page by row-number ranges (use only if orbis_id is non-monotonic)
-- Page 1 (rows 1..10000):
WITH numbered AS (
  SELECT *, row_number() OVER (ORDER BY orbis_id) AS rn
  FROM tmp_buildings_footprints
)
SELECT *
FROM numbered
WHERE rn > 0 AND rn <= 10000;

-- Page 2 (rows 10001..20000):
WITH numbered AS (
  SELECT *, row_number() OVER (ORDER BY orbis_id) AS rn
  FROM tmp_buildings_footprints
)
SELECT *
FROM numbered
WHERE rn > 10000 AND rn <= 20000;

-- 5) Helpful queries for monitoring / debugging
-- Show min/max orbis_id for bounding
SELECT MIN(orbis_id) AS min_id, MAX(orbis_id) AS max_id
FROM tmp_buildings_footprints;

-- Check if orbis_id ordering is stable (quick sample)
SELECT orbis_id FROM tmp_buildings_footprints ORDER BY orbis_id LIMIT 20;

-- 6) DBeaver export tips
-- - Run one page query at a time.
-- - Right-click results → Export resultset → CSV (choose file and options).
-- - In Settings (Preferences → Database → Result Sets) reduce fetch size to e.g. 2000 if you hit Thrift 404.

-- 7) Optional: automatic chunking using SQL + client scripting (bash + databricks-sql-cli or JDBC)
-- Provide a small pseudo-script if you want automation (I can write it for you).