import os
import sys
import subprocess
import tempfile
import shutil
import tarfile
import random
import time
import struct
import multiprocessing

# Minimal valid J2K codestream (fallback seed)
# SOC, SIZ (1x1), COD, QCD, SOT, SOD, EOC
FALLBACK_SEED_HEX = (
    "ff4fff51002f0000000000010000000100000000000000000000000000000001070101070101"
    "ff52000c00000001010504040001ff5c000440ff90000a0000000000010001ff93000400ffd9"
)

def worker_fuzz(target_bin, seeds, found_event, result_queue, timeout_sec):
    local_seeds = [s for s in seeds if len(s) > 0]
    if not local_seeds:
        return

    def get_tmp_filename():
        return f"/tmp/fuzz_{os.getpid()}_{random.randint(0, 1000000)}.j2k"

    output_img = f"/tmp/out_{os.getpid()}.bmp"
    
    start_time = time.time()
    
    # Environment variables for ASAN
    env = os.environ.copy()
    env['ASAN_OPTIONS'] = 'halt_on_error=1:detect_leaks=0:symbolize=0'

    while not found_event.is_set():
        if time.time() - start_time > timeout_sec:
            break
            
        base = random.choice(local_seeds)
        data = bytearray(base)
        
        # Mutation strategy
        num_mutations = random.randint(1, 3)
        for _ in range(num_mutations):
            m = random.randint(0, 5)
            if m == 0: # Flip bit
                if len(data) > 0:
                    idx = random.randint(0, len(data)-1)
                    data[idx] ^= (1 << random.randint(0, 7))
            elif m == 1: # Flip byte
                if len(data) > 0:
                    idx = random.randint(0, len(data)-1)
                    data[idx] = random.randint(0, 255)
            elif m == 2: # Magic values
                if len(data) > 4:
                    idx = random.randint(0, len(data)-4)
                    val = random.choice([
                        b'\xff\xff', b'\x00\x00', b'\x7f\xff', b'\x80\x00', 
                        b'\xff\xfe', b'\x00\x01', b'\xff\xff\xff\xff'
                    ])
                    end = min(idx + len(val), len(data))
                    data[idx:end] = val[:end-idx]
            elif m == 3: # Delete chunk
                if len(data) > 10:
                    l = random.randint(1, 10)
                    s = random.randint(0, len(data)-l)
                    del data[s:s+l]
            elif m == 4: # Insert chunk
                if len(data) < 20000:
                    pos = random.randint(0, len(data))
                    chunk = random.randbytes(random.randint(1, 16))
                    data[pos:pos] = chunk
            elif m == 5: # Duplicate chunk
                if len(data) > 10:
                    l = random.randint(1, 16)
                    s = random.randint(0, len(data)-l)
                    chunk = data[s:s+l]
                    pos = random.randint(0, len(data))
                    data[pos:pos] = chunk
        
        tmp_file = get_tmp_filename()
        try:
            with open(tmp_file, "wb") as f:
                f.write(data)
            
            # Execute target
            proc = subprocess.run(
                [target_bin, "-i", tmp_file, "-o", output_img],
                capture_output=True,
                env=env,
                timeout=1
            )
            
            if proc.returncode != 0:
                stderr = proc.stderr
                # Check for Heap Buffer Overflow
                if b"AddressSanitizer" in stderr and b"heap-buffer-overflow" in stderr:
                    result_queue.put(bytes(data))
                    found_event.set()
                    if os.path.exists(tmp_file): os.remove(tmp_file)
                    return

        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
        finally:
            if os.path.exists(tmp_file):
                try: os.remove(tmp_file)
                except: pass

    if os.path.exists(output_img):
        try: os.remove(output_img)
        except: pass

class Solution:
    def solve(self, src_path: str) -> bytes:
        base_dir = os.path.abspath(os.path.dirname(src_path))
        work_dir = tempfile.mkdtemp(dir=base_dir)
        
        try:
            # 1. Extract source code
            if src_path.endswith(".tar.gz") or src_path.endswith(".tgz"):
                with tarfile.open(src_path, "r:gz") as t:
                    t.extractall(work_dir)
            elif src_path.endswith(".zip"):
                 subprocess.run(["unzip", "-q", src_path, "-d", work_dir], check=True)
            elif src_path.endswith(".tar"):
                with tarfile.open(src_path, "r:") as t:
                    t.extractall(work_dir)
            else:
                pass # Handle as directory or unknown

            # 2. Locate CMakeLists.txt
            source_root = None
            for root, dirs, files in os.walk(work_dir):
                if "CMakeLists.txt" in files:
                    source_root = root
                    break
            
            if not source_root:
                return bytes.fromhex(FALLBACK_SEED_HEX)

            build_dir = os.path.join(work_dir, "build")
            os.makedirs(build_dir, exist_ok=True)
            
            # 3. Build with ASAN
            cmake_cmd = [
                "cmake",
                source_root,
                "-DCMAKE_BUILD_TYPE=Debug",
                "-DCMAKE_C_FLAGS=-fsanitize=address -g -O1",
                "-DCMAKE_CXX_FLAGS=-fsanitize=address -g -O1",
                "-DBUILD_SHARED_LIBS=OFF",
                "-DBUILD_CODEC=ON",
                "-DBUILD_PKGCONFIG_FILES=OFF",
                "-DBUILD_JPIP=OFF",
                "-DBUILD_JPWL=OFF",
                "-DBUILD_MJ2=OFF",
                "-DBUILD_TESTING=OFF",
                "-DCMAKE_DISABLE_FIND_PACKAGE_PNG=ON",
                "-DCMAKE_DISABLE_FIND_PACKAGE_TIFF=ON",
                "-DCMAKE_DISABLE_FIND_PACKAGE_LCMS2=ON"
            ]
            
            subprocess.run(cmake_cmd, cwd=build_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["make", "-j8", "opj_decompress"], cwd=build_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            target_bin = None
            for root, dirs, files in os.walk(build_dir):
                if "opj_decompress" in files:
                    target_bin = os.path.join(root, "opj_decompress")
                    break
            
            if not target_bin:
                return bytes.fromhex(FALLBACK_SEED_HEX)

            # 4. Collect seeds
            seeds = []
            for root, dirs, files in os.walk(source_root):
                for f in files:
                    if f.lower().endswith(('.j2k', '.jp2', '.j2c')):
                        try:
                            with open(os.path.join(root, f), "rb") as fd:
                                content = fd.read()
                                if len(content) < 50000: 
                                    seeds.append(content)
                        except: pass
            
            if not seeds:
                seeds.append(bytes.fromhex(FALLBACK_SEED_HEX))

            # 5. Fuzzing
            found_event = multiprocessing.Event()
            result_queue = multiprocessing.Queue()
            
            num_workers = 8
            timeout = 120 # seconds
            
            workers = []
            for _ in range(num_workers):
                p = multiprocessing.Process(
                    target=worker_fuzz,
                    args=(target_bin, seeds, found_event, result_queue, timeout)
                )
                p.start()
                workers.append(p)
            
            poc = None
            try:
                poc = result_queue.get(timeout=timeout + 5)
            except:
                pass
            
            found_event.set()
            for p in workers:
                p.terminate()
                p.join()
            
            if poc:
                return poc
            else:
                return seeds[0]

        except Exception as e:
            return bytes.fromhex(FALLBACK_SEED_HEX)
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
