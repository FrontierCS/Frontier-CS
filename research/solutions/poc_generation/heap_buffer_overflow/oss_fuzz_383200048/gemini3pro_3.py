import os
import sys
import subprocess
import shutil
import tarfile
import tempfile
import random
import glob
import time
import concurrent.futures

class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp()
        try:
            # 1. Extract source
            if tarfile.is_tarfile(src_path):
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=work_dir)
            
            src_root = work_dir
            # Find Makefile to determine root
            makefiles = glob.glob(os.path.join(work_dir, '**', 'Makefile'), recursive=True)
            if makefiles:
                makefiles.sort(key=lambda p: len(p.split(os.sep)))
                src_root = os.path.dirname(makefiles[0])
            
            # 2. Compile UPX with ASAN
            env = os.environ.copy()
            # ASAN flags for detection
            flags = "-O1 -g -fsanitize=address -fno-omit-frame-pointer"
            env['CXXFLAGS'] = flags
            env['CFLAGS'] = flags
            env['LDFLAGS'] = flags
            
            # Build
            subprocess.run(['make', '-j8', 'all'], cwd=src_root, env=env, 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Find compiled binary
            upx_bin = None
            candidates = glob.glob(os.path.join(src_root, '**', 'upx*'), recursive=True)
            for c in candidates:
                if os.access(c, os.X_OK) and not os.path.isdir(c) and 'test' not in os.path.basename(c):
                    upx_bin = c
                    break
            
            if not upx_bin:
                return b''

            # 3. Create base ELF file
            base_so = os.path.join(work_dir, 'base.so')
            c_src = os.path.join(work_dir, 't.c')
            with open(c_src, 'w') as f:
                f.write('void f(){}')
            
            # Try 32-bit first (often smaller and target for this type of bug)
            # Use strip -s to reduce size towards 512 bytes ground truth
            subprocess.run(['gcc', '-m32', '-shared', '-fPIC', '-s', '-o', base_so, c_src],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if not os.path.exists(base_so):
                subprocess.run(['gcc', '-shared', '-fPIC', '-s', '-o', base_so, c_src],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if not os.path.exists(base_so):
                # Fallback
                with open(base_so, 'wb') as f:
                    f.write(b'\x7fELF' + b'\x00'*100)

            with open(base_so, 'rb') as f:
                base_data = f.read()

            # 4. Fuzzing
            result = []
            
            def fuzz(wid):
                t_start = time.time()
                # Run for up to 60 seconds
                while time.time() - t_start < 60:
                    if result: return
                    
                    # Mutate base ELF
                    data = bytearray(base_data)
                    if len(data) > 4:
                        # Mutate a few bytes
                        n = random.randint(1, 5)
                        for _ in range(n):
                            # Skip magic bytes
                            idx = random.randint(4, len(data)-1)
                            data[idx] = random.randint(0, 255)
                    
                    in_f = os.path.join(work_dir, f'i_{wid}.so')
                    out_f = os.path.join(work_dir, f'o_{wid}.upx')
                    
                    with open(in_f, 'wb') as f:
                        f.write(data)
                    
                    # Pack
                    # Use --force to pack even if UPX thinks it's suspicious
                    p = subprocess.run([upx_bin, '--force', '-o', out_f, in_f],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
                    
                    if p.returncode == 0 and os.path.exists(out_f):
                        # Unpack / Test
                        # -d triggers full decompression and un_DT_INIT
                        u = subprocess.run([upx_bin, '-d', '-o', '/dev/null', out_f],
                                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=10)
                        
                        # Check for crash (ASAN or Segfault)
                        is_crash = False
                        if u.returncode == 139 or u.returncode == -11:
                            is_crash = True
                        elif u.returncode != 0:
                            err = u.stderr.decode(errors='ignore')
                            if "AddressSanitizer" in err or "segmentation fault" in err.lower():
                                is_crash = True
                        
                        if is_crash:
                            result.append(out_f)
                            return
                    
                    # Cleanup
                    try:
                        if os.path.exists(in_f): os.remove(in_f)
                        if os.path.exists(out_f): os.remove(out_f)
                    except: pass
            
            # Parallel fuzzing
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as exc:
                exc.map(fuzz, range(8))
            
            if result:
                with open(result[0], 'rb') as f:
                    return f.read()
            
            return b''

        except Exception:
            return b''
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)