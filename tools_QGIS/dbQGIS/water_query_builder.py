"""
Water Geometry Query Builder
Modular SQL generator with H3 or Polygon spatial filtering
"""

# Load the SQL template
with open('Natural Water Geometry (TEMPLATE - H3 or Polygon).sql', 'r') as f:
    SQL_TEMPLATE = f.read()


def build_h3_filter(h3_tiles):
    """
    Build H3-based spatial filter (fast, partition-aware)
    
    Args:
        h3_tiles: list of H3 index strings, e.g., ['88608b923dfffff', '88608b9a8bfffff']
    
    Returns:
        SQL filter clause
    """
    h3_list = "', '".join(h3_tiles)
    return f"AND h3_index IN ('{h3_list}')"


def build_polygon_filter(polygon_wkt):
    """
    Build polygon-based spatial filter (precise boundaries)
    
    Args:
        polygon_wkt: WKT polygon string
    
    Returns:
        SQL filter clause
    """
    return f"""AND ST_Intersects(
            ST_GeomFromWKT('{polygon_wkt}'),
            ST_GeomFromWKT(geometry)
          )"""


def generate_water_query(
    product='nexventura_26060.000',
    license_zone='AND',
    filter_mode='h3',  # 'h3' or 'polygon'
    h3_tiles=None,
    polygon_wkt=None
):
    """
    Generate optimized water geometry query
    
    Args:
        product: Product name
        license_zone: License zone code
        filter_mode: 'h3' or 'polygon'
        h3_tiles: List of H3 tiles (required if filter_mode='h3')
        polygon_wkt: WKT polygon (required if filter_mode='polygon')
    
    Returns:
        Executable SQL query string
    """
    
    # Generate spatial filter based on mode
    if filter_mode == 'h3':
        if not h3_tiles:
            raise ValueError("h3_tiles required for H3 filter mode")
        spatial_filter = build_h3_filter(h3_tiles)
    elif filter_mode == 'polygon':
        if not polygon_wkt:
            raise ValueError("polygon_wkt required for polygon filter mode")
        spatial_filter = build_polygon_filter(polygon_wkt)
    else:
        raise ValueError(f"Invalid filter_mode: {filter_mode}")
    
    # Build query from template
    query = SQL_TEMPLATE.replace('{PRODUCT}', product)
    query = query.replace('{LICENSE_ZONE}', license_zone)
    query = query.replace('{SPATIAL_FILTER_POLYGONS}', spatial_filter)
    query = query.replace('{SPATIAL_FILTER_RELATIONS}', spatial_filter)
    
    return query


# ==================== USAGE EXAMPLES ====================

if __name__ == '__main__':
    
    # Example 1: H3 mode (fast)
    print("=" * 60)
    print("EXAMPLE 1: H3 Filter Mode")
    print("=" * 60)
    
    h3_query = generate_water_query(
        product='nexventura_26060.000',
        license_zone='AND',
        filter_mode='h3',
        h3_tiles=[
            '88608b923dfffff',
            '88608b9a8bfffff',
            '88608b8f19fffff'
        ]
    )
    print(h3_query[:500], "...\n")
    
    
    # Example 2: Polygon mode (precise)
    print("=" * 60)
    print("EXAMPLE 2: Polygon Filter Mode")
    print("=" * 60)
    
    polygon_query = generate_water_query(
        product='nexventura_26060.000',
        license_zone='AND',
        filter_mode='polygon',
        polygon_wkt='POLYGON((1.633 42.492, 1.633 42.542, 1.703 42.542, 1.703 42.492, 1.633 42.492))'
    )
    print(polygon_query[:500], "...\n")
    
    
    # Example 3: Integration with your existing H3 function
    print("=" * 60)
    print("EXAMPLE 3: Using your polygon_to_h3_tiles() function")
    print("=" * 60)
    
    # Assuming you have this function:
    # def polygon_to_h3_tiles(polygon_wkt, resolution=8):
    #     """Your existing function that converts polygon to H3 tiles"""
    #     pass
    
    my_polygon = 'POLYGON((1.633 42.492, 1.633 42.542, 1.703 42.542, 1.703 42.492, 1.633 42.492))'
    
    # Get H3 tiles from your function
    # h3_tiles = polygon_to_h3_tiles(my_polygon, resolution=8)
    
    # Generate query with H3 filtering
    # query = generate_water_query(
    #     filter_mode='h3',
    #     h3_tiles=h3_tiles
    # )
    
    print("""
    # Typical workflow:
    polygon_wkt = get_my_bbox()  # Your bbox logic
    h3_tiles = polygon_to_h3_tiles(polygon_wkt, resolution=8)
    
    # Use H3 for speed (2.10s vs 1.58s on your server)
    query = generate_water_query(filter_mode='h3', h3_tiles=h3_tiles)
    
    # Or use polygon for precision at boundary edges
    query = generate_water_query(filter_mode='polygon', polygon_wkt=polygon_wkt)
    """)
