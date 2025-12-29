import os
import sys
import subprocess
import tempfile
import tarfile
import shutil
import random
import time
from concurrent.futures import ThreadPoolExecutor

class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp()
        
        try:
            # Extract source code
            if src_path.endswith('.tar.gz') or src_path.endswith('.tgz'):
                try:
                    with tarfile.open(src_path, "r:gz") as tar:
                        tar.extractall(path=work_dir)
                except:
                    pass
            elif src_path.endswith('.tar'):
                try:
                    with tarfile.open(src_path, "r:") as tar:
                        tar.extractall(path=work_dir)
                except:
                    pass
            else:
                try:
                    shutil.unpack_archive(src_path, work_dir)
                except:
                    pass

            # Find build root
            src_root = work_dir
            for root, dirs, files in os.walk(work_dir):
                if 'configure' in files or 'Makefile' in files or 'CMakeLists.txt' in files:
                    src_root = root
                    break
            
            # Detect compiler
            cc = 'gcc'
            cxx = 'g++'
            try:
                subprocess.run(['clang', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                cc = 'clang'
                cxx = 'clang++'
            except:
                pass

            env = os.environ.copy()
            flags = "-fsanitize=address -g -O1 -fno-omit-frame-pointer"
            env['CC'] = cc
            env['CXX'] = cxx
            env['CFLAGS'] = flags
            env['CXXFLAGS'] = flags
            env['LDFLAGS'] = flags

            # Build
            built = False
            # Try configure
            if os.path.exists(os.path.join(src_root, 'configure')):
                subprocess.run(['./configure', '--disable-shared', '--enable-static'], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['make', '-j8'], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                built = True
            
            # Try CMake
            if not built and os.path.exists(os.path.join(src_root, 'CMakeLists.txt')):
                bdir = os.path.join(src_root, 'build_cmake')
                os.makedirs(bdir, exist_ok=True)
                subprocess.run(['cmake', '..'], cwd=bdir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['make', '-j8'], cwd=bdir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                built = True

            # Try Makefile directly if nothing else
            if not built and os.path.exists(os.path.join(src_root, 'Makefile')):
                subprocess.run(['make', '-j8'], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Find executable
            target = None
            candidates = []
            for root, dirs, files in os.walk(work_dir):
                for f in files:
                    path = os.path.join(root, f)
                    if os.access(path, os.X_OK) and not os.path.isdir(path):
                        candidates.append(path)
            
            # Prioritize based on name
            priority = ['dash_client', 'MP4Client', 'gpac']
            for name in priority:
                for c in candidates:
                    if name in os.path.basename(c):
                        target = c
                        break
                if target: break
            
            if not target and candidates:
                target = candidates[0]

            if not target:
                return b"https://a"

            # Fuzzing
            found_poc = None
            
            def try_input(data):
                nonlocal found_poc
                if found_poc: return
                
                tf_name = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, dir=work_dir) as tf:
                        tf.write(data)
                        tf_name = tf.name
                    
                    # Try direct invocation
                    proc = subprocess.run([target, tf_name], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=env, timeout=1.0)
                    if proc.returncode != 0:
                        err = proc.stderr.decode('utf-8', errors='ignore')
                        if "AddressSanitizer" in err:
                            found_poc = data
                            return

                    # Try with -i flag (common for GPAC/dash_client)
                    if not found_poc:
                        proc = subprocess.run([target, '-i', tf_name], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, env=env, timeout=1.0)
                        if proc.returncode != 0:
                            err = proc.stderr.decode('utf-8', errors='ignore')
                            if "AddressSanitizer" in err:
                                found_poc = data
                                return
                except:
                    pass
                finally:
                    if tf_name and os.path.exists(tf_name):
                        os.unlink(tf_name)

            # Strategy: check lengths increasing to find shortest PoC
            # Chars including URL safe and some binary
            chars = b"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/:._-@"
            prefixes = [b"http://", b"https://", b"file://", b"dash://", b"data:", b""]

            # Ground truth is 9 bytes. Check surrounding lengths.
            for length in range(1, 16):
                if found_poc: break
                
                seeds = set()
                # From prefixes
                for p in prefixes:
                    if len(p) <= length:
                        # Append one random suffix to fill
                        seeds.add(p + b'a' * (length - len(p)))
                        # Append some variations
                        for _ in range(5):
                            seeds.add(p + bytes(random.choice(chars) for _ in range(length - len(p))))
                    else:
                        seeds.add(p[:length])
                
                # Random strings
                for _ in range(20):
                    seeds.add(bytes(random.choice(chars) for _ in range(length)))
                
                # Run batch
                with ThreadPoolExecutor(max_workers=8) as exe:
                    futures = [exe.submit(try_input, s) for s in seeds]
                    for f in futures:
                        f.result()
                        if found_poc: break
            
            if found_poc:
                return found_poc
            
            # Fallback guess
            return b"https://a"

        finally:
            try:
                shutil.rmtree(work_dir)
            except:
                pass