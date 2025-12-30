import os
import sys
import subprocess
import tempfile
import shutil
import random
import time
import concurrent.futures

class Solution:
    def solve(self, src_path: str) -> bytes:
        temp_dir = tempfile.mkdtemp()
        try:
            # 1. Extract source code
            subprocess.check_call(['tar', 'xf', src_path, '-C', temp_dir], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            src_root = temp_dir
            # Find the actual source root if nested
            items = os.listdir(temp_dir)
            if len(items) == 1:
                possible_root = os.path.join(temp_dir, items[0])
                if os.path.isdir(possible_root):
                    src_root = possible_root
            
            # 2. Build the project
            # Setup build environment for ASAN
            env = os.environ.copy()
            env['CC'] = 'clang'
            env['CXX'] = 'clang++'
            # -fno-sanitize-recover=all ensures exit code is non-zero on error
            flags = "-fsanitize=address -fno-omit-frame-pointer -g -fno-sanitize-recover=all"
            env['CFLAGS'] = flags
            env['CXXFLAGS'] = flags
            env['LDFLAGS'] = flags
            
            # Clean first
            subprocess.run(['make', 'clean'], cwd=src_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
            
            # Build console app. USE_ASM=No is critical for ASAN compatibility in OpenH264
            # We assume 'make' builds the default targets which include the console decoder
            subprocess.check_call(['make', '-j8', 'USE_ASM=No', 'BUILDTYPE=Debug'], cwd=src_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
            
            # 3. Locate executable
            executable = None
            target_names = ['h264dec', 'svcdec', 'H264Dec']
            
            # Priority search locations
            search_dirs = [
                src_root,
                os.path.join(src_root, 'codec', 'console', 'dec'),
                os.path.join(src_root, 'bin')
            ]
            
            for d in search_dirs:
                if os.path.exists(d):
                    for name in target_names:
                        path = os.path.join(d, name)
                        if os.path.exists(path) and os.access(path, os.X_OK):
                            executable = path
                            break
                if executable: break
            
            # Fallback search
            if not executable:
                for root, _, files in os.walk(src_root):
                    for f in files:
                        if f in target_names:
                            path = os.path.join(root, f)
                            if os.access(path, os.X_OK):
                                executable = path
                                break
                    if executable: break
            
            if not executable:
                raise RuntimeError("Could not find h264dec/svcdec executable")
            
            # 4. Gather seeds
            seeds = []
            for root, _, files in os.walk(src_root):
                for f in files:
                    if f.endswith('.264') or f.endswith('.h264'):
                        try:
                            with open(os.path.join(root, f), 'rb') as fd:
                                content = fd.read()
                                if len(content) > 0:
                                    seeds.append(content)
                        except: pass
            
            # Fallback seed if none found
            if not seeds:
                seeds.append(b'\x00\x00\x00\x01\x67\x42\x00\x0a\xf8\x41\xa2\x00\x00\x00\x01\x68\xce\x38\x80\x00\x00\x00\x01\x65\x88\x84\x00\x00\x00\x01')

            # 5. Fuzzing
            found_crash = None
            
            # Runtime environment for ASAN
            run_env = env.copy()
            run_env['ASAN_OPTIONS'] = "detect_leaks=0:abort_on_error=1:symbolize=0"

            # Check seeds first
            for s in seeds:
                tf = os.path.join(temp_dir, "check.264")
                with open(tf, 'wb') as f: f.write(s)
                try:
                    # Provide /dev/null as output file to suppress writing
                    p = subprocess.run([executable, tf, os.devnull], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=run_env, timeout=2)
                    if p.returncode != 0 and b"AddressSanitizer" in p.stderr:
                        found_crash = s
                        break
                except: pass
            
            if found_crash:
                return found_crash
                
            start_time = time.time()
            timeout = 300 # 5 minutes fuzzing budget
            
            def fuzz_worker(idx):
                nonlocal found_crash
                rng = random.Random(idx + time.time())
                t_input = os.path.join(temp_dir, f"fuzz_{idx}.264")
                
                while time.time() - start_time < timeout:
                    if found_crash: return
                    
                    seed = rng.choice(seeds)
                    data = bytearray(seed)
                    
                    # Mutation Strategy
                    # 0: Bit flips, 1: Byte sets, 2: Splicing (effective for dimensions mismatch), 3: Deletion
                    m_type = rng.randint(0, 3)
                    
                    if m_type == 0:
                        count = rng.randint(1, 5)
                        for _ in range(count):
                            if not data: break
                            pos = rng.randint(0, len(data)-1)
                            data[pos] ^= (1 << rng.randint(0, 7))
                            
                    elif m_type == 1:
                        count = rng.randint(1, 5)
                        for _ in range(count):
                            if not data: break
                            pos = rng.randint(0, len(data)-1)
                            data[pos] = rng.randint(0, 255)
                            
                    elif m_type == 2: # Splicing
                        other = rng.choice(seeds)
                        if len(other) > 20:
                            sz = rng.randint(10, min(1000, len(other)))
                            start = rng.randint(0, len(other) - sz)
                            chunk = other[start:start+sz]
                            if not data:
                                data = bytearray(chunk)
                            else:
                                ins = rng.randint(0, len(data))
                                data[ins:ins] = chunk
                                
                    elif m_type == 3: # Deletion
                        if len(data) > 20:
                            sz = rng.randint(1, 20)
                            start = rng.randint(0, len(data)-sz)
                            del data[start:start+sz]
                    
                    if not data: continue
                    
                    with open(t_input, 'wb') as f:
                        f.write(data)
                    
                    try:
                        p = subprocess.run([executable, t_input, os.devnull], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=run_env, timeout=1)
                        if p.returncode != 0:
                            if b"AddressSanitizer" in p.stderr and b"heap-buffer-overflow" in p.stderr:
                                found_crash = bytes(data)
                                return
                    except:
                        pass
            
            # Run threads
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as exc:
                exc.map(fuzz_worker, range(8))
            
            if found_crash:
                # Minimization Step: Trim trailing bytes
                min_data = found_crash
                # Try to remove chunks from the end
                chunk_size = 100
                while len(min_data) > chunk_size:
                    candidate = min_data[:-chunk_size]
                    tf = os.path.join(temp_dir, "min.264")
                    with open(tf, 'wb') as f: f.write(candidate)
                    try:
                        p = subprocess.run([executable, tf, os.devnull], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=run_env, timeout=1)
                        if p.returncode != 0 and b"AddressSanitizer" in p.stderr:
                            min_data = candidate
                        else:
                            # If trimming failed, try smaller chunk or stop
                            if chunk_size > 10:
                                chunk_size //= 2
                            else:
                                break
                    except:
                        break
                return min_data
            
            return seeds[0]
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
