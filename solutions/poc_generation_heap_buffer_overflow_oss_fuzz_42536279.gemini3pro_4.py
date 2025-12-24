import os
import sys
import tarfile
import subprocess
import tempfile
import shutil
import random
import glob
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Prepare Source Code
            extract_dir = os.path.join(temp_dir, "source")
            os.makedirs(extract_dir, exist_ok=True)
            
            if os.path.isfile(src_path):
                # Attempt extraction
                try:
                    mode = "r:gz" if src_path.endswith(('.tar.gz', '.tgz')) else "r:"
                    if not src_path.endswith(('.tar.gz', '.tgz', '.tar')):
                        mode = "r"
                    with tarfile.open(src_path, mode) as tar:
                        tar.extractall(path=extract_dir)
                except Exception:
                    # If extraction fails or file is not a tar, proceed only if it's a directory (unlikely here)
                    return b""
            elif os.path.isdir(src_path):
                shutil.copytree(src_path, extract_dir, dirs_exist_ok=True)
            else:
                return b""

            # Normalize source root (handle tarballs that contain a single top-level directory)
            src_root = extract_dir
            entries = os.listdir(src_root)
            if len(entries) == 1 and os.path.isdir(os.path.join(src_root, entries[0])):
                src_root = os.path.join(src_root, entries[0])

            # 2. Build Vulnerable Binary with ASAN
            # We target OpenH264's decoder (h264dec)
            # We assume clang is present for ASan support.
            
            # Clean up potential previous builds if any (though unlikely in temp)
            # Build command
            build_cmd = [
                "make", "-j8",
                "OS=linux", "ARCH=x86_64", "USE_ASM=No",
                "CC=clang", "CXX=clang++",
                "CFLAGS=-fsanitize=address -g -O1 -fno-omit-frame-pointer",
                "CXXFLAGS=-fsanitize=address -g -O1 -fno-omit-frame-pointer",
                "LDFLAGS=-fsanitize=address",
                "h264dec"
            ]
            
            try:
                subprocess.call(build_cmd, cwd=src_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

            # Locate the binary
            binary_path = None
            for name in ["h264dec", "svcdec", "decConsole"]:
                candidates = glob.glob(os.path.join(src_root, "**", name), recursive=True)
                for c in candidates:
                    if os.access(c, os.X_OK):
                        binary_path = c
                        break
                if binary_path: break
            
            if not binary_path:
                return b""

            # 3. Collect Seeds
            seeds = []
            seed_files = glob.glob(os.path.join(src_root, "**", "*.264"), recursive=True)
            # Include other potential extensions
            seed_files.extend(glob.glob(os.path.join(src_root, "**", "*.h264"), recursive=True))
            
            for sf in seed_files:
                try:
                    with open(sf, "rb") as f:
                        data = f.read()
                        if data:
                            seeds.append(data)
                except:
                    pass
            
            # Fallback seed if none found
            if not seeds:
                # A minimal H.264 stream
                seeds.append(bytes.fromhex("000000016742000af841a20000000168ce388000000001658884"))

            # 4. Fuzzing Loop
            start_time = time.time()
            time_limit = 120 # Seconds to find the PoC
            rng = random.Random(42536279) # Seed for reproducibility
            
            # Helper to check for crash
            def check_crash(data):
                tpath = os.path.join(temp_dir, "crash_test.264")
                with open(tpath, "wb") as f:
                    f.write(data)
                
                try:
                    proc = subprocess.run(
                        [binary_path, tpath],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        timeout=1.0 # Short timeout for video decoding
                    )
                    
                    if proc.returncode != 0:
                        stderr_out = proc.stderr.decode(errors='ignore')
                        # We specifically want heap buffer overflow, but any ASan crash indicates success for PoC gen
                        if "AddressSanitizer" in stderr_out:
                            return True
                except subprocess.TimeoutExpired:
                    pass
                except Exception:
                    pass
                return False

            # First pass: Check existing seeds (unlikely to crash but good baseline)
            for s in seeds:
                if check_crash(s):
                    return s

            # Second pass: Mutation
            while time.time() - start_time < time_limit:
                base_seed = rng.choice(seeds)
                mutated = bytearray(base_seed)
                
                mutation_type = rng.random()
                
                if mutation_type < 0.5:
                    # Random bit flips
                    num_flips = rng.randint(1, 16)
                    for _ in range(num_flips):
                        idx = rng.randint(0, len(mutated) - 1)
                        bit = rng.randint(0, 7)
                        mutated[idx] ^= (1 << bit)
                
                elif mutation_type < 0.8:
                    # Byte overwrites (try to disrupt headers/dimensions)
                    num_bytes = rng.randint(1, 8)
                    start_idx = rng.randint(0, max(0, len(mutated) - num_bytes))
                    for i in range(num_bytes):
                        mutated[start_idx + i] = rng.randint(0, 255)
                        
                else:
                    # Chunk duplication / shuffle (good for creating mismatched layer dimensions)
                    if len(mutated) > 20:
                        chunk_len = rng.randint(4, 64)
                        src_idx = rng.randint(0, len(mutated) - chunk_len)
                        chunk = mutated[src_idx : src_idx + chunk_len]
                        
                        dst_idx = rng.randint(0, len(mutated))
                        mutated[dst_idx : dst_idx] = chunk

                poc_bytes = bytes(mutated)
                if check_crash(poc_bytes):
                    return poc_bytes
            
            # If we time out, return a seed to ensure we return bytes
            return seeds[0]
