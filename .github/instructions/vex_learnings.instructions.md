---
applyTo: '**/*.vfl'
---
## Syntax and Declarations

### Arrays
- Declare arrays as `type name[]`, e.g., `int prims_curr[] = pointprims(geoself(), @ptnum);`
- Use functions like `append()`, `len()`, etc. for manipulation.

### Attributes
- Use type prefixes: `f@` for floats, `i@` for integers, `s@` for strings, `v@` for vectors.
- Read attributes: `type var = prefix@attr;`
- Write attributes: `prefix@attr = value;`
- For other points: `point(geometry, "attr", ptnum)`

## Key Functions

### Geometry and Attributes
- `geoself()`: Reference current geometry ([docs](https://www.sidefx.com/docs/houdini20.5/vex/functions/geoself.html))
- `pointprims(geometry, ptnum)`: Get primitives connected to a point ([docs](https://www.sidefx.com/docs/houdini20.5/vex/functions/pointprims.html))
- `point(geometry, "attr", ptnum)`: Get attribute value from another point
- `setpointattrib(geohandle, "attr", ptnum, value)`: Set attribute on a point ([docs](https://www.sidefx.com/docs/houdini20.5/vex/functions/setpointattrib.html))
- `npoints(geometry)`: Number of points in geometry ([docs](https://www.sidefx.com/docs/houdini20.5/vex/functions/npoints.html))

### Parameters and Measurements
- `chf("param")`: Get float parameter from node; check if > 0 for defaults ([docs](https://www.sidefx.com/docs/houdini20.5/vex/functions/chf.html))
- `distance(v1, v2)`: Euclidean distance between two vectors ([docs](https://www.sidefx.com/docs/houdini20.5/vex/functions/distance.html))

### Debugging
- `printf(format, ...)`: Print formatted output for debugging ([docs](https://www.sidefx.com/docs/houdini20.5/vex/functions/printf.html))

## Workflows

### Fusing Points in Chains
1. Assign `s@chain_id` and `i@order` via traversal.
2. Sort points by `chain_id`, then `order`.
3. Use Polypath with Group set to `chain_id`.
4. Fuse to merge close points within chains.

### Building Polylines from Attributes
- Sort points by chain attributes.
- Use Add SOP with "By Group" or custom wrangle to follow @next and create primitives.
- Note: Polypath lacks "Connect by Attribute" in Houdini 20.5.

## General Tips
- Use conditional assignment: `if (condition) attr = value;` to avoid overwriting.
- Generate unique pair IDs: `min_pt * npoints(0) + max_pt`
- Test code incrementally; verify function signatures in official docs.
- Always use `geoself()` instead of `0` for current geometry.