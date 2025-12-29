import os
import sys
import tarfile
import tempfile
import subprocess
import shutil
import struct
import random
import time
from concurrent.futures import ThreadPoolExecutor

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a temporary directory for build and fuzzing
        base_dir = tempfile.mkdtemp()
        try:
            # 1. Extract Source
            if os.path.isfile(src_path):
                try:
                    with tarfile.open(src_path) as tar:
                        tar.extractall(path=base_dir)
                except Exception:
                    pass
                # Locate the root of the extracted source
                entries = os.listdir(base_dir)
                possible_root = os.path.join(base_dir, entries[0])
                if len(entries) == 1 and os.path.isdir(possible_root):
                    src_root = possible_root
                else:
                    src_root = base_dir
            else:
                src_root = src_path

            # 2. Compile UPX with ASAN
            # Locate Makefile
            makefile_dir = src_root
            if not os.path.exists(os.path.join(src_root, "Makefile")):
                if os.path.exists(os.path.join(src_root, "src", "Makefile")):
                    makefile_dir = os.path.join(src_root, "src")
            
            # Setup Environment
            env = os.environ.copy()
            flags = "-fsanitize=address,undefined -g -O1"
            env["CXX"] = "clang++"
            env["CC"] = "clang"
            env["CXXFLAGS"] = flags
            env["CFLAGS"] = flags
            env["LDFLAGS"] = flags

            # Run make
            try:
                subprocess.run(
                    ["make", "-j8"], 
                    cwd=makefile_dir, 
                    env=env, 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL,
                    timeout=300 
                )
            except Exception:
                pass

            # Find the UPX binary
            upx_bin = None
            for root, dirs, files in os.walk(src_root):
                if "upx.out" in files:
                    upx_bin = os.path.join(root, "upx.out")
                    break
                if "upx" in files:
                    p = os.path.join(root, "upx")
                    if os.access(p, os.X_OK):
                        upx_bin = p
                        break
            
            if not upx_bin:
                return b'A' * 512

            # 3. Create Seed Input (ELF Shared Library)
            seed_src = os.path.join(base_dir, "seed.c")
            seed_so = os.path.join(base_dir, "seed.so")
            packed_so = os.path.join(base_dir, "packed.so")

            with open(seed_src, "w") as f:
                f.write("int test(){return 0;}")

            # Compile to shared object
            has_gcc = shutil.which("gcc") is not None
            if has_gcc:
                try:
                    subprocess.run(
                        ["gcc", "-shared", "-fPIC", "-o", seed_so, seed_src],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=True
                    )
                except:
                    return b'A' * 512
            else:
                return b'A' * 512

            # Pack with UPX
            try:
                subprocess.run(
                    [upx_bin, "-1", "-f", "-o", packed_so, seed_so],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=10,
                    check=True
                )
            except:
                return b'A' * 512

            with open(packed_so, "rb") as f:
                seed_data = f.read()

            # 4. Fuzzing
            found_poc = None
            
            def fuzz_worker(worker_id):
                nonlocal found_poc
                rng = random.Random()
                rng.seed(worker_id + time.time())
                
                for _ in range(500):
                    if found_poc is not None:
                        return

                    # Mutation Strategy
                    curr_data = bytearray(seed_data)
                    choice = rng.random()
                    
                    if choice < 0.2:
                        # Truncation
                        if len(curr_data) > 64:
                            sz = rng.randint(64, len(curr_data))
                            curr_data = curr_data[:sz]
                    elif choice < 0.6:
                        # Byte corruption
                        count = rng.randint(1, 10)
                        for _ in range(count):
                            idx = rng.randint(0, len(curr_data)-1)
                            curr_data[idx] = rng.randint(0, 255)
                    else:
                        # Integer overwrites
                        count = rng.randint(1, 4)
                        vals = [0, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF, 0xFFFF, 0xFFFFFFFE]
                        for _ in range(count):
                            if len(curr_data) >= 4:
                                idx = rng.randint(0, len(curr_data)-4)
                                val = rng.choice(vals)
                                try:
                                    struct.pack_into("<I", curr_data, idx, val)
                                except:
                                    pass

                    tmp_name = os.path.join(base_dir, f"fuzz_{worker_id}.out")
                    try:
                        with open(tmp_name, "wb") as f:
                            f.write(curr_data)
                    except:
                        continue

                    # Execute upx -d (decompression)
                    try:
                        res = subprocess.run(
                            [upx_bin, "-d", "-o", os.devnull, tmp_name],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE,
                            timeout=0.5
                        )
                        if res.returncode != 0:
                            err = res.stderr.decode(errors='ignore')
                            if "AddressSanitizer" in err or "heap-buffer-overflow" in err:
                                found_poc = bytes(curr_data)
                                return
                    except subprocess.TimeoutExpired:
                        pass
                    except Exception:
                        pass
            
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(fuzz_worker, i) for i in range(8)]
                for f in futures:
                    f.result()
            
            if found_poc:
                return found_poc
            
            return seed_data

        except Exception:
            return b'A' * 512
        finally:
            shutil.rmtree(base_dir, ignore_errors=True)