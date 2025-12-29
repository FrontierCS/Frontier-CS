import os
import sys
import subprocess
import tarfile
import tempfile
import shutil
import random
import struct
import time
import concurrent.futures
import uuid

class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp()
        
        try:
            # 1. Extract the source code
            if os.path.isfile(src_path):
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=work_dir)
            
            # Locate the build root (where configure script is)
            build_root = work_dir
            for root, dirs, files in os.walk(work_dir):
                if 'configure' in files:
                    build_root = root
                    break
            
            # 2. Compile libdwarf/dwarfdump with AddressSanitizer
            env = os.environ.copy()
            # Optimize for speed but keep debug info and sanitizers
            cflags = "-g -O1 -fsanitize=address -fno-omit-frame-pointer"
            env['CFLAGS'] = cflags
            env['CXXFLAGS'] = cflags
            env['LDFLAGS'] = "-fsanitize=address"
            
            try:
                subprocess.run(
                    ["./configure", "--disable-shared", "--disable-dependency-tracking"],
                    cwd=build_root, env=env,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
                )
                subprocess.run(
                    ["make", "-j8"],
                    cwd=build_root, env=env,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
                )
            except subprocess.CalledProcessError:
                # If build fails, we proceed to check if binary was created anyway
                pass

            # Locate the compiled dwarfdump binary
            dwarfdump_bin = None
            for root, dirs, files in os.walk(build_root):
                if 'dwarfdump' in files:
                    candidate = os.path.join(root, 'dwarfdump')
                    if os.access(candidate, os.X_OK) and os.path.isfile(candidate):
                        dwarfdump_bin = candidate
                        break
            
            if not dwarfdump_bin:
                # Without the binary we cannot verify, return empty bytes or handle error
                return b""

            # 3. Generate a Seed Input
            # We create a valid ELF object with DWARF 5 debug info using system gcc
            seed_c = os.path.join(work_dir, "seed.c")
            seed_o = os.path.join(work_dir, "seed.o")
            with open(seed_c, "w") as f:
                f.write("int main() { return 0; }")
            
            # Try compiling with -gdwarf-5
            subprocess.run(
                ["gcc", "-gdwarf-5", "-c", seed_c, "-o", seed_o],
                cwd=work_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            
            # Fallback to standard -g if -gdwarf-5 fails
            if not os.path.exists(seed_o):
                 subprocess.run(
                    ["gcc", "-g", "-c", seed_c, "-o", seed_o],
                    cwd=work_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            
            if not os.path.exists(seed_o):
                return b""

            with open(seed_o, "rb") as f:
                seed_data = bytearray(f.read())

            # 4. Fuzzing Loop
            # We use multiple threads to invoke dwarfdump on mutated inputs
            found_crash = None
            stop_fuzzing = False
            
            def fuzz_worker():
                nonlocal found_crash, stop_fuzzing
                
                # Use a unique filename for this worker/iteration to avoid collisions
                unique_filename = os.path.join(work_dir, f"fuzz_{uuid.uuid4().hex}.o")
                local_data = bytearray(seed_data)
                
                # Run a batch of mutations to amortize thread overhead
                for _ in range(50):
                    if stop_fuzzing:
                        return

                    # Mutation Logic
                    # Reset to seed occasionally
                    if random.random() < 0.2:
                        local_data[:] = seed_data
                    
                    mutation_type = random.random()
                    if mutation_type < 0.5:
                        # 32-bit Integer Injection (targeting counts/sizes)
                        if len(local_data) > 4:
                            pos = random.randint(0, len(local_data) - 4)
                            # Interesting values for overflow/logic errors
                            val = random.choice([
                                0xFFFFFFFF, 0x80000000, 0x7FFFFFFF, 
                                0xFFFF, 0x10000, 0, 1, 
                                random.randint(0, 0xFFFFFFFF)
                            ])
                            struct.pack_into("<I", local_data, pos, val)
                    elif mutation_type < 0.8:
                        # Byte randomization
                        pos = random.randint(0, len(local_data) - 1)
                        local_data[pos] = random.randint(0, 255)
                    else:
                        # Bit flipping
                        pos = random.randint(0, len(local_data) - 1)
                        local_data[pos] ^= (1 << random.randint(0, 7))

                    # Write mutated file
                    with open(unique_filename, "wb") as f:
                        f.write(local_data)
                    
                    # Run target
                    # -n tells dwarfdump to print .debug_names section (vulnerable path)
                    try:
                        proc = subprocess.run(
                            [dwarfdump_bin, "-n", unique_filename],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE,
                            timeout=0.2  # Fast timeout
                        )
                        
                        if proc.returncode != 0:
                            # Check for ASAN error
                            stderr_out = proc.stderr.decode(errors='ignore')
                            if "AddressSanitizer" in stderr_out or "heap-buffer-overflow" in stderr_out:
                                found_crash = bytes(local_data)
                                stop_fuzzing = True
                                return
                    except subprocess.TimeoutExpired:
                        pass
                    except Exception:
                        pass
                
                # Cleanup
                if os.path.exists(unique_filename):
                    os.remove(unique_filename)

            # Use ThreadPoolExecutor to run fuzz workers
            start_time = time.time()
            max_duration = 180  # Max 3 minutes
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                futures = set()
                while time.time() - start_time < max_duration and not stop_fuzzing:
                    # Maintain pool saturation
                    while len(futures) < 16 and not stop_fuzzing:
                        futures.add(executor.submit(fuzz_worker))
                    
                    # Wait for at least one to complete
                    done, futures = concurrent.futures.wait(
                        futures, 
                        timeout=0.1, 
                        return_when=concurrent.futures.FIRST_COMPLETED
                    )
            
            if found_crash:
                return found_crash
            
            # If no crash found, return the seed as best effort
            return bytes(seed_data)

        except Exception:
            return b""
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)