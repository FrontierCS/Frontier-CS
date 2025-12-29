import os
import sys
import tarfile
import subprocess
import shutil
import tempfile
import random
import time
import threading
from concurrent.futures import ThreadPoolExecutor

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the heap-use-after-free vulnerability in ots::OTSStream::Write.
        """
        work_dir = tempfile.mkdtemp()
        try:
            # Extract source code
            with tarfile.open(src_path) as tar:
                tar.extractall(work_dir)
            
            # Locate the source root directory
            src_root = work_dir
            for root, dirs, files in os.walk(work_dir):
                if 'meson.build' in files or 'configure.ac' in files or 'configure' in files:
                    src_root = root
                    break
            
            # Prepare build environment
            build_dir = os.path.join(work_dir, 'build_output')
            os.makedirs(build_dir, exist_ok=True)
            
            env = os.environ.copy()
            env['CC'] = 'clang'
            env['CXX'] = 'clang++'
            env['CFLAGS'] = '-fsanitize=address -g -O1'
            env['CXXFLAGS'] = '-fsanitize=address -g -O1'
            env['LDFLAGS'] = '-fsanitize=address'
            
            executable = None
            built = False
            
            # Build Strategy 1: Meson
            if os.path.exists(os.path.join(src_root, 'meson.build')):
                try:
                    subprocess.run(['meson', 'setup', build_dir], cwd=src_root, env=env, 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    subprocess.run(['ninja', '-C', build_dir], env=env, 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    built = True
                except Exception:
                    pass
            
            # Build Strategy 2: Autotools / Make
            if not built:
                try:
                    if os.path.exists(os.path.join(src_root, 'autogen.sh')):
                        subprocess.run(['./autogen.sh'], cwd=src_root, env=env, 
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                    if os.path.exists(os.path.join(src_root, 'configure')):
                        subprocess.run(['./configure'], cwd=src_root, env=env, 
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        subprocess.run(['make', '-j8'], cwd=src_root, env=env, 
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        built = True
                    elif os.path.exists(os.path.join(src_root, 'Makefile')):
                         subprocess.run(['make', '-j8'], cwd=src_root, env=env, 
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                         built = True
                except Exception:
                    pass

            # Find the ots-sanitize executable
            for root, dirs, files in os.walk(work_dir):
                if 'ots-sanitize' in files:
                    path = os.path.join(root, 'ots-sanitize')
                    if os.access(path, os.X_OK):
                        executable = path
                        break
            
            if not executable:
                # Fallback if build fails
                return b'\x00\x01\x00\x00\x00\x00\x00\x00'

            # Collect seed files from the source tree
            seeds = []
            for root, dirs, files in os.walk(work_dir):
                for f in files:
                    if f.lower().endswith(('.ttf', '.otf', '.woff', '.woff2')):
                        try:
                            with open(os.path.join(root, f), 'rb') as fd:
                                content = fd.read()
                                if len(content) < 50000: # Limit size for speed
                                    seeds.append(content)
                        except:
                            pass
            
            if not seeds:
                # Add a minimal valid TTF header as a fallback seed
                seeds.append(b'\x00\x01\x00\x00\x00\x00\x00\x00')

            # Fuzzing Logic
            start_time = time.time()
            crash_found = None
            lock = threading.Lock()
            
            def fuzz_worker():
                nonlocal crash_found
                local_rng = random.Random()
                
                while True:
                    # Check global stop conditions
                    if time.time() - start_time > 120: # Timeout after 2 minutes
                        break
                    
                    with lock:
                        if crash_found: return
                    
                    # Selection
                    seed = local_rng.choice(seeds)
                    mutated = bytearray(seed)
                    
                    # Mutation
                    num_ops = local_rng.randint(1, 8)
                    for _ in range(num_ops):
                        if not mutated: break
                        op = local_rng.randint(0, 3)
                        idx = local_rng.randint(0, len(mutated)-1)
                        if op == 0: # Bit flip
                            mutated[idx] ^= (1 << local_rng.randint(0, 7))
                        elif op == 1: # Byte replace
                            mutated[idx] = local_rng.randint(0, 255)
                        elif op == 2: # Delete byte
                            del mutated[idx]
                        elif op == 3: # Insert byte
                            mutated.insert(idx, local_rng.randint(0, 255))

                    # Execution
                    # Use unique temp files
                    inp_fd, inp_path = tempfile.mkstemp()
                    out_fd, out_path = tempfile.mkstemp()
                    os.close(inp_fd)
                    os.close(out_fd)
                    
                    try:
                        with open(inp_path, 'wb') as f:
                            f.write(mutated)
                        
                        # ots-sanitize [input] [output]
                        # We must provide output arg to trigger writing (where vuln lies)
                        proc = subprocess.run(
                            [executable, inp_path, out_path],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE,
                            env=env,
                            timeout=1
                        )
                        
                        if proc.returncode != 0:
                            stderr_output = proc.stderr.decode(errors='ignore')
                            if "AddressSanitizer" in stderr_output and "heap-use-after-free" in stderr_output:
                                with lock:
                                    if not crash_found:
                                        crash_found = bytes(mutated)
                                return
                    except subprocess.TimeoutExpired:
                        pass
                    except Exception:
                        pass
                    finally:
                        if os.path.exists(inp_path): os.unlink(inp_path)
                        if os.path.exists(out_path): os.unlink(out_path)

            # Run fuzzing threads
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(fuzz_worker) for _ in range(8)]
                for f in futures:
                    f.result()
            
            if crash_found:
                return crash_found
            
            # Return a seed if no crash found (best effort)
            return seeds[0]

        finally:
            shutil.rmtree(work_dir, ignore_errors=True)