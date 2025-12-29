import sys
import os
import subprocess
import tempfile
import shutil
import random
import struct
import tarfile
import glob
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        base_dir = tempfile.mkdtemp()
        try:
            # Extract source
            with tarfile.open(src_path) as tar:
                tar.extractall(path=base_dir)
            
            src_root = base_dir
            entries = os.listdir(base_dir)
            if len(entries) == 1 and os.path.isdir(os.path.join(base_dir, entries[0])):
                src_root = os.path.join(base_dir, entries[0])
            
            exe_path = os.path.join(src_root, "fuzz_target")
            built = False
            
            # Attempt 1: Manual Compilation (Fastest and most controlled for single binary)
            sources = []
            for root, dirs, files in os.walk(src_root):
                for f in files:
                    if f.endswith(".cc"):
                        # Exclude tests, demos, and woff2 (to avoid brotli dep issues)
                        path = os.path.join(root, f)
                        if "test" in path or "demo" in path or "fuzz" in path:
                            continue
                        if "woff2" in path:
                            continue
                        sources.append(path)
            
            main_src = None
            for s in sources:
                if "ots-sanitize.cc" in s:
                    main_src = s
                    break
            
            if main_src:
                inc_src = os.path.join(src_root, "src")
                inc_inc = os.path.join(src_root, "include")
                
                # Compile command
                cmd = [
                    "g++", "-fsanitize=address", "-g", "-O1", 
                    "-I", inc_src, "-I", inc_inc, 
                    "-DOTS_DEBUG",
                    main_src
                ] + [s for s in sources if s != main_src] + ["-lz", "-o", exe_path]
                
                try:
                    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
                    if os.path.exists(exe_path):
                        built = True
                except subprocess.CalledProcessError:
                    pass

            # Attempt 2: Autotools/Configure (Fallback)
            if not built:
                if os.path.exists(os.path.join(src_root, "configure")) or os.path.exists(os.path.join(src_root, "autogen.sh")):
                     try:
                        if os.path.exists(os.path.join(src_root, "autogen.sh")):
                             subprocess.run(["sh", "autogen.sh"], cwd=src_root, stderr=subprocess.DEVNULL)
                        
                        env = os.environ.copy()
                        env["CXXFLAGS"] = "-fsanitize=address -g -O0"
                        env["LDFLAGS"] = "-fsanitize=address"
                        subprocess.run(["./configure"], cwd=src_root, env=env, stderr=subprocess.DEVNULL)
                        subprocess.run(["make", "-j4"], cwd=src_root, env=env, stderr=subprocess.DEVNULL)
                        
                        for r, d, f in os.walk(src_root):
                            if "ots-sanitize" in f:
                                cand = os.path.join(r, "ots-sanitize")
                                if os.access(cand, os.X_OK):
                                    exe_path = cand
                                    built = True
                                    break
                     except: pass

            if not built:
                return self.generate_fallback()

            # Construct a robust seed: SFNT with head, hhea, maxp, hmtx
            # This ensures we pass basic checks and reach deep sanitation logic where Write UAFs often live.
            seed = bytearray()
            # SFNT Header
            seed += struct.pack(">I", 0x00010000) # version
            seed += struct.pack(">H", 4) # numTables
            seed += struct.pack(">H", 32) # searchRange
            seed += struct.pack(">H", 2) # entrySelector
            seed += struct.pack(">H", 0) # rangeShift
            
            # Directory
            # offsets: header=12, dir=16*4=64. Data starts at 76 (0x4C)
            offset = 76
            
            # 1. head
            seed += b'head'
            seed += b'\x00\x00\x00\x00' # checksum
            seed += struct.pack(">I", offset)
            seed += struct.pack(">I", 54)
            offset += 54 + 2 # + padding
            
            # 2. hhea
            seed += b'hhea'
            seed += b'\x00\x00\x00\x00'
            seed += struct.pack(">I", offset)
            seed += struct.pack(">I", 36)
            offset += 36 + 2
            
            # 3. maxp
            seed += b'maxp'
            seed += b'\x00\x00\x00\x00'
            seed += struct.pack(">I", offset)
            seed += struct.pack(">I", 6)
            offset += 6 + 2
            
            # 4. hmtx
            seed += b'hmtx'
            seed += b'\x00\x00\x00\x00'
            seed += struct.pack(">I", offset)
            seed += struct.pack(">I", 100) # Arbitrary size for hmtx
            offset += 100
            
            # Data construction
            
            # head data (54 bytes)
            head_data = bytearray(54)
            struct.pack_into(">I", head_data, 12, 0x5F0F3CF5) # magic
            struct.pack_into(">H", head_data, 18, 2048) # unitsPerEm
            struct.pack_into(">H", head_data, 44, 0) # indexToLocFormat
            seed += head_data + b'\x00\x00'
            
            # hhea data (36 bytes)
            hhea_data = bytearray(36)
            struct.pack_into(">I", hhea_data, 0, 0x00010000) # version
            struct.pack_into(">H", hhea_data, 34, 1) # numOfLongHorMetrics
            seed += hhea_data + b'\x00\x00'
            
            # maxp data (6 bytes)
            maxp_data = struct.pack(">IH", 0x00010000, 1) # version, numGlyphs
            seed += maxp_data + b'\x00\x00'
            
            # hmtx data
            seed += b'\x00' * 100

            best_input = seed
            start_time = time.time()
            
            # Fuzz for 50 seconds max
            while time.time() - start_time < 50:
                curr = bytearray(best_input)
                
                # Mutation
                mutations = random.randint(1, 4)
                for _ in range(mutations):
                    m = random.randint(0, 4)
                    if m == 0: # Byte flip
                        idx = random.randint(0, len(curr)-1)
                        curr[idx] ^= random.randint(1, 255)
                    elif m == 1: # Bit flip
                        idx = random.randint(0, len(curr)-1)
                        bit = random.randint(0, 7)
                        curr[idx] ^= (1 << bit)
                    elif m == 2: # Integer overwrite (targeting lengths/offsets)
                        if len(curr) > 4:
                            idx = random.randint(0, len(curr)-4)
                            val = random.choice([0, 0xFFFFFFFF, 0x7FFFFFFF, 0x80000000, random.randint(0, 65535)])
                            struct.pack_into(">I", curr, idx, val)
                    elif m == 3: # Small chunks havoc
                        idx = random.randint(0, len(curr)-1)
                        chunk_len = random.randint(1, 4)
                        for k in range(chunk_len):
                            if idx+k < len(curr):
                                curr[idx+k] = random.randint(0, 255)
                    elif m == 4: # Insert junk
                        idx = random.randint(0, len(curr))
                        curr[idx:idx] = os.urandom(random.randint(1, 10))

                with tempfile.NamedTemporaryFile(delete=False) as tf:
                    tf.write(curr)
                    tf_name = tf.name
                
                try:
                    res = subprocess.run([exe_path, tf_name], capture_output=True, timeout=1)
                    if res.returncode != 0:
                        err = res.stderr.decode('utf-8', 'ignore')
                        # Check for UAF
                        if "AddressSanitizer" in err and "heap-use-after-free" in err:
                            os.unlink(tf_name)
                            return bytes(curr)
                except:
                    pass
                finally:
                    if os.path.exists(tf_name):
                        os.unlink(tf_name)
            
            return bytes(seed)

        except Exception:
            return self.generate_fallback()
        finally:
            shutil.rmtree(base_dir)

    def generate_fallback(self) -> bytes:
        return b'\x00\x01\x00\x00' + b'\x00'*200