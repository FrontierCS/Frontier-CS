import os
import sys
import subprocess
import shutil
import random
import time
import multiprocessing
import glob

def fuzz_worker(binary_path, seed, result_list, worker_id):
    tmp_filename = f"/tmp/poc_{worker_id}_{os.getpid()}.ttf"
    current_input = bytearray(seed)
    
    start_time = time.time()
    # Run loop
    while time.time() - start_time < 180:
        if len(result_list) > 0:
            break
            
        mutated = bytearray(current_input)
        
        # Mutation strategies
        r = random.random()
        if r < 0.1: # Bit flips
            for _ in range(random.randint(1, 4)):
                idx = random.randint(0, len(mutated) - 1)
                bit = random.randint(0, 7)
                mutated[idx] ^= (1 << bit)
        elif r < 0.3: # Byte overwrite
            idx = random.randint(0, len(mutated) - 1)
            mutated[idx] = random.randint(0, 255)
        elif r < 0.5: # Insert chunk
            chunk_len = random.randint(1, 16)
            chunk = os.urandom(chunk_len)
            pos = random.randint(0, len(mutated))
            mutated[pos:pos] = chunk
        elif r < 0.7: # Delete chunk
            if len(mutated) > 10:
                chunk_len = random.randint(1, 10)
                pos = random.randint(0, len(mutated) - chunk_len)
                del mutated[pos:pos+chunk_len]
        else: # Resize/Pad
            target = 800
            if len(mutated) < target:
                mutated.extend(os.urandom(target - len(mutated)))
            elif len(mutated) > target:
                mutated = mutated[:target]
        
        # Cap size
        if len(mutated) > 2000:
            mutated = mutated[:2000]

        # Write to temp file
        try:
            with open(tmp_filename, "wb") as f:
                f.write(mutated)
        except:
            continue
            
        # Execute binary
        try:
            proc = subprocess.run(
                [binary_path, tmp_filename],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=1
            )
            
            # Check for ASAN output
            if b"AddressSanitizer" in proc.stderr and b"heap-use-after-free" in proc.stderr:
                result_list.append(bytes(mutated))
                break
            
            # Simple hill climbing: if we didn't crash but didn't timeout/fail badly, maybe keep mutation
            # Heuristic: mostly random walk
            if random.random() < 0.2:
                current_input = mutated
            if random.random() < 0.05:
                current_input = bytearray(seed)
                
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
            
    if os.path.exists(tmp_filename):
        try:
            os.remove(tmp_filename)
        except:
            pass

class Solution:
    def solve(self, src_path: str) -> bytes:
        # 1. Build the vulnerable binary with ASAN
        build_dir = os.path.join(src_path, "build_fuzz_gen")
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        os.makedirs(build_dir)
        
        env = os.environ.copy()
        env['CC'] = 'gcc'
        env['CXX'] = 'g++'
        env['CFLAGS'] = '-fsanitize=address -g'
        env['CXXFLAGS'] = '-fsanitize=address -g'
        env['LDFLAGS'] = '-fsanitize=address'
        
        binary_path = None
        
        # Check for Meson build system
        if os.path.exists(os.path.join(src_path, "meson.build")):
            try:
                subprocess.run(["meson", "setup", build_dir, src_path], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                subprocess.run(["ninja", "-C", build_dir], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                found = glob.glob(os.path.join(build_dir, "**", "ots-sanitize"), recursive=True)
                if found:
                    binary_path = found[0]
            except:
                pass
                
        # Check for Autotools build system if Meson failed or missing
        if not binary_path and (os.path.exists(os.path.join(src_path, "configure")) or os.path.exists(os.path.join(src_path, "autogen.sh"))):
            try:
                if os.path.exists(os.path.join(src_path, "autogen.sh")):
                     subprocess.run(["./autogen.sh"], cwd=src_path, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["./configure"], cwd=src_path, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["make", "-j8"], cwd=src_path, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                found = glob.glob(os.path.join(src_path, "**", "ots-sanitize"), recursive=True)
                if found:
                    binary_path = found[0]
            except:
                pass
        
        # Fallback if build fails
        if not binary_path:
            return b'wOF2' + os.urandom(796)
            
        # 2. Fuzzing
        manager = multiprocessing.Manager()
        result_list = manager.list()
        
        # Prepare seeds
        # Minimal TTF seed
        seed_ttf = b'\x00\x01\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x63\x6d\x61\x70\x00\x00\x00\x00\x00\x00\x00\x20\x00\x00\x00\x00'
        # Minimal WOFF2 seed
        seed_woff2 = b'wOF2' + b'\x00\x01\x00\x00' + b'\x00\x00\x03\x20' + os.urandom(100)
        
        seeds = [seed_ttf, seed_woff2, seed_woff2 + os.urandom(500)]
        
        pool = multiprocessing.Pool(processes=8)
        
        for i in range(8):
            pool.apply_async(fuzz_worker, args=(binary_path, seeds[i % len(seeds)], result_list, i))
            
        pool.close()
        
        # Wait for results (max 3 minutes)
        start_wait = time.time()
        found_poc = None
        while time.time() - start_wait < 180:
            if len(result_list) > 0:
                found_poc = result_list[0]
                break
            time.sleep(1)
            
        pool.terminate()
        pool.join()
        
        if found_poc:
            return found_poc
            
        # If no crash found, return a formatted guess of length 800
        return b'wOF2' + b'A' * 796
