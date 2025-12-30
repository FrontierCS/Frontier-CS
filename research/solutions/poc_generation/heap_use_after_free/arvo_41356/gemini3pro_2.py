import os
import sys
import subprocess
import tempfile
import tarfile
import shutil
import random
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        temp_dir = tempfile.mkdtemp()
        try:
            # 1. Extract source
            with tarfile.open(src_path) as tar:
                tar.extractall(path=temp_dir)
            
            # Find actual source root
            src_root = temp_dir
            for item in os.listdir(temp_dir):
                full_path = os.path.join(temp_dir, item)
                if os.path.isdir(full_path) and not item.startswith('.'):
                    src_root = full_path
                    break
            
            # 2. Setup build environment
            env = os.environ.copy()
            flags = "-fsanitize=address -g"
            env["CFLAGS"] = flags
            env["CXXFLAGS"] = flags
            env["CC"] = "clang"
            env["CXX"] = "clang++"

            build_dir = os.path.join(src_root, "build_sol")
            os.makedirs(build_dir, exist_ok=True)

            # 3. Build the project
            # Attempt CMake
            if os.path.exists(os.path.join(src_root, "CMakeLists.txt")):
                subprocess.run(
                    ["cmake", "..", "-DBUILD_SHARED_LIBS=OFF"], 
                    cwd=build_dir, env=env, 
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                subprocess.run(
                    ["make", "-j8"], 
                    cwd=build_dir, env=env, 
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            # Attempt Make
            elif os.path.exists(os.path.join(src_root, "Makefile")):
                subprocess.run(
                    ["make", "-j8"], 
                    cwd=src_root, env=env, 
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                build_dir = src_root

            # 4. Identify Fuzzing Target
            target_bin = None
            
            # 4a. Look for existing fuzz executables
            candidates = []
            for root, _, files in os.walk(src_root):
                for f in files:
                    path = os.path.join(root, f)
                    if os.access(path, os.X_OK) and not f.endswith((".sh", ".py", ".o", ".a", ".so")):
                        candidates.append(path)
            
            # Prioritize binaries with "fuzz" in name
            for c in candidates:
                if "fuzz" in os.path.basename(c).lower():
                    target_bin = c
                    break
            
            # 4b. If no fuzz binary found, try to compile a custom driver
            if not target_bin:
                fuzz_src = None
                # Search for LLVMFuzzerTestOneInput source file
                for root, _, files in os.walk(src_root):
                    for f in files:
                        if f.endswith((".cc", ".cpp", ".c")):
                            try:
                                with open(os.path.join(root, f), "r", errors="ignore") as fp:
                                    if "LLVMFuzzerTestOneInput" in fp.read():
                                        fuzz_src = os.path.join(root, f)
                                        break
                            except: pass
                    if fuzz_src: break
                
                if fuzz_src:
                    # Find static library to link against
                    libs = []
                    for root, _, files in os.walk(src_root):
                        for f in files:
                            if f.endswith(".a"):
                                libs.append(os.path.join(root, f))
                    # Pick the largest library, likely the main one
                    libs.sort(key=lambda x: os.path.getsize(x), reverse=True)
                    
                    if libs:
                        driver_path = os.path.join(temp_dir, "driver.cpp")
                        with open(driver_path, "w") as d:
                            d.write("""
#include <cstdint>
#include <vector>
#include <fstream>
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size);
int main(int argc, char **argv) {
    if (argc < 2) return 0;
    std::ifstream f(argv[1], std::ios::binary);
    std::vector<uint8_t> buf((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
    LLVMFuzzerTestOneInput(buf.data(), buf.size());
    return 0;
}
""")
                        out_bin = os.path.join(temp_dir, "fuzzer_custom")
                        
                        # Find include directories
                        inc_flags = []
                        for root, dirs, _ in os.walk(src_root):
                            if "include" in dirs:
                                inc_flags.append("-I" + os.path.join(root, "include"))
                        if not inc_flags:
                            inc_flags = ["-I" + src_root]
                        
                        # Compile driver
                        cmd = ["clang++", "-fsanitize=address", "-g", driver_path, fuzz_src, libs[0], "-o", out_bin] + inc_flags + ["-lpthread"]
                        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        
                        if os.path.exists(out_bin):
                            target_bin = out_bin

            # 4c. Fallback to any executable found
            if not target_bin and candidates:
                target_bin = candidates[0]
            
            if not target_bin:
                return b""

            # 5. Fuzz
            seeds = [b"{}", b"[]", b"", b"- ", b"key: val", b"? k : v", b"&a [*a]", b"!!str"]
            # Extract seeds from source tests
            for root, _, files in os.walk(src_root):
                for f in files:
                    if f.endswith((".yaml", ".yml", ".json")):
                        try:
                            with open(os.path.join(root, f), "rb") as fp:
                                seeds.append(fp.read(512))
                        except: pass

            end_time = time.time() + 60
            while time.time() < end_time:
                seed = bytearray(random.choice(seeds))
                if not seed: seed = bytearray(b" ")
                
                # Mutate
                if random.random() < 0.8:
                    op = random.randint(0, 2)
                    idx = random.randint(0, len(seed)-1)
                    if op == 0: seed[idx] ^= random.randint(1, 255)
                    elif op == 1: seed.insert(idx, random.randint(32, 126))
                    elif op == 2 and len(seed) > 1: del seed[idx]
                
                payload = bytes(seed)
                with tempfile.NamedTemporaryFile(delete=False) as tf:
                    tf.write(payload)
                    tf_name = tf.name
                
                try:
                    p = subprocess.run([target_bin, tf_name], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=1)
                    if p.returncode != 0:
                        err = p.stderr.decode(errors="ignore")
                        if "AddressSanitizer" in err:
                            os.unlink(tf_name)
                            return payload
                except:
                    pass
                
                if os.path.exists(tf_name):
                    os.unlink(tf_name)
            
            return b""
        except:
            return b""
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)