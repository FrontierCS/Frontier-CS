import os
import sys
import tarfile
import subprocess
import tempfile
import shutil
import random
import re
import glob
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """
        work_dir = tempfile.mkdtemp()
        try:
            # 1. Extract source code
            with tarfile.open(src_path) as tar:
                tar.extractall(path=work_dir)

            # Locate actual source root (handle nested folder)
            src_root = work_dir
            entries = os.listdir(work_dir)
            if len(entries) == 1 and os.path.isdir(os.path.join(work_dir, entries[0])):
                src_root = os.path.join(work_dir, entries[0])

            # 2. Compile with AddressSanitizer
            binaries = self._compile(src_root)
            if not binaries:
                # If standard build failed, try to find any existing binary
                binaries = self._find_binaries(src_root)
            
            if not binaries:
                return b""

            # 3. Analyze source for fuzzing dictionary
            dictionary = self._extract_strings(src_root)
            
            # 4. Gather seeds
            seeds = self._find_seeds(src_root)
            if not seeds:
                seeds = [b"A", b"test", b"12345"]
                # Add short dictionary words as seeds
                for w in dictionary:
                    seeds.append(w)

            # 5. Fuzzing Loop
            # We have 8 vCPUs, but running single process fuzzing is often sufficient for small PoCs
            # We will try each binary found.
            start_time = time.time()
            max_duration = 120 # Seconds to find the bug

            for binary in binaries:
                remaining_time = max_duration - (time.time() - start_time)
                if remaining_time <= 0: break

                crash_input = self._fuzz(binary, seeds, dictionary, min(remaining_time, 45))
                if crash_input:
                    # 6. Minimize the PoC
                    return self._minimize(binary, crash_input)

            return b""

        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def _compile(self, src_dir):
        env = os.environ.copy()
        # Enable ASAN
        flags = "-fsanitize=address -g -O1"
        env["CFLAGS"] = flags
        env["CXXFLAGS"] = flags
        
        # Prefer clang if available, else gcc
        if shutil.which("clang"):
            env["CC"] = "clang"
            env["CXX"] = "clang++"

        built = False
        # Heuristic 1: Makefile
        if os.path.exists(os.path.join(src_dir, "Makefile")):
            subprocess.run(["make", "-j8"], cwd=src_dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            built = True
        # Heuristic 2: configure
        elif os.path.exists(os.path.join(src_dir, "configure")):
            subprocess.run(["chmod", "+x", "configure"], cwd=src_dir, stderr=subprocess.DEVNULL)
            subprocess.run(["./configure"], cwd=src_dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["make", "-j8"], cwd=src_dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            built = True
        # Heuristic 3: CMake
        elif os.path.exists(os.path.join(src_dir, "CMakeLists.txt")):
            bdir = os.path.join(src_dir, "build_fuzz")
            os.makedirs(bdir, exist_ok=True)
            subprocess.run(["cmake", ".."], cwd=bdir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["make", "-j8"], cwd=bdir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            src_dir = bdir
            built = True
        
        return self._find_binaries(src_dir)

    def _find_binaries(self, directory):
        binaries = []
        for root, dirs, files in os.walk(directory):
            for f in files:
                path = os.path.join(root, f)
                if os.access(path, os.X_OK):
                    # Filter out scripts
                    if f.endswith(('.sh', '.py', '.pl', '.o', '.a', '.so')): continue
                    try:
                        with open(path, 'rb') as fp:
                            header = fp.read(4)
                            if header.startswith(b'\x7fELF'):
                                binaries.append(path)
                    except:
                        pass
        return binaries

    def _extract_strings(self, src_dir):
        strings = set()
        for root, dirs, files in os.walk(src_dir):
            for f in files:
                if f.endswith(('.c', '.cpp', '.h', '.hpp', '.cc')):
                    try:
                        with open(os.path.join(root, f), 'r', errors='ignore') as fp:
                            content = fp.read()
                            # Find string literals
                            matches = re.findall(r'"([^"\\]+)"', content)
                            for m in matches:
                                if len(m) < 40:
                                    strings.add(m.encode('utf-8'))
                    except: pass
        return list(strings)

    def _find_seeds(self, src_dir):
        seeds = []
        for root, dirs, files in os.walk(src_dir):
            if any(x in root.lower() for x in ['test', 'sample', 'example', 'corpus']):
                for f in files:
                    if f.endswith(('.txt', '.xml', '.json', '.dat', '.in')):
                        try:
                            with open(os.path.join(root, f), 'rb') as fp:
                                data = fp.read()
                                if 0 < len(data) < 1000:
                                    seeds.append(data)
                        except: pass
        return seeds

    def _fuzz(self, binary, seeds, dictionary, duration):
        start_time = time.time()
        population = list(seeds)
        if not population:
            population = [b"A"]
        
        # Try initial seeds
        for s in population:
            if self._execute(binary, s):
                return s

        while time.time() - start_time < duration:
            # Mutation
            parent = random.choice(population)
            mutant = self._mutate(parent, dictionary)
            
            if self._execute(binary, mutant):
                return mutant
            
            # Add to population with low probability to keep diversity
            if random.random() < 0.05:
                population.append(mutant)
                if len(population) > 200:
                    population.pop(0)
        return None

    def _mutate(self, data, dictionary):
        arr = bytearray(data)
        if not arr: return b"A"

        method = random.randint(0, 5)
        if method == 0: # Bit flip
            idx = random.randint(0, len(arr)-1)
            arr[idx] ^= (1 << random.randint(0, 7))
        elif method == 1: # Insert byte
            idx = random.randint(0, len(arr))
            arr.insert(idx, random.randint(0, 255))
        elif method == 2 and len(arr) > 1: # Delete byte
            idx = random.randint(0, len(arr)-1)
            del arr[idx]
        elif method == 3 and dictionary: # Insert dict word
            word = random.choice(dictionary)
            idx = random.randint(0, len(arr))
            arr[idx:idx] = word
        elif method == 4 and dictionary: # Replace dict word
            word = random.choice(dictionary)
            if len(arr) >= len(word):
                idx = random.randint(0, len(arr)-len(word))
                arr[idx:idx+len(word)] = word
        elif method == 5: # Repeat chunk (good for overflows/logic)
            if len(arr) > 0:
                chunk_len = random.randint(1, min(10, len(arr)))
                start = random.randint(0, len(arr)-chunk_len)
                chunk = arr[start:start+chunk_len]
                idx = random.randint(0, len(arr))
                arr[idx:idx] = chunk
        
        # Keep it reasonably short
        if len(arr) > 300:
            arr = arr[:300]
        return bytes(arr)

    def _execute(self, binary, data):
        try:
            # Target binaries usually read from stdin
            p = subprocess.Popen([binary], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            _, stderr = p.communicate(input=data, timeout=0.5)
            if p.returncode != 0:
                if b"AddressSanitizer" in stderr:
                    return True
        except:
            pass
        return False

    def _minimize(self, binary, data):
        current = data
        step = 1
        while step < len(current):
            # Attempt to remove 'step' bytes at all positions
            found_smaller = False
            for i in range(0, len(current) - step + 1):
                subset = current[:i] + current[i+step:]
                if self._execute(binary, subset):
                    current = subset
                    found_smaller = True
                    step = 1 # Reset step
                    break
            
            if not found_smaller:
                step += 1
        return current