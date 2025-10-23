---
applyTo: '**/*.vfl'
---
# VEX_PROMPT_KB
# Compact, machine-oriented rules and snippets for automated edits

EXPORT_PARAM: "export vector a"  # do NOT use '&'
FUNC_CAPTURE: "no"  # functions don't capture outer scope; pass arrays explicitly
FUNC_MUTATE_PARAM: "export int arr[]"  # use export to mutate caller array

APPEND_AMBIGUITY: true
APPEND_FIX_TEMP: "tmp = point(...); append(arr, tmp);"

NESTED_ARRAYS: avoid ambiguous append(outer, inner)
NESTED_FIX1: "idx=len(outer); resize(outer, idx+1); outer[idx]=inner;"
NESTED_FIX2: "flatten: flat[], offs[], lens[]; append values; record offs/lens"
NESTED_AVOID_RESIZE: "avoid resize() on nested arrays (int[][]); use explicit resize+assign or linked-list (head/next) for adjacency buckets"
NESTED_UPUSH: "upush() is safe for flat arrays, but ambiguous for nested arrays; prefer resize+assign for int[][]"
ADJACENCY_LIST: "for bucket grouping, prefer head[]/next[] linked-list pattern to avoid nested array resizing"

NO_SLICE_SYNTAX: true
SLICE_FIX: "for(i=a;i<b;++i) append(sub, arr[i]);"

SAFE_ATOI: true
SAFE_ATOI_RULES: "empty->-1, non-numeric->SENTINEL(2147483647), use validator then atoi"
SENTINEL: 2147483647
ROOT_MARKER: -1

PRIM_ATTR_DEFAULT: "addprimattrib(0, 'new_id', -1)"
SET_PRIM_ATTR: "setprimattrib(0, 'new_id', prim, val, 'set')"
PREFER_SETPRIMATTR: true

COPY_POINT_ATTR_PATTERN: |
  if (haspointattrib(0, 'trips')) {
    string v = point(0, 'trips', src_pt);
    setpointattrib(0, 'trips', newpt, v, 'set');
  }

DEBUG_PRINT: "warning(sprintf(...)) or printf"
GEO_HANDLE: geoself()  # prefer over literal 0
MAX_ITER_PARAM: chi('maxIter')  # safety guard
MIN_THRESHOLD_PARAM: chf('MinThreshold')

ATTRIBUTE_PREFIXES: "use s@, i@, f@, v@ when using @-shorthand; Houdini won't guess types"
ATTR_CAST_EXAMPLE: "int id = atoi(s@id); // or float v = atof(s@val);"

NO_PRIMNUM_FUNC: "primnum is not a valid VEX function; use explicit primitive indices or primpoints/prim/vertex functions."

# End of compact KB