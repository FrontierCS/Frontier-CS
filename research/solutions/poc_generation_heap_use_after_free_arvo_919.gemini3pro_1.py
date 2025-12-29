import os
import sys
import subprocess
import random
import struct
import tempfile
import shutil
import time
import glob
import multiprocessing

def worker_fuzz(args):
    """
    Worker function to perform mutation-based fuzzing.
    """
    binary_path, seeds, timeout, worker_id = args
    start_time = time.time()
    rng = random.Random()
    rng.seed(start_time + worker_id)
    
    local_seeds = list(seeds)
    if not local_seeds:
        return None

    while time.time() - start_time < timeout:
        seed = rng.choice(local_seeds)
        data = bytearray(seed)
        
        # Stack mutations
        num_mutations = rng.randint(1, 5)
        for _ in range(num_mutations):
            if len(data) == 0:
                data.append(0)
                continue
            
            m_type = rng.randint(0, 5)
            if m_type == 0: # Flip bit
                idx = rng.randint(0, len(data) - 1)
                bit = rng.randint(0, 7)
                data[idx] ^= (1 << bit)
            elif m_type == 1: # Random byte
                idx = rng.randint(0, len(data) - 1)
                data[idx] = rng.randint(0, 255)
            elif m_type == 2: # Delete chunk
                if len(data) > 4:
                    length = rng.randint(1, min(len(data)//2, 128))
                    start = rng.randint(0, len(data) - length)
                    del data[start:start+length]
            elif m_type == 3: # Insert junk
                pos = rng.randint(0, len(data))
                length = rng.randint(1, 128)
                blob = bytearray(rng.getrandbits(8) for _ in range(length))
                data[pos:pos] = blob
            elif m_type == 4: # Magic int overwrite
                if len(data) >= 4:
                    pos = rng.randint(0, len(data) - 4)
                    val = rng.choice([0xFFFFFFFF, 0x80000000, 0x7FFFFFFF, 0xFFFF, 0x00000000])
                    try:
                        struct.pack_into('>I', data, pos, val)
                    except: pass
            elif m_type == 5: # Swap bytes
                if len(data) > 1:
                    p1 = rng.randint(0, len(data)-1)
                    p2 = rng.randint(0, len(data)-1)
                    data[p1], data[p2] = data[p2], data[p1]

        # Write candidate to file
        with tempfile.NamedTemporaryFile(delete=False, mode='wb') as f:
            f.write(data)
            tmp_name = f.name
        
        try:
            # Run target with ASAN environment
            env = os.environ.copy()
            env['ASAN_OPTIONS'] = 'detect_leaks=0:abort_on_error=1:disable_coredump=1:symbolize=0'
            
            proc = subprocess.run(
                [binary_path, tmp_name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                env=env,
                timeout=0.5
            )
            
            # Check for crash (ASan usually exits with non-zero or specific signal)
            # SIGSEGV is -11, ASan error often prints "AddressSanitizer" to stderr
            if b"AddressSanitizer" in proc.stderr or proc.returncode == -11 or proc.returncode == 139:
                return bytes(data)
                
        except Exception:
            pass
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
                
    return None

class Solution:
    def solve(self, src_path: str) -> bytes:
        # 1. Build the vulnerable target with ASAN enabled
        binary = self.build_target(src_path)
        
        # Fallback if build fails: return a valid TTF header to avoid empty return
        if not binary:
            return b'\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

        # 2. Collect seeds from source tree (prioritizing 'arvo' if present)
        seeds = self.collect_seeds(src_path)
        if not seeds:
            # Minimal TTF header if no seeds found
            seeds = [b'\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00']

        # 3. Parallel Fuzzing
        workers = 8
        pool = multiprocessing.Pool(processes=workers)
        
        max_time = 120 # Allow reasonable time to fuzz
        start_time = time.time()
        round_duration = 5 
        
        found_poc = None
        
        try:
            while time.time() - start_time < max_time:
                results = []
                for i in range(workers):
                    results.append(pool.apply_async(worker_fuzz, ((binary, seeds, round_duration, i),)))
                
                # Check results
                for r in results:
                    try:
                        res = r.get()
                        if res:
                            found_poc = res
                            pool.terminate()
                            return found_poc
                    except:
                        pass
                
                if found_poc: break
        except:
            pass
        finally:
            pool.terminate()
            pool.join()
        
        # If no crash found, return the first seed (best effort)
        return found_poc if found_poc else seeds[0]

    def build_target(self, src_path):
        """
        Attempts to build 'ots-sanitize' from source using meson or autotools.
        """
        env = os.environ.copy()
        # Compile with AddressSanitizer
        env['CC'] = 'gcc'
        env['CXX'] = 'g++'
        env['CFLAGS'] = '-fsanitize=address -g -O1'
        env['CXXFLAGS'] = '-fsanitize=address -g -O1'
        env['LDFLAGS'] = '-fsanitize=address'
        
        # Try Meson
        if os.path.exists(os.path.join(src_path, 'meson.build')):
            bdir = os.path.join(src_path, 'build_fuzz')
            if os.path.exists(bdir): shutil.rmtree(bdir)
            try:
                subprocess.run(['meson', 'setup', bdir], cwd=src_path, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['ninja', '-C', bdir], cwd=src_path, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                bin_p = os.path.join(bdir, 'ots-sanitize')
                if os.path.exists(bin_p): return bin_p
            except: pass
            
        # Try Autotools
        if os.path.exists(os.path.join(src_path, 'configure.ac')) or os.path.exists(os.path.join(src_path, 'autogen.sh')):
            try:
                if os.path.exists(os.path.join(src_path, 'autogen.sh')):
                    subprocess.run(['bash', 'autogen.sh'], cwd=src_path, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                if os.path.exists(os.path.join(src_path, 'configure')):
                    subprocess.run(['./configure'], cwd=src_path, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run(['make', '-j8'], cwd=src_path, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                    # Check standard locations
                    paths = [
                        os.path.join(src_path, 'ots-sanitize'),
                        os.path.join(src_path, 'utils', 'ots-sanitize')
                    ]
                    for p in paths:
                        if os.path.exists(p): return p
            except: pass
            
        return None

    def collect_seeds(self, src_path):
        """
        Scans the source directory for TTF/OTF files to use as seeds.
        Prioritizes 'arvo' font if found, then small files.
        """
        seeds = []
        files = glob.glob(os.path.join(src_path, '**', '*.ttf'), recursive=True)
        files += glob.glob(os.path.join(src_path, '**', '*.otf'), recursive=True)
        
        # Sort files: Prefer 'arvo' in name, then smaller files
        files.sort(key=lambda x: (not 'arvo' in os.path.basename(x).lower(), os.path.getsize(x)))
        
        # Take top candidates
        for f in files[:25]:
            try:
                with open(f, 'rb') as fd:
                    data = fd.read()
                    # Skip very large files to keep fuzzing fast
                    if len(data) < 500 * 1024:
                        seeds.append(data)
            except: pass
        return seeds