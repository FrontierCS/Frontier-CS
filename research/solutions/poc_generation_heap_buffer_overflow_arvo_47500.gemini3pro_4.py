import os
import sys
import subprocess
import tempfile
import shutil
import tarfile
import random
import time
import concurrent.futures

def run_fuzz_case(args):
    bin_path, data = args
    if not data:
        return None
    
    tpath = None
    try:
        fd, tpath = tempfile.mkstemp(suffix='.j2k')
        os.write(fd, data)
        os.close(fd)
        
        # Run binary with ASAN
        # We expect a crash (non-zero return code) with ASAN message in stderr
        proc = subprocess.run(
            [bin_path, '-i', tpath, '-o', os.devnull],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=0.5, # Fast execution check
            close_fds=True
        )
        
        if proc.returncode != 0:
            if b"AddressSanitizer" in proc.stderr or b"Sanitizer" in proc.stderr:
                try:
                    os.unlink(tpath)
                except:
                    pass
                return data
                
    except Exception:
        pass
        
    if tpath and os.path.exists(tpath):
        try:
            os.unlink(tpath)
        except:
            pass
    return None

class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp()
        
        try:
            # Extract source code
            try:
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=work_dir)
            except Exception:
                # Fallback if detection fails, though usually works
                pass

            src_root = work_dir
            for root, dirs, files in os.walk(work_dir):
                if 'CMakeLists.txt' in files:
                    src_root = root
                    break
            
            build_dir = os.path.join(src_root, 'build_fuzz')
            os.makedirs(build_dir, exist_ok=True)
            
            # Configure and Build with ASAN
            # Requires cmake and a compiler (gcc/clang)
            cmd_cmake = [
                'cmake',
                '-DCMAKE_BUILD_TYPE=Release',
                '-DCMAKE_C_FLAGS=-fsanitize=address -g',
                '-DCMAKE_CXX_FLAGS=-fsanitize=address -g',
                '-DBUILD_SHARED_LIBS=OFF',
                '-DBUILD_CODEC=ON',
                '-DBUILD_PKGCONFIG_FILES=OFF',
                '-DBUILD_TESTING=OFF',
                '..'
            ]
            
            try:
                subprocess.run(cmd_cmake, cwd=build_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                
                n_jobs = str(os.cpu_count() or 4)
                subprocess.run(['make', '-j', n_jobs], cwd=build_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            except subprocess.CalledProcessError:
                # If build fails, we can't fuzz properly, return a dummy seed
                pass
            
            bin_path = None
            for root, dirs, files in os.walk(build_dir):
                if 'opj_decompress' in files:
                    bin_path = os.path.join(root, 'opj_decompress')
                    break
            
            if not bin_path:
                # Fallback to standard location
                possible = os.path.join(build_dir, 'bin', 'opj_decompress')
                if os.path.exists(possible):
                    bin_path = possible

            # Collect Seeds
            seeds = []
            for root, dirs, files in os.walk(src_root):
                for f in files:
                    if f.endswith('.j2k') or f.endswith('.jp2') or f.endswith('.j2c'):
                        seeds.append(os.path.join(root, f))
            
            seed_data = []
            for s in seeds:
                try:
                    with open(s, 'rb') as f:
                        d = f.read()
                        if len(d) < 100000: # Limit size
                            seed_data.append(d)
                except:
                    pass
            
            # Synthetic Fallback Seed (Minimal J2K)
            synthetic = bytes.fromhex(
                "FF4FFF51002F00000000008000000080000000000000000000000000000100000000000000000000000000000000"
                "FF52000C00000001010504040001"
                "FF5C001320909898A0A8A8B0B8B8C0C8C8D0D8D8"
                "FF90000A0000000000000001FF93FFD9"
            )
            
            if not seed_data:
                seed_data.append(synthetic)
            
            if not bin_path:
                return seed_data[0] # Return best guess if build failed

            # Fuzzing Loop
            max_workers = os.cpu_count() or 4
            executor = concurrent.futures.ProcessPoolExecutor(max_workers=max_workers)
            futures = []
            
            # Initial load
            for d in seed_data:
                futures.append(executor.submit(run_fuzz_case, (bin_path, d)))
                for _ in range(5):
                    futures.append(executor.submit(run_fuzz_case, (bin_path, self._mutate(d))))
            
            start_time = time.time()
            timeout = 180 # 3 minutes total budget
            
            while time.time() - start_time < timeout:
                done, not_done = concurrent.futures.wait(futures, timeout=0.1, return_when=concurrent.futures.FIRST_COMPLETED)
                futures = list(not_done)
                
                for f in done:
                    res = f.result()
                    if res:
                        executor.shutdown(wait=False)
                        return res
                
                # Schedule more
                if len(futures) < max_workers * 4:
                    parent = random.choice(seed_data) if seed_data else synthetic
                    child = self._mutate(parent)
                    futures.append(executor.submit(run_fuzz_case, (bin_path, child)))
            
            executor.shutdown(wait=False)
            return seed_data[0] # Return a valid file if no crash found

        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def _mutate(self, data: bytes) -> bytes:
        arr = bytearray(data)
        if not arr: return data
        num_ops = random.randint(1, 4)
        for _ in range(num_ops):
            mode = random.randint(0, 3)
            idx = random.randint(0, len(arr)-1)
            
            if mode == 0: # Flip bit
                bit = random.randint(0, 7)
                arr[idx] ^= (1 << bit)
            elif mode == 1: # Random byte
                arr[idx] = random.randint(0, 255)
            elif mode == 2: # Arithmetic
                val = arr[idx]
                delta = random.choice([1, -1, 2, -2, 10, -10])
                arr[idx] = (val + delta) % 256
            elif mode == 3: # Small block replace
                if len(arr) > 4 and random.random() < 0.2:
                    sz = random.randint(1, 4)
                    if idx + sz <= len(arr):
                        for k in range(sz):
                            arr[idx+k] = random.randint(0, 255)
        return bytes(arr)