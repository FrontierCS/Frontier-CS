import os
import sys
import subprocess
import shutil
import glob
import re
import struct
import random
import time
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Use a temporary directory for the entire operation
        base_dir = os.path.abspath(os.getcwd())
        work_dir = tempfile.mkdtemp(prefix="work_tic30_")
        
        try:
            # Extract source
            subprocess.check_call(["tar", "xf", src_path, "-C", work_dir], 
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Find the extracted folder
            items = [x for x in os.listdir(work_dir) if not x.startswith('.')]
            if len(items) == 1 and os.path.isdir(os.path.join(work_dir, items[0])):
                src_root = os.path.join(work_dir, items[0])
            else:
                src_root = work_dir
            
            # Build Directory
            build_dir = os.path.join(work_dir, "build")
            os.makedirs(build_dir, exist_ok=True)
            
            # Environment for ASAN
            env = os.environ.copy()
            flags = "-g -O0 -fsanitize=address"
            env["CFLAGS"] = flags
            env["CXXFLAGS"] = flags
            env["LDFLAGS"] = flags
            
            # Locate configure script
            configure_script = os.path.join(src_root, "configure")
            if not os.path.exists(configure_script):
                for root, dirs, files in os.walk(src_root):
                    if "configure" in files:
                        configure_script = os.path.join(root, "configure")
                        break
            
            # Configure targeting tic30
            subprocess.check_call([
                configure_script,
                "--target=tic30-unknown-coff",
                "--disable-shared",
                "--disable-nls",
                "--disable-werror",
                "--disable-gdb",
                "--disable-sim",
                "--disable-readline",
                "--disable-libdecnumber"
            ], cwd=build_dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Build objdump
            subprocess.check_call(["make", "-j8", "all-binutils"], cwd=build_dir, env=env,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Find objdump binary
            objdump_bin = None
            for root, dirs, files in os.walk(build_dir):
                if "objdump" in files:
                    fpath = os.path.join(root, "objdump")
                    if os.access(fpath, os.X_OK):
                        objdump_bin = fpath
                        break
            
            if not objdump_bin:
                return b'\x60\x00\x00\x00' + b'\x00'*6

            # Extract Seeds from tic30-dis.c
            seeds = set()
            tic30_dis_c = None
            for root, dirs, files in os.walk(src_root):
                if "tic30-dis.c" in files:
                    tic30_dis_c = os.path.join(root, "tic30-dis.c")
                    break
            
            if tic30_dis_c:
                with open(tic30_dis_c, "r", errors="ignore") as f:
                    content = f.read()
                    lines = content.splitlines()
                    for line in lines:
                        if "print_branch" in line:
                            found = re.findall(r'0x[0-9a-fA-F]+', line)
                            for hex_str in found:
                                try:
                                    val = int(hex_str, 16)
                                    # Filter likely masks
                                    if val < 0xFF000000:
                                        seeds.add(val)
                                except:
                                    pass
            
            seed_list = list(seeds) if seeds else [0x60000000]
            
            # Helper to check crash
            def check(data):
                tfd, tpath = tempfile.mkstemp()
                os.write(tfd, data)
                os.close(tfd)
                try:
                    # Run objdump on raw binary with tic30 architecture
                    proc = subprocess.run(
                        [objdump_bin, "-D", "-b", "binary", "-m", "tic30", tpath],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        timeout=1
                    )
                    if proc.returncode != 0:
                        err = proc.stderr.decode(errors='ignore')
                        if "AddressSanitizer" in err:
                            return True
                except:
                    pass
                finally:
                    if os.path.exists(tpath):
                        os.remove(tpath)
                return False

            # Fuzzing Phase
            # 1. Direct seeds
            for s in seed_list:
                # Big Endian
                chunk = struct.pack('>I', s)
                payload = chunk + b'\x00'*6
                if check(payload): return payload
                
                # Little Endian
                chunk_le = struct.pack('<I', s)
                payload = chunk_le + b'\x00'*6
                if check(payload): return payload

            # 2. Mutated seeds
            start_time = time.time()
            while time.time() - start_time < 20: 
                s = random.choice(seed_list)
                base = bytearray(struct.pack('>I', s))
                
                # Bit flips in operand area
                idx = random.choice([2, 3])
                base[idx] ^= (1 << random.randint(0, 7))
                
                payload = bytes(base) + os.urandom(6)
                if check(payload): return payload
                
            # 3. Random fallback
            for _ in range(200):
                payload = os.urandom(10)
                if check(payload): return payload

            return struct.pack('>I', seed_list[0]) + b'\x00'*6

        except Exception:
            return b'\x60\x00\x00\x00' + b'\x00'*6
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)