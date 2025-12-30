import os
import sys
import shutil
import subprocess
import tempfile
import glob

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a temporary working directory
        with tempfile.TemporaryDirectory() as work_dir:
            # Setup source directory
            src_root = os.path.join(work_dir, "src")
            os.makedirs(src_root, exist_ok=True)
            
            # Extract source
            if os.path.isfile(src_path) and (src_path.endswith('.tar.gz') or src_path.endswith('.tgz')):
                try:
                    subprocess.run(['tar', 'xzf', src_path, '-C', src_root], check=True, stderr=subprocess.DEVNULL)
                except subprocess.CalledProcessError:
                    return b''
                # If tarball created a single subdirectory, move into it
                entries = os.listdir(src_root)
                if len(entries) == 1 and os.path.isdir(os.path.join(src_root, entries[0])):
                    src_root = os.path.join(src_root, entries[0])
            elif os.path.isdir(src_path):
                # Copy directory content
                for item in os.listdir(src_path):
                    s = os.path.join(src_path, item)
                    d = os.path.join(src_root, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
            else:
                return b''

            # Identify the Fuzzer
            # We look for fuzzers related to polygonToCells (v4) or polyfill (v3)
            fuzzer_src = None
            candidates = []
            
            for root, dirs, files in os.walk(src_root):
                for f in files:
                    if f.endswith('.c') and 'fuzz' in f:
                        f_path = os.path.join(root, f)
                        content = ""
                        try:
                            with open(f_path, 'r', errors='ignore') as fp:
                                content = fp.read()
                        except: pass
                        
                        score = 0
                        # Prioritize polygonToCells and Experimental
                        if 'polygonToCells' in f: score += 10
                        elif 'polyfill' in f: score += 8
                        
                        if 'polygonToCells' in content: score += 5
                        if 'Experimental' in content: score += 5
                        
                        if score > 0:
                            candidates.append((score, f_path))
                        # Keep generic fuzzers as backup
                        elif 'test' not in f:
                            candidates.append((1, f_path))
            
            candidates.sort(key=lambda x: x[0], reverse=True)
            if not candidates:
                return b''
            
            fuzzer_src = candidates[0][1]

            # Gather Library Sources
            lib_srcs = []
            include_dirs = set()
            
            for root, dirs, files in os.walk(src_root):
                # Check for header files to add to includes
                if any(f.endswith('.h') for f in files):
                    include_dirs.add(root)
                
                # Filter source files
                # Exclude tests, apps, fuzzers, benchmarks
                path_parts = root.split(os.sep)
                if any(x in path_parts for x in ['test', 'tests', 'apps', 'examples', 'benchmark', 'fuzzers']):
                    continue
                
                for f in files:
                    if f.endswith('.c'):
                        lib_srcs.append(os.path.join(root, f))

            # Compile
            fuzzer_exe = os.path.join(work_dir, 'fuzzer_bin')
            cflags = ['-g', '-O1', '-fsanitize=address,fuzzer']
            for inc in include_dirs:
                cflags.append(f'-I{inc}')
            
            # Helper to run cmake config if possible (generates config.h if needed)
            try:
                subprocess.run(['cmake', '.'], cwd=src_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except: pass

            cmd = ['clang'] + cflags + [fuzzer_src] + lib_srcs + ['-o', fuzzer_exe, '-lm']
            
            # Attempt compilation
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode != 0:
                return b''
            
            # Fuzz
            # Set timeout to fit in evaluation window
            fuzz_cmd = [
                fuzzer_exe, 
                '-max_total_time=240', 
                '-print_final_stats=1', 
                f'-artifact_prefix={work_dir}/'
            ]
            
            try:
                subprocess.run(fuzz_cmd, cwd=work_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=250)
            except subprocess.TimeoutError:
                pass
            
            # Find Crash
            crashes = glob.glob(os.path.join(work_dir, 'crash-*'))
            if crashes:
                # Return the smallest crash input
                crashes.sort(key=os.path.getsize)
                with open(crashes[0], 'rb') as f:
                    return f.read()
            
            return b''