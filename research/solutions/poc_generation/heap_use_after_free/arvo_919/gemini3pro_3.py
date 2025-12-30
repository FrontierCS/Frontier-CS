import os
import sys
import tarfile
import subprocess
import tempfile
import shutil
import random
import glob
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp()
        
        try:
            # Extract source
            try:
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=work_dir)
            except Exception:
                return b''
            
            # Find source root
            src_root = work_dir
            for root, dirs, files in os.walk(work_dir):
                if 'configure.ac' in files or 'meson.build' in files:
                    src_root = root
                    break
            
            # Detect compiler
            cc = 'gcc'
            cxx = 'g++'
            try:
                subprocess.run(['clang', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                cc = 'clang'
                cxx = 'clang++'
            except Exception:
                pass

            # Environment for ASAN
            env = os.environ.copy()
            env['CC'] = cc
            env['CXX'] = cxx
            flags = "-fsanitize=address -g -O1"
            env['CFLAGS'] = flags
            env['CXXFLAGS'] = flags
            env['LDFLAGS'] = flags
            
            ots_bin = None
            
            # Build
            built = False
            # Try autotools
            if os.path.exists(os.path.join(src_root, 'autogen.sh')):
                subprocess.run(['./autogen.sh'], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            
            if os.path.exists(os.path.join(src_root, 'configure')):
                subprocess.run(['./configure'], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                subprocess.run(['make', '-j8'], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                built = True

            # Try meson if not built or binary not found
            if not built and os.path.exists(os.path.join(src_root, 'meson.build')):
                build_dir = os.path.join(src_root, 'build_meson')
                subprocess.run(['meson', 'setup', build_dir, '-Db_sanitize=address', '-Ddebug=true'], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                subprocess.run(['ninja', '-C', build_dir], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                built = True

            # Find binary
            for root, dirs, files in os.walk(src_root):
                if 'ots-sanitize' in files:
                    ots_bin = os.path.join(root, 'ots-sanitize')
                    break
            
            if not ots_bin:
                return b''

            os.chmod(ots_bin, 0o755)

            # Collect seeds
            seeds = []
            for root, dirs, files in os.walk(src_root):
                for f in files:
                    if f.endswith('.ttf') or f.endswith('.otf'):
                        try:
                            p = os.path.join(root, f)
                            if os.path.getsize(p) < 100000:
                                with open(p, 'rb') as fd:
                                    seeds.append(fd.read())
                        except Exception:
                            pass
            
            if not seeds:
                seeds.append(b'\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

            # Fuzzing
            start_t = time.time()
            time_limit = 240 # 4 minutes
            
            result_container = {'poc': None}

            def check_crash(data):
                with tempfile.NamedTemporaryFile(delete=False) as tf:
                    tf.write(data)
                    tf_name = tf.name
                
                try:
                    p = subprocess.run([ots_bin, tf_name], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=0.5)
                    if p.returncode != 0:
                        if b"heap-use-after-free" in p.stderr:
                            return True
                except Exception:
                    pass
                finally:
                    if os.path.exists(tf_name):
                        os.remove(tf_name)
                return False

            def worker(wid):
                rng = random.Random(wid + time.time())
                while time.time() - start_t < time_limit:
                    if result_container['poc']:
                        return
                    
                    seed = rng.choice(seeds)
                    mut = bytearray(seed)
                    
                    # Mutate
                    ops = rng.randint(1, 8)
                    for _ in range(ops):
                        m = rng.randint(0, 3)
                        if len(mut) == 0: break
                        if m == 0: # flip
                            i = rng.randint(0, len(mut)-1)
                            mut[i] ^= (1 << rng.randint(0,7))
                        elif m == 1: # set
                            i = rng.randint(0, len(mut)-1)
                            mut[i] = rng.randint(0, 255)
                        elif m == 2: # del
                            if len(mut) > 10:
                                i = rng.randint(0, len(mut)-5)
                                l = rng.randint(1, min(30, len(mut)-i))
                                del mut[i:i+l]
                        elif m == 3: # splice
                            if seeds:
                                other = rng.choice(seeds)
                                if len(other) > 0:
                                    start = rng.randint(0, len(other)-1)
                                    l = rng.randint(1, min(50, len(other)-start))
                                    chunk = other[start:start+l]
                                    ins = rng.randint(0, len(mut))
                                    mut[ins:ins] = chunk

                    candidate = bytes(mut)
                    if check_crash(candidate):
                        result_container['poc'] = candidate
                        return

            with ThreadPoolExecutor(max_workers=8) as exe:
                futures = [exe.submit(worker, i) for i in range(8)]
                for f in as_completed(futures):
                    if result_container['poc']:
                        for ft in futures: ft.cancel()
                        break
            
            final_poc = result_container['poc']
            
            if final_poc:
                # Minimization
                data = bytearray(final_poc)
                
                # Truncate from end
                changed = True
                while changed and len(data) > 800:
                    changed = False
                    reduction = max(1, (len(data) - 800) // 2)
                    candidate = data[:-reduction]
                    if check_crash(bytes(candidate)):
                        data = candidate
                        changed = True
                
                return bytes(data)
                
            return seeds[0] if seeds else b''

        except Exception:
            return b''
        finally:
            try:
                shutil.rmtree(work_dir)
            except Exception:
                pass