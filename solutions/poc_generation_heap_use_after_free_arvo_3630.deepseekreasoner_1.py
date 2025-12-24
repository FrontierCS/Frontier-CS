import os
import sys
import tempfile
import tarfile
import shutil
import subprocess
import multiprocessing
import random
import string
import re
import time
import signal
from pathlib import Path
from typing import List, Optional, Tuple

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a temporary workspace
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            # Extract the tarball
            with tarfile.open(src_path, 'r:*') as tar:
                tar.extractall(work_dir)
            
            # Find the extracted root (assuming single top-level directory)
            extracted_dirs = list(work_dir.iterdir())
            if not extracted_dirs:
                raise RuntimeError("No files extracted")
            src_root = extracted_dirs[0]
            if not src_root.is_dir():
                src_root = work_dir  # fallback
            
            # Compile with ASAN and UBSAN
            self.compile_with_sanitizers(src_root)
            
            # Find the proj binary
            proj_bin = self.find_proj_binary(src_root)
            if proj_bin is None:
                raise RuntimeError("Could not find proj binary")
            
            # Parse lsat parameters from PJ_lsat.c
            lsat_params = self.parse_lsat_parameters(src_root)
            
            # Fuzz for a crashing input
            crash_input = self.fuzz_crash(proj_bin, lsat_params)
            if crash_input is None:
                # Fallback: if fuzzing fails, return a known pattern (guess)
                return b"+proj=lsat +ellps=clrk66 +lat_0=0 +lon_0=0"
            
            # Minimize the crashing input
            minimized = self.minimize_input(proj_bin, crash_input)
            return minimized.encode('utf-8')
    
    def compile_with_sanitizers(self, src_root: Path):
        # Try autotools (configure + make)
        configure = src_root / 'configure'
        if configure.is_file():
            env = os.environ.copy()
            env['CFLAGS'] = '-fsanitize=address -fsanitize=undefined -g'
            env['LDFLAGS'] = '-fsanitize=address -fsanitize=undefined'
            subprocess.run([str(configure)], cwd=src_root, env=env, check=True, capture_output=True)
            subprocess.run(['make', '-j8'], cwd=src_root, check=True, capture_output=True)
        else:
            # Try CMake
            cmake_cache = src_root / 'CMakeCache.txt'
            if not cmake_cache.is_file():
                build_dir = src_root / 'build'
                build_dir.mkdir(exist_ok=True)
                env = os.environ.copy()
                cmake_args = ['cmake', '-DCMAKE_C_FLAGS=-fsanitize=address -fsanitize=undefined -g',
                              '-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address -fsanitize=undefined',
                              '..']
                subprocess.run(cmake_args, cwd=build_dir, env=env, check=True, capture_output=True)
                subprocess.run(['make', '-j8'], cwd=build_dir, check=True, capture_output=True)
    
    def find_proj_binary(self, src_root: Path) -> Optional[Path]:
        # Common locations
        possibilities = [
            src_root / 'src' / 'proj',
            src_root / 'proj',
            src_root / 'build' / 'src' / 'proj',
            src_root / 'build' / 'proj',
            src_root / 'bin' / 'proj',
        ]
        for p in possibilities:
            if p.is_file() and os.access(p, os.X_OK):
                return p
        # Search recursively
        for root, dirs, files in os.walk(src_root):
            for f in files:
                if f == 'proj' or f == 'proj.exe':
                    path = Path(root) / f
                    if os.access(path, os.X_OK):
                        return path
        return None
    
    def parse_lsat_parameters(self, src_root: Path) -> List[str]:
        # Find PJ_lsat.c
        lsat_path = None
        for root, dirs, files in os.walk(src_root):
            for f in files:
                if f == 'PJ_lsat.c' or f == 'pj_lsat.c':
                    lsat_path = Path(root) / f
                    break
            if lsat_path:
                break
        if lsat_path is None:
            # If not found, return default parameters for lsat
            return ['ellps', 'a', 'b', 'lat_0', 'lon_0', 'lsat', 'path']
        
        # Try to extract parameter names from PJ_LIST array
        with open(lsat_path, 'r') as f:
            content = f.read()
        
        # Look for patterns like { "param_name", ... }
        # The array might be named "lsat[]" or "PJ_LSAT_PARAMS"
        # We'll look for lines with double quotes and optional preceding { or comma
        param_pattern = r'"(?P<param>\w+)"\s*,[^}]*?NULL'
        matches = re.findall(param_pattern, content, re.DOTALL)
        if matches:
            return list(set(matches))  # deduplicate
        
        # Fallback
        return ['ellps', 'a', 'b', 'lat_0', 'lon_0', 'lsat', 'path']
    
    def fuzz_crash(self, proj_bin: Path, lsat_params: List[str], timeout_sec=30) -> Optional[str]:
        start_time = time.time()
        num_workers = multiprocessing.cpu_count()
        pool = multiprocessing.Pool(processes=num_workers)
        manager = multiprocessing.Manager()
        crash_found = manager.Value('b', False)
        crash_input = manager.Value('s', '')
        
        def fuzz_worker(worker_id):
            local_random = random.Random(worker_id + time.time())
            while not crash_found.value and time.time() - start_time < timeout_sec:
                # Generate random lsat projection string
                num_params = local_random.randint(1, len(lsat_params))
                chosen_params = local_random.sample(lsat_params, num_params)
                args = ['+proj=lsat']
                for param in chosen_params:
                    if param == 'ellps':
                        ellps_options = ['WGS84', 'clrk66', 'GRS80', 'bessel']
                        value = local_random.choice(ellps_options)
                    elif param in ('a', 'b'):
                        value = str(local_random.uniform(6300000, 6400000))
                    elif param in ('lat_0', 'lon_0'):
                        value = str(local_random.uniform(-90, 90))
                    elif param == 'lsat':
                        value = str(local_random.randint(1, 5))
                    elif param == 'path':
                        value = str(local_random.randint(1, 999))
                    else:
                        value = str(local_random.randint(0, 100))
                    args.append(f'+{param}={value}')
                
                # Run proj with these arguments
                proc = subprocess.run([str(proj_bin)] + args,
                                       stdin=subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.PIPE,
                                       timeout=2)
                # Check for ASAN crash (non-zero exit and stderr contains 'use-after-free' or 'ASAN')
                if proc.returncode != 0:
                    stderr = proc.stderr.decode('utf-8', errors='ignore')
                    if 'use-after-free' in stderr or 'AddressSanitizer' in stderr:
                        crash_found.value = True
                        crash_input.value = ' '.join(args)
                        return crash_input.value
            return None
        
        # Run workers
        try:
            results = pool.map_async(fuzz_worker, range(num_workers)).get(timeout=timeout_sec+5)
            for res in results:
                if res is not None:
                    return res
        except multiprocessing.TimeoutError:
            pass
        finally:
            pool.close()
            pool.join()
        
        return crash_input.value if crash_found.value else None
    
    def minimize_input(self, proj_bin: Path, crash_input: str) -> str:
        # Split into individual +key=value tokens
        tokens = crash_input.split()
        # Ensure first token is +proj=lsat
        if not tokens or not tokens[0].startswith('+proj='):
            return crash_input
        
        # Try removing tokens one by one
        i = 1
        while i < len(tokens):
            test_tokens = tokens[:i] + tokens[i+1:]
            if self.does_crash(proj_bin, test_tokens):
                tokens = test_tokens
                # Keep i the same to try removing the next token
            else:
                i += 1
        
        # Try shortening values
        for idx, token in enumerate(tokens):
            if '=' in token:
                key, value = token.split('=', 1)
                # Try empty value
                if self.does_crash(proj_bin, tokens[:idx] + [key + '='] + tokens[idx+1:]):
                    tokens[idx] = key + '='
                    continue
                # Try single character if value is longer
                if len(value) > 1:
                    for c in ['0', '1', 'a', '.']:
                        if self.does_crash(proj_bin, tokens[:idx] + [key + '=' + c] + tokens[idx+1:]):
                            tokens[idx] = key + '=' + c
                            break
        
        return ' '.join(tokens)
    
    def does_crash(self, proj_bin: Path, args: List[str]) -> bool:
        try:
            proc = subprocess.run([str(proj_bin)] + args,
                                   stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.PIPE,
                                   timeout=2)
            if proc.returncode != 0:
                stderr = proc.stderr.decode('utf-8', errors='ignore')
                if 'use-after-free' in stderr or 'AddressSanitizer' in stderr:
                    return True
        except subprocess.TimeoutExpired:
            pass
        return False
