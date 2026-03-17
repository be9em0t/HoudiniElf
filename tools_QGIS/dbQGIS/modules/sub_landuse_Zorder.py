from collections import deque

layer = iface.activeLayer()
assert layer is not None, "Select your landuse polygon layer first"

# Step 1: discover connected overlap clusters and assign each a stable ID.
# Create a field to store the cluster ID (only >1-member clusters get an ID; singles get -1).
cluster_field = "cluster_id"
if cluster_field not in [f.name() for f in layer.fields()]:
    layer.dataProvider().addAttributes([QgsField(cluster_field, QVariant.Int)])
    layer.updateFields()

# Optional: keep z_order if you want to do Task 2 later
z_field = "z_order"
if z_field not in [f.name() for f in layer.fields()]:
    layer.dataProvider().addAttributes([QgsField(z_field, QVariant.Int)])
    layer.updateFields()

# Read all features once (avoid multiple provider hits)
features = list(layer.getFeatures())

# Build spatial index from full feature list
index = QgsSpatialIndex()
for f in features:
    index.addFeature(f)

# Cache geometries, areas, and bounding boxes (to avoid recomputing)
geoms = {f.id(): f.geometry() for f in features}
areas = {fid: g.area() for fid, g in geoms.items()}
bboxes = {fid: g.boundingBox() for fid, g in geoms.items()}

# Union-Find (Disjoint Set) for overlap groups
parent = {f.id(): f.id() for f in features}
# Track actual overlap edges (undirected) so we can build z-order layers later
overlaps = {f.id(): set() for f in features}

def find(u):
    while parent[u] != u:
        parent[u] = parent[parent[u]]
        u = parent[u]
    return u

def union(u, v):
    ru, rv = find(u), find(v)
    if ru != rv:
        parent[rv] = ru

# Find overlaps (bbox + precise intersect check)
# Note: QgsGeometry.prepareGeometry() may not exist in all QGIS builds, so fall back to direct intersects.
use_prepared = hasattr(QgsGeometry, 'prepareGeometry')
for f in features:
    fid = f.id()
    geom = geoms[fid]
    bbox = bboxes[fid]
    candidates = index.intersects(bbox)

    if use_prepared:
        prepared = geom.prepareGeometry()

    # Only check candidates with higher IDs to avoid redundant work
    for c in candidates:
        if c <= fid:
            continue

        already_in_same_cluster = (find(fid) == find(c))

        # Extra quick filter: bbox check before full geometry intersect
        if not bbox.intersects(bboxes[c]):
            continue

        # Treat as overlap only if intersection area is > 0 (touching-only doesn't count).
        # This is the most robust definition for “proper overlap”.
        inter = geom.intersection(geoms[c])
        overlaps_test = (inter is not None) and (inter.area() > 0)

        if overlaps_test:
            if not already_in_same_cluster:
                union(fid, c)
            overlaps[fid].add(c)
            overlaps[c].add(fid)

# Group features by connected-component root
groups = {}
for fid in parent:
    root = find(fid)
    groups.setdefault(root, []).append(fid)

# Build cluster assignment (task 1)
# Each overlap-connected group (size > 1) gets a cluster ID.
cluster_vals = {}
cluster_id_by_root = {}
cluster_counter = 0

for root, members in groups.items():
    if len(members) <= 1:
        for fid in members:
            cluster_vals[fid] = -1
        continue

    cluster_id_by_root[root] = cluster_counter
    for fid in members:
        cluster_vals[fid] = cluster_counter
    cluster_counter += 1

# Write back cluster_id (so you can inspect clusters in the attribute table)
with edit(layer):
    field_idx = layer.fields().indexOf(cluster_field)
    for fid, cid in cluster_vals.items():
        layer.changeAttributeValue(fid, field_idx, cid)

# Task 2: Compute z_order for each cluster.
# Option A: strict layering based on overlap chains (longest path) – can produce high z values for long chains.
# Option B: compressed layering so non-overlapping siblings can share z levels (greedy coloring).
compress_z = True

z_order_vals = {fid: -1 for fid in cluster_vals}

# Build reverse mapping: cluster_id -> member fids (excluding -1)
clusters = {}
for fid, cid in cluster_vals.items():
    if cid < 0:
        continue
    clusters.setdefault(cid, []).append(fid)

for cid, members in clusters.items():
    members_set = set(members)

    if compress_z:
        # Greedy coloring: assign the smallest z not used by any overlapping neighbor already assigned.
        # We process larger polygons first so they get lower z values where possible.
        ordered = sorted(members, key=lambda f: (-areas.get(f, 0.0), f))
        assigned = {}
        for fid in ordered:
            used = {assigned[n] for n in overlaps[fid] if n in assigned and n in members_set}
            z = 0
            while z in used:
                z += 1
            assigned[fid] = z
            z_order_vals[fid] = z

    else:
        # Build directed acyclic graph where edges go from larger->smaller (tie-break on fid).
        indegree = {fid: 0 for fid in members}
        out_edges = {fid: [] for fid in members}

        for fid in members:
            for nb in overlaps[fid]:
                if nb not in members_set:
                    continue
                if fid == nb:
                    continue
                if areas.get(fid, 0.0) > areas.get(nb, 0.0) or (areas.get(fid, 0.0) == areas.get(nb, 0.0) and fid < nb):
                    out_edges[fid].append(nb)
                    indegree[nb] += 1
                else:
                    out_edges[nb].append(fid)
                    indegree[fid] += 1

        # Assign z_orders using topological layering (Kahn's algorithm)
        q = deque([fid for fid, deg in indegree.items() if deg == 0])
        for fid in q:
            z_order_vals[fid] = 0

        while q:
            u = q.popleft()
            for v in out_edges[u]:
                z_order_vals[v] = max(z_order_vals[v], z_order_vals[u] + 1)
                indegree[v] -= 1
                if indegree[v] == 0:
                    q.append(v)

        # Fallback in case of cycles (should not happen with the tie-breaker): sort by area.
        if any(deg > 0 for deg in indegree.values()):
            members_sorted = sorted(members, key=lambda f: (-areas.get(f, 0.0), f))
            for z_idx, fid in enumerate(members_sorted):
                z_order_vals[fid] = z_idx

# Write z_order back to the attribute table
with edit(layer):
    z_idx = layer.fields().indexOf(z_field)
    for fid, z in z_order_vals.items():
        layer.changeAttributeValue(fid, z_idx, z)

print(f"Done. Found {cluster_counter} overlap clusters; stored IDs in '{cluster_field}' and z-orders in '{z_field}'.")