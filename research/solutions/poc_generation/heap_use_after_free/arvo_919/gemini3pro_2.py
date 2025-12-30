import os
import sys
import tarfile
import subprocess
import tempfile
import shutil
import random
import time
import multiprocessing
import glob
import struct

def worker_fuzz(exe, seeds, queue, stop_event):
    r = random.Random()
    # Add env vars for ASAN to ensure it aborts on error
    env = os.environ.copy()
    env['ASAN_OPTIONS'] = 'abort_on_error=1:detect_leaks=0'
    
    while not stop_event.is_set():
        try:
            if not seeds:
                break
            seed = r.choice(seeds)
            mutated = bytearray(seed)
            
            # Mutation logic
            num_mutations = r.randint(1, 5)
            for _ in range(num_mutations):
                if not mutated: break
                op = r.choice(['flip', 'replace', 'insert', 'delete', 'chunk_replace'])
                idx = r.randint(0, len(mutated)-1)
                
                if op == 'flip':
                    bit = r.randint(0, 7)
                    mutated[idx] ^= (1 << bit)
                elif op == 'replace':
                    mutated[idx] = r.randint(0, 255)
                elif op == 'insert':
                    if len(mutated) < 10000:
                        val = r.randint(0, 255)
                        mutated.insert(idx, val)
                elif op == 'delete':
                    if len(mutated) > 20:
                        del mutated[idx]
                elif op == 'chunk_replace':
                    # Replace a chunk with random bytes or interesting values
                    chunk_len = r.randint(1, 4)
                    for i in range(min(chunk_len, len(mutated) - idx)):
                        mutated[idx + i] = r.randint(0, 255)

            data = bytes(mutated)
            
            # Write temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ttf') as tf:
                tf.write(data)
                tf_path = tf.name
            
            try:
                # Run target
                # ots-sanitize [filename] writes to stdout
                p = subprocess.run(
                    [exe, tf_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    env=env,
                    timeout=1
                )
                
                if p.returncode != 0:
                    stderr = p.stderr.decode(errors='ignore')
                    if "AddressSanitizer: heap-use-after-free" in stderr:
                        queue.put(data)
                        stop_event.set()
                        os.unlink(tf_path)
                        return
            except subprocess.TimeoutExpired:
                pass
            finally:
                if os.path.exists(tf_path):
                    os.unlink(tf_path)
                    
        except Exception:
            pass

class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp()
        try:
            # 1. Extract source
            with tarfile.open(src_path) as tar:
                tar.extractall(work_dir)
            
            # Find source root
            src_root = work_dir
            for root, dirs, files in os.walk(work_dir):
                if 'meson.build' in files or 'configure.ac' in files or 'configure' in files:
                    src_root = root
                    break
            
            # 2. Build vulnerable binary
            ots_bin = self._build(src_root)
            if not ots_bin:
                # Fallback: cannot build, return a dummy seed
                return self._make_fallback_seed()

            # 3. Collect seeds
            seeds = self._collect_seeds(src_root)
            if not seeds:
                seeds = [self._make_fallback_seed()]

            # 4. Fuzz
            # Limit fuzzing time to ~3 minutes to fit evaluation constraints
            poc = self._fuzz(ots_bin, seeds, duration=180)
            return poc
            
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def _build(self, src_root):
        env = os.environ.copy()
        # Ensure AddressSanitizer is used
        flags = "-fsanitize=address -g -O1"
        env['CC'] = 'clang'
        env['CXX'] = 'clang++'
        env['CFLAGS'] = flags
        env['CXXFLAGS'] = flags
        env['LDFLAGS'] = flags
        
        # Method 1: Meson
        if os.path.exists(os.path.join(src_root, 'meson.build')):
            build_dir = os.path.join(src_root, 'build_work')
            try:
                # meson setup
                subprocess.run(
                    ['meson', 'setup', build_dir, '-Ddebug=true', '-Db_sanitize=address'],
                    cwd=src_root, env=env, check=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                # ninja compile
                subprocess.run(
                    ['ninja', '-C', build_dir],
                    cwd=src_root, env=env, check=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                bin_path = os.path.join(build_dir, 'ots-sanitize')
                if os.path.exists(bin_path):
                    return bin_path
            except Exception:
                pass

        # Method 2: Autotools
        if os.path.exists(os.path.join(src_root, 'configure')) or os.path.exists(os.path.join(src_root, 'autogen.sh')):
            try:
                if not os.path.exists(os.path.join(src_root, 'configure')):
                    subprocess.run(['./autogen.sh'], cwd=src_root, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                subprocess.run(['./configure'], cwd=src_root, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['make', '-j8'], cwd=src_root, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                candidates = [
                    os.path.join(src_root, 'ots-sanitize'),
                    os.path.join(src_root, '.libs', 'ots-sanitize'),
                    os.path.join(src_root, 'util', 'ots-sanitize')
                ]
                for c in candidates:
                    if os.path.exists(c):
                        return c
            except Exception:
                pass
        
        return None

    def _collect_seeds(self, src_root):
        # Look for valid TTF/OTF in tests
        seeds = []
        test_dir = os.path.join(src_root, 'tests')
        if os.path.exists(test_dir):
            files = glob.glob(os.path.join(test_dir, '**', '*.ttf'), recursive=True) + \
                    glob.glob(os.path.join(test_dir, '**', '*.otf'), recursive=True)
            
            # Prioritize 'arvo' seeds if prompt hint is relevant to file naming
            arvo_files = [f for f in files if 'arvo' in f.lower()]
            other_files = [f for f in files if 'arvo' not in f.lower()]
            
            # Read small seeds
            for fpath in (arvo_files + other_files):
                try:
                    size = os.path.getsize(fpath)
                    if size < 20000: # Limit size
                        with open(fpath, 'rb') as f:
                            seeds.append(f.read())
                        if len(seeds) >= 20: # Do not collect too many
                            break
                except:
                    pass
        return seeds

    def _make_fallback_seed(self):
        # Construct a minimal SFNT structure with one 'cmap' table
        # sfnt header (12 bytes) + 1 table record (16 bytes) + table data
        # Header:
        #  sfntVersion: 0x00010000
        #  numTables: 1
        #  searchRange: 16
        #  entrySelector: 0
        #  rangeShift: 0
        header = b'\x00\x01\x00\x00\x00\x01\x00\x10\x00\x00\x00\x00'
        # Table Record:
        #  tag: 'cmap'
        #  checksum: 0 (placeholder)
        #  offset: 28 (12 + 16)
        #  length: 4
        record = b'cmap\x00\x00\x00\x00\x00\x00\x00\x1C\x00\x00\x00\x04'
        # Data:
        #  Dummy bytes
        data = b'\x00\x00\x00\x00'
        return header + record + data

    def _fuzz(self, exe, seeds, duration):
        manager = multiprocessing.Manager()
        queue = manager.Queue()
        stop_event = manager.Event()
        
        pool = multiprocessing.Pool(processes=8)
        
        for _ in range(8):
            pool.apply_async(worker_fuzz, (exe, seeds, queue, stop_event))
            
        start_time = time.time()
        result = None
        
        while time.time() - start_time < duration:
            if stop_event.is_set():
                if not queue.empty():
                    result = queue.get()
                break
            time.sleep(1)
            
        stop_event.set()
        pool.close()
        pool.join()
        
        if result:
            return result
        # If no crash, return best effort seed
        return seeds[0]