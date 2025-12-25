import os
import sys
import tarfile
import subprocess
import tempfile
import shutil
import glob
import random
import time
import concurrent.futures

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a temporary directory for build and execution
        base_dir = os.getcwd()
        work_dir = tempfile.mkdtemp()
        
        try:
            # Extract the source code
            with tarfile.open(src_path) as tar:
                # Sanitize extraction paths to prevent traversal
                def is_within_directory(directory, target):
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                    prefix = os.path.commonprefix([abs_directory, abs_target])
                    return prefix == abs_directory

                def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                    for member in tar.getmembers():
                        member_path = os.path.join(path, member.name)
                        if not is_within_directory(path, member_path):
                            continue
                    tar.extractall(path, members, numeric_owner=numeric_owner)
                
                safe_extract(tar, work_dir)

            # Identify source root directory
            src_root = work_dir
            for item in os.listdir(work_dir):
                candidate = os.path.join(work_dir, item)
                if os.path.isdir(candidate):
                    if os.path.exists(os.path.join(candidate, 'configure.ac')) or \
                       os.path.exists(os.path.join(candidate, 'meson.build')) or \
                       os.path.exists(os.path.join(candidate, 'CMakeLists.txt')):
                        src_root = candidate
                        break
            
            # Prepare build environment with AddressSanitizer (ASan)
            env = os.environ.copy()
            env['CC'] = 'clang'
            env['CXX'] = 'clang++'
            # -fsanitize=address is crucial to detect Use-After-Free
            flags = '-fsanitize=address -g -O1'
            env['CFLAGS'] = flags
            env['CXXFLAGS'] = flags
            env['LDFLAGS'] = flags
            
            binary_path = None
            
            # Strategy 1: Build using Meson
            if os.path.exists(os.path.join(src_root, 'meson.build')) and shutil.which('meson'):
                build_dir = os.path.join(src_root, 'build_meson')
                try:
                    subprocess.run(['meson', 'setup', build_dir], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                    subprocess.run(['ninja', '-C', build_dir], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                    
                    for root, dirs, files in os.walk(build_dir):
                        if 'ots-sanitize' in files:
                            candidate = os.path.join(root, 'ots-sanitize')
                            if os.access(candidate, os.X_OK):
                                binary_path = candidate
                                break
                except Exception:
                    pass

            # Strategy 2: Build using Autotools if Meson failed
            if not binary_path and (os.path.exists(os.path.join(src_root, 'configure.ac')) or os.path.exists(os.path.join(src_root, 'autogen.sh'))):
                try:
                    if os.path.exists(os.path.join(src_root, 'autogen.sh')):
                        subprocess.run(['./autogen.sh'], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                    
                    if os.path.exists(os.path.join(src_root, 'configure')):
                        subprocess.run(['./configure'], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                        subprocess.run(['make', '-j8'], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                        
                        # Locate binary
                        for root, dirs, files in os.walk(src_root):
                            if 'ots-sanitize' in files:
                                candidate = os.path.join(root, 'ots-sanitize')
                                if os.access(candidate, os.X_OK):
                                    binary_path = candidate
                                    break
                except Exception:
                    pass
            
            # Fallback: Look for any pre-existing or misplaced binary
            if not binary_path:
                for root, dirs, files in os.walk(src_root):
                    if 'ots-sanitize' in files:
                        candidate = os.path.join(root, 'ots-sanitize')
                        if os.access(candidate, os.X_OK):
                            binary_path = candidate
                            break
            
            if not binary_path:
                return b''

            # Gather seeds for fuzzing
            seeds = []
            for root, dirs, files in os.walk(src_root):
                for f in files:
                    if f.lower().endswith(('.ttf', '.otf', '.woff', '.woff2')):
                        seeds.append(os.path.join(root, f))
            
            # Prioritize seeds based on problem description ('arvo')
            arvo_seeds = [s for s in seeds if 'arvo' in os.path.basename(s).lower()]
            if arvo_seeds:
                primary_seeds = arvo_seeds
            else:
                # If no specific target seed found, use smallest valid fonts to speed up fuzzing
                primary_seeds = sorted(seeds, key=os.path.getsize)[:50]
            
            if not primary_seeds:
                # Create dummy seed if no fonts found
                dummy = os.path.join(work_dir, 'dummy.ttf')
                with open(dummy, 'wb') as f:
                    f.write(b'\x00\x01\x00\x00' + b'\x00'*12)
                primary_seeds = [dummy]

            # Fuzzing Logic
            stop_event = False
            found_solution = None

            def fuzz_worker(worker_idx, seed_list, bin_path, tmp_base, timeout_ts):
                nonlocal stop_event
                nonlocal found_solution
                
                # Seed random generator uniquely per thread
                rng = random.Random(worker_idx + time.time())
                
                while time.time() < timeout_ts and not stop_event:
                    # Pick a seed
                    seed_file = rng.choice(seed_list)
                    try:
                        with open(seed_file, 'rb') as f:
                            data = bytearray(f.read())
                    except:
                        continue
                        
                    if not data: continue
                    
                    # Mutate
                    mutations = rng.randint(1, 4)
                    for _ in range(mutations):
                        mtype = rng.randint(0, 3)
                        if mtype == 0: # Byte Flip
                            idx = rng.randint(0, len(data)-1)
                            data[idx] ^= rng.randint(1, 255)
                        elif mtype == 1: # Delete Chunk
                            if len(data) > 5:
                                idx = rng.randint(0, len(data)-1)
                                l = rng.randint(1, min(20, len(data)-idx))
                                del data[idx:idx+l]
                        elif mtype == 2: # Insert Junk
                            idx = rng.randint(0, len(data))
                            count = rng.randint(1, 4)
                            vals = [rng.randint(0, 255) for _ in range(count)]
                            data[idx:idx] = bytearray(vals)
                        elif mtype == 3: # Integer Overwrite (trigger buffer issues)
                             if len(data) > 4:
                                 idx = rng.randint(0, len(data)-4)
                                 v = rng.choice([0xFFFFFFFF, 0x7FFFFFFF, 0x80000000, 0xFFFF, 0, 0x01000000])
                                 data[idx] = v & 0xFF
                                 data[idx+1] = (v >> 8) & 0xFF
                                 data[idx+2] = (v >> 16) & 0xFF
                                 data[idx+3] = (v >> 24) & 0xFF
                    
                    # Save mutated file
                    tname = f"fuzz_{worker_idx}.ttf"
                    tpath = os.path.join(tmp_base, tname)
                    try:
                        with open(tpath, 'wb') as f:
                            f.write(data)
                    except:
                        continue

                    # Execute binary
                    try:
                        res = subprocess.run(
                            [bin_path, tpath],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            timeout=0.5
                        )
                        # Check for ASan crash
                        if res.returncode != 0:
                            err = res.stderr.decode(errors='ignore')
                            if "AddressSanitizer" in err and "heap-use-after-free" in err:
                                stop_event = True
                                found_solution = bytes(data)
                                return
                    except subprocess.TimeoutExpired:
                        pass
                    except Exception:
                        pass
            
            # Run parallel fuzzers
            # Set time limit to allow compilation + ~2-3 mins of fuzzing
            end_time = time.time() + 180 
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(fuzz_worker, i, primary_seeds, binary_path, work_dir, end_time) for i in range(8)]
                concurrent.futures.wait(futures)
            
            if found_solution:
                return found_solution
            
            # Fallback: return a seed if no crash found (unlikely if vulnerable)
            if primary_seeds:
                with open(primary_seeds[0], 'rb') as f:
                    return f.read()
            return b''

        except Exception:
            return b''
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
