import os
import sys
import shutil
import subprocess
import tempfile
import glob
import random
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a temporary directory for build and execution
        base_dir = tempfile.mkdtemp()
        
        try:
            # Extract the source code
            try:
                shutil.unpack_archive(src_path, base_dir)
            except Exception:
                # Fallback for tarballs if unpack_archive fails detection
                subprocess.run(['tar', 'xf', src_path, '-C', base_dir], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Locate the source root (containing Makefile)
            source_root = base_dir
            for root, dirs, files in os.walk(base_dir):
                if 'Makefile' in files and 'codec' in dirs:
                    source_root = root
                    break
            
            # Setup environment for ASAN build
            env = os.environ.copy()
            flags = "-fsanitize=address -g -O1 -fno-omit-frame-pointer"
            env['CFLAGS'] = flags
            env['CXXFLAGS'] = flags
            env['LDFLAGS'] = flags
            
            # Build the project
            # Using -j8 for speed, USE_ASM=No to avoid nasm dependency issues
            make_cmd = [
                'make', '-j8',
                'USE_ASM=No',
                'ARCH=x86_64',
                'BUILDTYPE=Debug'
            ]
            
            subprocess.run(make_cmd, cwd=source_root, env=env, 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Locate the compiled binary (h264dec)
            binary_name = 'h264dec'
            binary_path = None
            
            candidates = [
                os.path.join(source_root, binary_name),
                os.path.join(source_root, 'codec', 'console', 'dec', binary_name),
                os.path.join(source_root, 'bin', binary_name),
            ]
            
            for p in candidates:
                if os.path.exists(p) and os.access(p, os.X_OK):
                    binary_path = p
                    break
            
            if not binary_path:
                # Recursive search if not in standard paths
                for root, dirs, files in os.walk(source_root):
                    if binary_name in files:
                        p = os.path.join(root, binary_name)
                        if os.access(p, os.X_OK):
                            binary_path = p
                            break
            
            if not binary_path:
                return b''

            # Collect seed files from the source tree
            seeds = []
            for root, dirs, files in os.walk(source_root):
                for f in files:
                    if f.endswith('.264') or f.endswith('.jsv') or f.endswith('.h264'):
                        seeds.append(os.path.join(root, f))
            
            # Load seeds
            loaded_seeds = []
            if seeds:
                # Sort by size to prefer smaller seeds for faster fuzzing
                seeds.sort(key=os.path.getsize)
                # Take top 20
                for s in seeds[:20]:
                    try:
                        with open(s, 'rb') as f:
                            loaded_seeds.append(bytearray(f.read()))
                    except:
                        pass
            
            # If no seeds found, construct a minimal dummy seed (H.264 SPS)
            if not loaded_seeds:
                loaded_seeds = [bytearray(b'\x00\x00\x00\x01\x67\x42\x00\x1e\xf8\x40\x50\x20')]

            # Fuzzing Loop
            start_time = time.time()
            fuzz_duration = 45 # seconds
            
            poc_file = os.path.join(base_dir, 'poc.264')
            
            # Keep track of the last mutated input
            current_input = loaded_seeds[0]
            
            while time.time() - start_time < fuzz_duration:
                # Pick a seed
                base = random.choice(loaded_seeds)
                current_input = bytearray(base)
                
                # Apply mutations
                mutation_type = random.randint(0, 3)
                
                if mutation_type == 0:
                    # Bit flips
                    num_flips = random.randint(1, 10)
                    for _ in range(num_flips):
                        if not current_input: break
                        idx = random.randint(0, len(current_input) - 1)
                        current_input[idx] ^= (1 << random.randint(0, 7))
                        
                elif mutation_type == 1:
                    # Byte overwrite
                    if current_input:
                        idx = random.randint(0, len(current_input) - 1)
                        current_input[idx] = random.randint(0, 255)
                        
                elif mutation_type == 2:
                    # Chunk insertion (to trigger buffer overflows)
                    idx = random.randint(0, len(current_input))
                    chunk_len = random.randint(1, 64)
                    chunk = bytearray(random.getrandbits(8) for _ in range(chunk_len))
                    current_input[idx:idx] = chunk
                    
                elif mutation_type == 3:
                    # Targeted: Try to flip SPS (0x67) to SubsetSPS (0x6F) to trigger SVC logic
                    # Scan for potential NAL headers
                    for i in range(min(len(current_input)-5, 100)):
                        # Look for 0x67
                        if current_input[i] == 0x67:
                             if random.random() < 0.5:
                                 current_input[i] = 0x6F # Flip to SVC Subset SPS
                
                # Write candidate
                with open(poc_file, 'wb') as f:
                    f.write(current_input)
                
                # Execute binary
                try:
                    proc = subprocess.run(
                        [binary_path, poc_file],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        timeout=1.0, # Short timeout
                        env=env
                    )
                    
                    # Check for ASAN crash
                    if proc.returncode != 0:
                        stderr_out = proc.stderr.decode('latin1', errors='ignore')
                        if "AddressSanitizer" in stderr_out and "heap-buffer-overflow" in stderr_out:
                            return bytes(current_input)
                            
                except subprocess.TimeoutExpired:
                    continue
                except Exception:
                    continue

            # Return the last attempted input if no crash found (best effort)
            return bytes(current_input)

        except Exception:
            return b''
        finally:
            # Cleanup
            shutil.rmtree(base_dir, ignore_errors=True)
