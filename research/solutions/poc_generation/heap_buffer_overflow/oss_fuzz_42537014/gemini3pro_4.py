import sys
import os
import subprocess
import tempfile
import shutil
import time
import random
import concurrent.futures

class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp()
        try:
            # 1. Extract Source
            if src_path.endswith('.tar.gz') or src_path.endswith('.tgz'):
                subprocess.run(['tar', 'xzf', src_path, '-C', work_dir], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif src_path.endswith('.tar.bz2'):
                subprocess.run(['tar', 'xjf', src_path, '-C', work_dir], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif src_path.endswith('.zip'):
                subprocess.run(['unzip', '-q', src_path, '-d', work_dir], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(['tar', 'xf', src_path, '-C', work_dir], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # 2. Locate Source Root
            source_root = work_dir
            for root, dirs, files in os.walk(work_dir):
                if 'configure' in files or 'Makefile' in files:
                    source_root = root
                    break
            
            # 3. Build with ASAN
            env = os.environ.copy()
            env['CC'] = 'clang'
            env['CXX'] = 'clang++'
            env['CFLAGS'] = '-fsanitize=address -g -O1'
            env['CXXFLAGS'] = '-fsanitize=address -g -O1'
            env['LDFLAGS'] = '-fsanitize=address'
            
            # Configure
            configure_path = os.path.join(source_root, 'configure')
            if os.path.exists(configure_path):
                os.chmod(configure_path, 0o755)
                cmd = [
                    './configure',
                    '--static-bin',
                    '--disable-ssl',
                    '--disable-x11',
                    '--disable-sdl',
                    '--disable-oss-audio',
                    '--disable-pulseaudio',
                    '--use-zlib=no'
                ]
                subprocess.run(cmd, cwd=source_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Make
            subprocess.run(['make', '-j8'], cwd=source_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 4. Find Target Binary
            target_bin = None
            candidates = ['dash_client', 'gpac', 'MP4Box']
            for cand in candidates:
                for root, dirs, files in os.walk(source_root):
                    if cand in files:
                        fpath = os.path.join(root, cand)
                        if os.access(fpath, os.X_OK):
                            target_bin = fpath
                            break
                if target_bin: break
            
            if not target_bin:
                return b""

            # 5. Fuzzing
            def check(data):
                if not data: return False
                try:
                    with tempfile.NamedTemporaryFile(delete=False, mode='wb', prefix='fuzz_') as tf:
                        tf.write(data)
                        name = tf.name
                except:
                    return False
                
                crashed = False
                try:
                    # Try both passing as file arg and -i arg
                    cmds = [[target_bin, name], [target_bin, '-i', name]]
                    for cmd in cmds:
                        res = subprocess.run(
                            cmd,
                            env=env,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE,
                            timeout=0.5
                        )
                        if res.returncode != 0 and b"AddressSanitizer" in res.stderr:
                            crashed = True
                            break
                except (subprocess.TimeoutExpired, Exception):
                    pass
                finally:
                    if os.path.exists(name):
                        os.unlink(name)
                return crashed

            # Initial Seeds
            seeds = [
                b"http://", b"https://", b"file://", b"dash://",
                b"123456789", b"abcdefghi",
                b"A"*9, b"\x00"*9, b"\xff"*9,
                b"http://a", b"file:///a", b"dash://a",
                b"%s%s%s%s", b"../../../",
                b"mp4box", b"isom",
            ]
            # Add random seeds
            for _ in range(20):
                seeds.append(os.urandom(random.randint(1, 16)))

            executor = concurrent.futures.ThreadPoolExecutor(max_workers=8)
            futures = {}
            for s in seeds:
                futures[executor.submit(check, s)] = s

            found_poc = None
            start_time = time.time()
            population = seeds[:]

            while time.time() - start_time < 240: # 4 minutes max
                done, _ = concurrent.futures.wait(futures, timeout=0.1, return_when=concurrent.futures.FIRST_COMPLETED)
                for f in done:
                    inp = futures.pop(f)
                    if f.result():
                        found_poc = inp
                        break
                
                if found_poc:
                    break
                
                while len(futures) < 16:
                    if population:
                        base = random.choice(population)
                    else:
                        base = b"A"*9
                    
                    # Mutate
                    m = bytearray(base)
                    op = random.randint(0, 4)
                    if not m: m = bytearray(b"A")
                    pos = random.randint(0, len(m)-1)
                    
                    if op == 0: # Flip bit
                        m[pos] ^= (1 << random.randint(0,7))
                    elif op == 1: # Flip byte
                        m[pos] = random.randint(0, 255)
                    elif op == 2: # Insert
                        m.insert(pos, random.randint(0, 255))
                    elif op == 3: # Delete
                        if len(m) > 1: del m[pos]
                    elif op == 4: # Splice
                        m += random.choice(seeds)
                    
                    # Truncate to keep short (target is 9 bytes)
                    if len(m) > 32: m = m[:32]
                    
                    child = bytes(m)
                    if child and child not in population:
                        population.append(child)
                        if len(population) > 500: population.pop(0)
                        futures[executor.submit(check, child)] = child

            executor.shutdown(wait=False)

            # 6. Minimize
            if found_poc:
                current = found_poc
                improved = True
                while improved:
                    improved = False
                    for i in range(len(current)):
                        # Try removing byte at i
                        candidate = current[:i] + current[i+1:]
                        if not candidate: continue
                        if check(candidate):
                            current = candidate
                            improved = True
                            break
                return current

            return b"http://a" # Fallback guess

        except Exception:
            return b""
        finally:
            shutil.rmtree(work_dir)