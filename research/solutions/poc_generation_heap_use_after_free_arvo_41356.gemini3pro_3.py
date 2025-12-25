import os
import sys
import tarfile
import subprocess
import shutil
import random
import time
import re
import glob

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Working directories
        base_dir = "/tmp/work_arvo_poc"
        if os.path.exists(base_dir):
            shutil.rmtree(base_dir)
        os.makedirs(base_dir)
        
        src_dir = os.path.join(base_dir, "src")
        os.makedirs(src_dir)
        out_dir = os.path.join(base_dir, "out")
        os.makedirs(out_dir)
        work_dir = os.path.join(base_dir, "work")
        os.makedirs(work_dir)
        
        # Extract source
        try:
            with tarfile.open(src_path) as tar:
                tar.extractall(path=src_dir)
        except Exception:
            return b""
            
        # Locate project root
        project_root = src_dir
        entries = os.listdir(src_dir)
        if len(entries) == 1 and os.path.isdir(os.path.join(src_dir, entries[0])):
            project_root = os.path.join(src_dir, entries[0])
            
        # Create Fuzz Driver (Generic main for LLVMFuzzerTestOneInput)
        driver_path = os.path.join(base_dir, "driver.cpp")
        driver_obj = os.path.join(base_dir, "driver.o")
        driver_lib = os.path.join(base_dir, "libFuzzingEngine.a")
        
        with open(driver_path, "w") as f:
            f.write(r"""
#include <iostream>
#include <fstream>
#include <vector>
#include <cstdint>

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size);

int main(int argc, char** argv) {
    for (int i = 1; i < argc; i++) {
        std::ifstream file(argv[i], std::ios::binary | std::ios::ate);
        if (!file) continue;
        std::streamsize size = file.tellg();
        file.seekg(0, std::ios::beg);
        std::vector<uint8_t> buffer(size);
        if (file.read((char*)buffer.data(), size)) {
            LLVMFuzzerTestOneInput(buffer.data(), buffer.size());
        }
    }
    return 0;
}
""")

        # Build Environment
        env = os.environ.copy()
        env['CC'] = "clang"
        env['CXX'] = "clang++"
        cflags = "-g -O1 -fsanitize=address -fno-omit-frame-pointer"
        env['CFLAGS'] = cflags
        env['CXXFLAGS'] = cflags
        env['SRC'] = project_root
        env['WORK'] = work_dir
        env['OUT'] = out_dir
        env['LIB_FUZZING_ENGINE'] = driver_lib
        
        # Compile driver
        try:
            subprocess.run(["clang++", "-c", driver_path, "-o", driver_obj, "-O1"], check=True, stderr=subprocess.DEVNULL)
            subprocess.run(["ar", "r", driver_lib, driver_obj], check=True, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            pass

        # Build Target
        built = False
        
        # 1. Check for build.sh (OSS-Fuzz style)
        build_sh = os.path.join(project_root, "build.sh")
        if os.path.exists(build_sh):
            try:
                subprocess.run(["bash", build_sh], cwd=project_root, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                built = True
            except subprocess.CalledProcessError:
                pass
                
        # 2. Check for CMake
        if not built and os.path.exists(os.path.join(project_root, "CMakeLists.txt")):
            build_dir = os.path.join(project_root, "build")
            os.makedirs(build_dir, exist_ok=True)
            try:
                # Try to configure with ASAN
                cmd = ["cmake", "..", "-DCMAKE_CXX_FLAGS=" + cflags, "-DCMAKE_C_FLAGS=" + cflags]
                subprocess.run(cmd, cwd=build_dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["make", "-j8"], cwd=build_dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                built = True
                # Collect binaries
                for root, _, files in os.walk(build_dir):
                    for f in files:
                        path = os.path.join(root, f)
                        if os.access(path, os.X_OK) and not f.endswith('.so') and not f.endswith('.a'):
                            try:
                                shutil.copy(path, out_dir)
                            except: pass
            except: pass
            
        # 3. Check for Makefile
        if not built and (os.path.exists(os.path.join(project_root, "Makefile")) or os.path.exists(os.path.join(project_root, "makefile"))):
            try:
                subprocess.run(["make", "-j8"], cwd=project_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                built = True
                # Collect binaries
                for root, _, files in os.walk(project_root):
                    for f in files:
                        path = os.path.join(root, f)
                        if os.access(path, os.X_OK) and not f.endswith('.so') and not f.endswith('.a'):
                             if "build" not in path:
                                try:
                                    shutil.copy(path, out_dir)
                                except: pass
            except: pass

        # Identify Fuzz Target
        candidates = []
        # Check $OUT
        for f in os.listdir(out_dir):
            path = os.path.join(out_dir, f)
            if os.access(path, os.X_OK) and not os.path.isdir(path) and not f.endswith('.sh'):
                candidates.append(path)
        
        # Filter candidates
        # Prefer names with 'fuzz', 'test', 'arvo', 'json'
        filtered = []
        for c in candidates:
            name = os.path.basename(c).lower()
            if any(x in name for x in ['fuzz', 'test', 'run', 'arvo', 'json']):
                filtered.append(c)
        
        if filtered:
            candidates = filtered
        
        # Sort candidates
        candidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        if not candidates:
            return b""
            
        target_bin = candidates[0]
        
        # Harvest Seeds
        seeds = [b"A", b"{}", b"[]", b'{"a":1}', b'[1,2]']
        dictionary = []
        
        # Read from source
        for root, _, files in os.walk(project_root):
            for f in files:
                path = os.path.join(root, f)
                # Seed from files
                if f.endswith(('.json', '.txt')):
                    try:
                        with open(path, 'rb') as fd:
                            d = fd.read()
                            if 0 < len(d) < 2000:
                                seeds.append(d)
                    except: pass
                # Dict from strings
                if f.endswith(('.c', '.cc', '.cpp', '.h', '.hpp')):
                     try:
                         with open(path, 'r', encoding='latin-1') as fd:
                             c = fd.read()
                             matches = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', c)
                             for m in matches:
                                 if len(m) < 40:
                                     dictionary.append(m.encode('utf-8', 'ignore'))
                     except: pass
        
        # Fuzz Loop
        start_time = time.time()
        timeout = 240 # Run for up to 4 minutes
        
        # Ensure ASAN Options
        run_env = env.copy()
        run_env['ASAN_OPTIONS'] = "detect_leaks=0:abort_on_error=1:symbolize=0"
        
        fuzz_input_path = os.path.join(base_dir, "fuzz_input")
        
        # Pre-check seeds
        for s in seeds:
            with open(fuzz_input_path, "wb") as f:
                f.write(s)
            try:
                proc = subprocess.run([target_bin, fuzz_input_path], env=run_env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=1)
                if proc.returncode != 0:
                    err = proc.stderr.decode('latin-1', 'ignore')
                    if "AddressSanitizer" in err and ("heap-use-after-free" in err or "double-free" in err):
                        return s
            except: pass
            
        # Mutate
        while time.time() - start_time < timeout:
            seed = random.choice(seeds)
            mutated = self.mutate(seed, dictionary)
            
            with open(fuzz_input_path, "wb") as f:
                f.write(mutated)
            
            try:
                proc = subprocess.run([target_bin, fuzz_input_path], env=run_env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=0.5)
                if proc.returncode != 0:
                    err = proc.stderr.decode('latin-1', 'ignore')
                    if "AddressSanitizer" in err and ("heap-use-after-free" in err or "double-free" in err):
                        return mutated
            except subprocess.TimeoutExpired:
                pass
            except Exception:
                pass
                
        return b""

    def mutate(self, data, dictionary):
        if not data: data = b" "
        data = bytearray(data)
        op = random.randint(0, 5)
        
        if op == 0 and dictionary:
             pos = random.randint(0, len(data))
             word = random.choice(dictionary)
             data[pos:pos] = word
        elif op == 1: # Flip
            if data:
                p = random.randint(0, len(data)-1)
                data[p] ^= random.randint(1, 255)
        elif op == 2: # Replace
             if data:
                p = random.randint(0, len(data)-1)
                data[p] = random.randint(0, 255)
        elif op == 3: # Delete
            if len(data) > 1:
                l = random.randint(1, min(5, len(data)))
                p = random.randint(0, len(data)-l)
                del data[p:p+l]
        elif op == 4: # Copy/Repeat
            if len(data) > 0:
                l = random.randint(1, min(5, len(data)))
                p = random.randint(0, len(data)-l)
                chunk = data[p:p+l]
                data[p:p] = chunk
        elif op == 5: # Insert structure
             chars = b"{}[],:\""
             p = random.randint(0, len(data))
             data.insert(p, random.choice(chars))
             
        return bytes(data)
