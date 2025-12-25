import os
import sys
import tarfile
import subprocess
import shutil
import tempfile
import struct
import random
import concurrent.futures
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp()
        try:
            # 1. Extract source code
            with tarfile.open(src_path) as tar:
                tar.extractall(work_dir)
            
            src_root = work_dir
            for root, dirs, files in os.walk(work_dir):
                if 'Makefile' in files:
                    src_root = root
                    break
            
            # 2. Build UPX with AddressSanitizer
            env = os.environ.copy()
            asan_flags = "-fsanitize=address -g -O1"
            env['CXX'] = "g++"
            env['CC'] = "gcc"
            env['CFLAGS'] = asan_flags
            env['CXXFLAGS'] = asan_flags
            env['LDFLAGS'] = asan_flags
            
            # Attempt to build
            try:
                subprocess.check_call(['make', '-j8'], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                # Try building in src subdirectory if root fails
                src_subdir = os.path.join(src_root, 'src')
                if os.path.isdir(src_subdir):
                    try:
                        subprocess.check_call(['make', '-j8'], cwd=src_subdir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except:
                        pass

            # Locate the compiled binary
            upx_bin = None
            for root, dirs, files in os.walk(src_root):
                for name in ['upx', 'upx.out']:
                    if name in files:
                        path = os.path.join(root, name)
                        if os.access(path, os.X_OK):
                            try:
                                subprocess.check_call([path, '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                upx_bin = path
                                break
                            except:
                                continue
                if upx_bin: break
            
            if not upx_bin:
                # Failed to build, return placeholder
                return b'A' * 512

            # 3. Create a seed file (Packed ELF)
            # Create a C file with a constructor to trigger DT_INIT logic
            source_c = os.path.join(work_dir, "vuln.c")
            with open(source_c, "w") as f:
                f.write("void __attribute__((constructor)) init() {}\nint main() { return 0; }")
            
            seed_elf = os.path.join(work_dir, "seed_elf")
            subprocess.check_call(['gcc', '-o', seed_elf, source_c], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            packed_elf = os.path.join(work_dir, "packed_elf")
            subprocess.check_call([upx_bin, '-f', '-o', packed_elf, seed_elf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            with open(packed_elf, 'rb') as f:
                seed_data = f.read()

            # 4. Fuzzing Loop
            crashes = []

            def check_poc(data):
                fd, path = tempfile.mkstemp(dir=work_dir)
                os.close(fd)
                with open(path, 'wb') as f:
                    f.write(data)
                try:
                    # Target: upx -d <file>
                    proc = subprocess.run(
                        [upx_bin, '-d', path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        env=env,
                        timeout=1
                    )
                    if proc.returncode != 0:
                        err = proc.stderr.decode('utf-8', errors='ignore')
                        if "AddressSanitizer" in err or "heap-buffer-overflow" in err:
                            return data
                except:
                    pass
                finally:
                    if os.path.exists(path):
                        os.unlink(path)
                return None

            mutations = []
            slen = len(seed_data)
            
            # Generate truncated versions (target ground truth length ~512 bytes)
            # Coarse grained
            for l in range(100, slen, 50):
                mutations.append(seed_data[:l])
            # Fine grained around 512
            for l in range(400, 600, 4):
                if l < slen:
                    mutations.append(seed_data[:l])
            
            # Generate bit flips and overwrites
            for _ in range(300):
                d = bytearray(seed_data)
                ops = random.randint(1, 5)
                for _ in range(ops):
                    pos = random.randint(0, len(d)-1)
                    if random.random() < 0.5:
                        d[pos] ^= random.randint(1, 255)
                    else:
                        d[pos] = random.randint(0, 255)
                mutations.append(bytes(d))

            # Execute fuzzing
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = {executor.submit(check_poc, m): m for m in mutations}
                start_time = time.time()
                for f in concurrent.futures.as_completed(futures):
                    res = f.result()
                    if res:
                        crashes.append(res)
                        # If we found a compact PoC, return early
                        if len(res) <= 550:
                            return res
                    
                    if time.time() - start_time > 50:
                        break
            
            if crashes:
                # Return the shortest crash found
                crashes.sort(key=len)
                return crashes[0]
            
            # Fallback
            return seed_data[:512]

        except Exception:
            return b'A' * 512
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
