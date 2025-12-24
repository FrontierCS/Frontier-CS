import os
import sys
import tarfile
import subprocess
import tempfile
import shutil
import random
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        Args:
            src_path: Path to the vulnerable source code tarball
        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        workspace = tempfile.mkdtemp()
        try:
            # 1. Extract source code
            with tarfile.open(src_path) as tar:
                tar.extractall(path=workspace)
            
            # Find root directory of the source
            src_root = workspace
            entries = os.listdir(workspace)
            if len(entries) == 1 and os.path.isdir(os.path.join(workspace, entries[0])):
                src_root = os.path.join(workspace, entries[0])
            
            # 2. Configure build environment for MSAN (Memory Sanitizer)
            # MSAN is required to detect uninitialized value vulnerabilities
            env = os.environ.copy()
            flags = "-fsanitize=memory -fsanitize-memory-track-origins -g -O1 -fno-omit-frame-pointer"
            env['CC'] = 'clang'
            env['CXX'] = 'clang++'
            env['CFLAGS'] = flags
            env['CXXFLAGS'] = flags
            env['LDFLAGS'] = flags
            
            # 3. Build the project
            build_dir = os.path.join(src_root, 'build_fuzz')
            os.makedirs(build_dir, exist_ok=True)
            
            built_targets = []
            
            # Strategy A: CMake
            if os.path.exists(os.path.join(src_root, 'CMakeLists.txt')):
                try:
                    subprocess.run(['cmake', '..'], cwd=build_dir, env=env, check=True, 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run(['make', '-j8'], cwd=build_dir, env=env, check=True, 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                    for root, _, files in os.walk(build_dir):
                        for f in files:
                            p = os.path.join(root, f)
                            if os.access(p, os.X_OK) and not f.endswith('.sh') and not f.endswith('.py'):
                                built_targets.append(p)
                except Exception:
                    pass

            # Strategy B: Configure/Make
            if not built_targets and os.path.exists(os.path.join(src_root, 'configure')):
                try:
                    subprocess.run(['chmod', '+x', './configure'], cwd=src_root, stderr=subprocess.DEVNULL)
                    subprocess.run(['./configure'], cwd=src_root, env=env, check=True,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run(['make', '-j8'], cwd=src_root, env=env, check=True,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    
                    for root, _, files in os.walk(src_root):
                        for f in files:
                            p = os.path.join(root, f)
                            if os.access(p, os.X_OK) and not p.endswith('.o'):
                                built_targets.append(p)
                except Exception:
                    pass
            
            # Strategy C: Raw Make
            if not built_targets and os.path.exists(os.path.join(src_root, 'Makefile')):
                try:
                    subprocess.run(['make', '-j8'], cwd=src_root, env=env, check=True,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    for root, _, files in os.walk(src_root):
                        for f in files:
                            p = os.path.join(root, f)
                            if os.access(p, os.X_OK) and not p.endswith('.o'):
                                built_targets.append(p)
                except Exception:
                    pass

            if not built_targets:
                return b""

            # 4. Identify Target Binary
            target = None
            # Prefer binaries with 'fuzz' in the name
            for t in built_targets:
                if 'fuzz' in os.path.basename(t).lower():
                    target = t
                    break
            # Fallback to the largest binary
            if not target:
                target = max(built_targets, key=lambda x: os.path.getsize(x))
            
            # Update LD_LIBRARY_PATH to include build libs
            lib_paths = set()
            for root, _, _ in os.walk(workspace):
                dirname = os.path.basename(root)
                if 'lib' in dirname or '.libs' in dirname:
                    lib_paths.add(root)
            env['LD_LIBRARY_PATH'] = ':'.join(lib_paths) + ':' + env.get('LD_LIBRARY_PATH', '')

            # 5. Collect Seeds
            seeds = []
            valid_exts = {'.nc', '.cdf', '.h5', '.hdf5', '.exr', '.tif', '.tiff', '.jpg', '.jpeg', '.png', '.bmp', '.xml'}
            
            for root, _, files in os.walk(src_root):
                if 'build' in root: continue
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    p = os.path.join(root, f)
                    if 0 < os.path.getsize(p) < 200000:
                        if ext in valid_exts:
                            seeds.insert(0, p) # Priority
                        elif not f.endswith(('.c', '.h', '.cpp', '.hpp', '.o', '.py', '.sh', '.in', '.am', '.m4', '.po')):
                            seeds.append(p)
            
            if not seeds:
                # Fallback dummy seed
                dummy = os.path.join(workspace, 'seed.bin')
                with open(dummy, 'wb') as f:
                    f.write(b'\x00' * 256)
                seeds.append(dummy)

            # Load corpus
            corpus = []
            for s in seeds[:50]:
                try:
                    with open(s, 'rb') as f:
                        corpus.append(bytearray(f.read()))
                except:
                    pass
            if not corpus:
                corpus = [bytearray(b'A'*100)]

            # 6. Fuzz Loop
            fuzz_file = os.path.join(workspace, 'fuzz_input')
            start_time = time.time()
            time_limit = 120 # Short fuzzing session
            
            while time.time() - start_time < time_limit:
                parent = random.choice(corpus)
                child = bytearray(parent)
                
                # Mutate
                num_mutations = random.randint(1, 5)
                for _ in range(num_mutations):
                    if not child: break
                    op = random.random()
                    if op < 0.1: # Insert
                        pos = random.randint(0, len(child))
                        child.insert(pos, random.randint(0, 255))
                    elif op < 0.2: # Delete
                        if len(child) > 1:
                            pos = random.randint(0, len(child)-1)
                            del child[pos]
                    elif op < 0.7: # Flip byte
                        pos = random.randint(0, len(child)-1)
                        child[pos] = random.randint(0, 255)
                    else: # Flip bit
                        pos = random.randint(0, len(child)-1)
                        bit = random.randint(0, 7)
                        child[pos] ^= (1 << bit)
                
                # Write
                try:
                    with open(fuzz_file, 'wb') as f:
                        f.write(child)
                except:
                    continue
                
                # Execute
                try:
                    proc = subprocess.run([target, fuzz_file], env=env, 
                                        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, 
                                        timeout=0.5)
                    
                    if proc.returncode != 0:
                        # MSAN usually outputs to stderr
                        if b"MemorySanitizer" in proc.stderr or b"uninitialized-value" in proc.stderr:
                            return bytes(child)
                        # Check exit code 77 or similar often used by sanitizers
                        if proc.returncode == 77: 
                            return bytes(child)
                            
                except subprocess.TimeoutExpired:
                    pass
                except Exception:
                    pass
            
            return bytes(corpus[0])

        finally:
            shutil.rmtree(workspace, ignore_errors=True)
