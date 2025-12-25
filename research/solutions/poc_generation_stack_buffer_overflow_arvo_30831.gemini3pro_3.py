import os
import sys
import tarfile
import subprocess
import tempfile
import shutil
import random
import time
import glob
import concurrent.futures

class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp()
        try:
            # 1. Extract the tarball
            try:
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=work_dir)
            except Exception:
                pass
            
            # 2. Locate Source/Build Root
            build_root = work_dir
            # Heuristic: look for build files in subdirectories
            for root, dirs, files in os.walk(work_dir):
                if "Makefile" in files or "build.sh" in files or "CMakeLists.txt" in files:
                    build_root = root
                    break
            
            # 3. Build the vulnerable application
            env = os.environ.copy()
            flags = "-fsanitize=address -g -O1"
            env["CFLAGS"] = flags
            env["CXXFLAGS"] = flags
            
            built = False
            
            # Method A: build.sh
            if os.path.exists(os.path.join(build_root, "build.sh")):
                try:
                    subprocess.run(["bash", "build.sh"], cwd=build_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    built = True
                except: pass
                
            # Method B: Makefile
            if not built and os.path.exists(os.path.join(build_root, "Makefile")):
                try:
                    subprocess.run(["make", "clean"], cwd=build_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run(["make"], cwd=build_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    built = True
                except: pass
                
            # Method C: CMake
            if not built and os.path.exists(os.path.join(build_root, "CMakeLists.txt")):
                try:
                    b_dir = os.path.join(build_root, "build_cmake")
                    os.makedirs(b_dir, exist_ok=True)
                    subprocess.run(["cmake", ".."], cwd=b_dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run(["make"], cwd=b_dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    built = True
                    build_root = b_dir # Update root to find exe here
                except: pass
            
            # Method D: Manual Compile (Fallback)
            if not built:
                src_files = []
                for r, d, f in os.walk(work_dir):
                    for file in f:
                        if file.endswith(".c") or file.endswith(".cpp"):
                            src_files.append(os.path.join(r, file))
                if src_files:
                    compiler = "g++" if any(f.endswith(".cpp") for f in src_files) else "gcc"
                    # Try to find common include paths
                    cmd = [compiler] + src_files + flags.split() + ["-o", "vuln", "-I", work_dir]
                    try:
                        subprocess.run(cmd, cwd=build_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except: pass

            # 4. Find the executable
            target_exe = None
            candidates = []
            for r, d, f in os.walk(work_dir):
                for file in f:
                    path = os.path.join(r, file)
                    if os.access(path, os.X_OK) and not path.endswith(".py") and not path.endswith(".sh") and not os.path.isdir(path):
                        candidates.append(path)
            
            # Prioritize newest file
            candidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            if candidates:
                target_exe = candidates[0]
            
            if not target_exe:
                # If build failed, return a dummy guess
                return b'\x40\x01\x12\x34' + b'A' * 17

            # 5. Fuzzing
            # Initial Seeds: CoAP Headers
            seeds = [
                b'\x40\x01\x00\x00', # CON GET
                b'\x50\x02\x12\x34', # NON POST
                b'\x60\x45\x00\x00', # ACK
                b"A" * 21
            ]
            # Generate more initial seeds
            base_seeds = list(seeds)
            for s in base_seeds:
                seeds.append(s + b'A' * 10)
                seeds.append(s + b'\xff' * 20)
            
            start_time = time.time()
            fuzz_limit = 25 # Seconds
            
            best_crash = None
            
            def check_input(inp):
                # Helper to run binary with input
                tf = tempfile.NamedTemporaryFile(delete=False)
                tf.write(inp)
                tf.close()
                path = tf.name
                crashed = False
                try:
                    # Try passing file as argument
                    p = subprocess.run([target_exe, path], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=0.5)
                    if p.returncode != 0 and b"AddressSanitizer" in p.stderr:
                        crashed = True
                    
                    # Try passing via stdin
                    if not crashed:
                        with open(path, 'rb') as f:
                            p = subprocess.run([target_exe], stdin=f, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=0.5)
                            if p.returncode != 0 and b"AddressSanitizer" in p.stderr:
                                crashed = True
                except:
                    pass
                finally:
                    if os.path.exists(path):
                        os.unlink(path)
                return inp if crashed else None

            # Run parallel fuzzing
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = {executor.submit(check_input, s): s for s in seeds}
                
                while time.time() - start_time < fuzz_limit:
                    done, _ = concurrent.futures.wait(futures, timeout=0.1, return_when=concurrent.futures.FIRST_COMPLETED)
                    
                    for f in done:
                        result = f.result()
                        original = futures.pop(f)
                        
                        if result:
                            best_crash = result
                            break # Found a crash
                        
                        # Add mutated tasks
                        if len(futures) < 16:
                            new_inp = self.mutate(original)
                            futures[executor.submit(check_input, new_inp)] = new_inp
                    
                    if best_crash:
                        break
                    
                    if len(futures) < 4:
                        # Refill if running low
                        s = random.choice(seeds)
                        futures[executor.submit(check_input, self.mutate(s))] = s

            if best_crash:
                return self.minimize(target_exe, best_crash)
            
            return b"A" * 21

        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def mutate(self, data: bytes) -> bytes:
        arr = bytearray(data)
        if not arr: return b'\x00'
        
        choice = random.randint(0, 4)
        idx = random.randint(0, len(arr)-1)
        
        if choice == 0: # Flip bit
            arr[idx] ^= (1 << random.randint(0, 7))
        elif choice == 1: # Replace byte
            arr[idx] = random.randint(0, 255)
        elif choice == 2: # Insert random byte
            arr.insert(idx, random.randint(0, 255))
        elif choice == 3: # Delete byte
            if len(arr) > 1:
                del arr[idx]
        elif choice == 4: # Append random byte
            arr.append(random.randint(0, 255))
        
        # Keep size reasonable for the problem
        if len(arr) > 60:
            arr = arr[:60]
            
        return bytes(arr)

    def minimize(self, exe: str, data: bytes) -> bytes:
        current = data
        
        def is_crash(d):
            tf = tempfile.NamedTemporaryFile(delete=False)
            tf.write(d)
            tf.close()
            c = False
            try:
                p = subprocess.run([exe, tf.name], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=0.5)
                if p.returncode != 0 and b"AddressSanitizer" in p.stderr:
                    c = True
                else:
                    with open(tf.name, 'rb') as f:
                        p = subprocess.run([exe], stdin=f, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=0.5)
                        if p.returncode != 0 and b"AddressSanitizer" in p.stderr:
                            c = True
            except: pass
            os.unlink(tf.name)
            return c

        # 1. Truncate from end
        while len(current) > 1:
            if is_crash(current[:-1]):
                current = current[:-1]
            else:
                break
        
        # 2. Remove bytes from middle
        i = 0
        while i < len(current):
            candidate = current[:i] + current[i+1:]
            if len(candidate) > 0 and is_crash(candidate):
                current = candidate
            else:
                i += 1
                
        return current
