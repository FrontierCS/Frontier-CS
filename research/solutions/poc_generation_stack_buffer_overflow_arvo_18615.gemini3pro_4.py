import os
import sys
import tarfile
import subprocess
import glob
import tempfile
import struct
import random
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp()
        
        try:
            # Extract source
            with tarfile.open(src_path) as tar:
                tar.extractall(path=work_dir)
            
            src_roots = glob.glob(os.path.join(work_dir, "binutils*"))
            if not src_roots:
                src_roots = glob.glob(os.path.join(work_dir, "*"))
            src_root = src_roots[0]
            if not os.path.isdir(src_root):
                 src_root = work_dir

            # Build directory
            build_dir = os.path.join(work_dir, "build")
            os.makedirs(build_dir, exist_ok=True)
            
            # Configure
            configure_script = os.path.join(src_root, "configure")
            try:
                os.chmod(configure_script, 0o755)
            except:
                pass

            cmd_config = [
                configure_script,
                "--target=tic30-unknown-coff",
                "--disable-nls",
                "--disable-werror",
                "--disable-gdb",
                "--disable-sim",
                "--disable-ld",
                "--disable-gas",
                "--disable-readline",
                "--disable-libdecnumber"
            ]
            
            subprocess.check_call(cmd_config, cwd=build_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Build opcodes library
            subprocess.check_call(["make", "-j8", "all-opcodes"], cwd=build_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Create Fuzzer Harness
            harness_code = r"""
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "bfd.h"
#include "dis-asm.h"

extern int print_insn_tic30 (bfd_vma, disassemble_info *);

unsigned char buffer[64];
unsigned int buf_len = 0;

int my_read_memory(bfd_vma memaddr, bfd_byte *myaddr, unsigned int length, struct disassemble_info *info) {
    if (memaddr + length > buf_len) return EIO;
    memcpy(myaddr, buffer + memaddr, length);
    return 0;
}

int main(int argc, char **argv) {
    setvbuf(stdout, NULL, _IONBF, 0);
    struct disassemble_info info;
    init_disassemble_info(&info, stdout, (fprintf_ftype) fprintf);
    info.arch = bfd_arch_tic30;
    info.mach = 0;
    info.read_memory_func = my_read_memory;
    info.buffer = buffer;
    info.buffer_vma = 0;
    info.endian = BFD_ENDIAN_BIG; 

    char line[256];
    while (fgets(line, sizeof(line), stdin)) {
        size_t len = strlen(line);
        if (len > 0 && line[len-1] == '\n') line[len-1] = 0;
        
        buf_len = 0;
        char *p = line;
        while (*p && *(p+1)) {
            unsigned int byte;
            if (sscanf(p, "%2x", &byte) == 1) {
                buffer[buf_len++] = (unsigned char)byte;
                p += 2;
            } else {
                break;
            }
        }
        info.buffer_length = buf_len;

        printf("Testing: %s\n", line);
        print_insn_tic30(0, &info);
    }
    return 0;
}
"""
            harness_path = os.path.join(build_dir, "fuzz_harness.c")
            with open(harness_path, "w") as f:
                f.write(harness_code)
            
            # Compile Harness
            inc_include = os.path.join(src_root, "include")
            inc_bfd_build = os.path.join(build_dir, "bfd")
            inc_bfd_src = os.path.join(src_root, "bfd")
            lib_opcodes = os.path.join(build_dir, "opcodes", "libopcodes.a")
            lib_bfd = os.path.join(build_dir, "bfd", "libbfd.a")
            lib_iberty = os.path.join(build_dir, "libiberty", "libiberty.a")
            
            exe_path = os.path.join(build_dir, "fuzz_harness")
            
            cmd_compile = [
                "gcc", "-o", exe_path, harness_path,
                f"-I{inc_include}", f"-I{inc_bfd_build}", f"-I{inc_bfd_src}",
                lib_opcodes, lib_bfd, lib_iberty, "-ldl"
            ]
            
            try:
                subprocess.check_call(cmd_compile + ["-lz"], cwd=build_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                subprocess.check_call(cmd_compile, cwd=build_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Generate Inputs
            inputs = []
            
            # 1. Random fuzzing
            for _ in range(1000):
                b = bytearray(random.getrandbits(8) for _ in range(10))
                inputs.append(b.hex())
            
            # 2. Structured fuzzing (Branch opcodes 0x60-0x6F)
            # Fuzz addressing mode byte (2nd byte)
            for op in range(0x60, 0x70):
                for byte2 in range(256):
                    for _ in range(2): # 2 random variations of trailing bytes
                        suffix = bytearray(random.getrandbits(8) for _ in range(8))
                        full = struct.pack(">BB", op, byte2) + suffix
                        inputs.append(full[:10].hex())

            input_file = os.path.join(build_dir, "inputs.txt")
            with open(input_file, "w") as f:
                for line in inputs:
                    f.write(line + "\n")
            
            # Run Fuzzer
            try:
                subprocess.check_output([exe_path], stdin=open(input_file, "r"), stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                # Crash detected
                output = e.output
                lines = output.strip().split(b'\n')
                for line in reversed(lines):
                    l = line.decode('utf-8', errors='ignore')
                    if "Testing:" in l:
                        hex_str = l.split("Testing:")[1].strip()
                        return bytes.fromhex(hex_str)
            
            # Fallback
            return bytes.fromhex("60800000000000000000")

        except Exception:
            # Fallback
            return bytes.fromhex("60800000000000000000")
        finally:
            shutil.rmtree(work_dir)