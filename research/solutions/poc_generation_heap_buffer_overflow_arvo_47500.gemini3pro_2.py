import os
import subprocess
import tempfile
import random
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Use a temporary directory for all operations
        with tempfile.TemporaryDirectory() as base_dir:
            # 1. Extract Source
            extract_dir = os.path.join(base_dir, "src")
            os.makedirs(extract_dir)
            try:
                subprocess.run(["tar", "-xf", src_path, "-C", extract_dir], 
                               check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            except Exception:
                return b""
            
            src_root = extract_dir
            # Handle tarball with single root folder
            entries = os.listdir(extract_dir)
            if len(entries) == 1 and os.path.isdir(os.path.join(extract_dir, entries[0])):
                src_root = os.path.join(extract_dir, entries[0])

            # 2. Compile with ASAN
            build_dir = os.path.join(base_dir, "build")
            os.makedirs(build_dir)
            
            # Configure with ASAN
            try:
                subprocess.run([
                    "cmake",
                    "-DCMAKE_BUILD_TYPE=Release",
                    "-DCMAKE_C_FLAGS=-fsanitize=address",
                    "-DCMAKE_CXX_FLAGS=-fsanitize=address",
                    src_root
                ], cwd=build_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # Build opj_decompress and opj_compress
                subprocess.run(["make", "-j8", "opj_decompress", "opj_compress"], 
                               cwd=build_dir, check=True, 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                return b""
            
            opj_decompress = os.path.join(build_dir, "bin", "opj_decompress")
            opj_compress = os.path.join(build_dir, "bin", "opj_compress")

            # 3. Prepare Seeds
            seeds = []
            # Search for existing small j2k/jp2 files in the source tree
            for root, dirs, files in os.walk(src_root):
                for f in files:
                    if f.lower().endswith('.j2k') or f.lower().endswith('.jp2'):
                        p = os.path.join(root, f)
                        if os.path.getsize(p) < 30000: # Limit size for efficiency
                            with open(p, "rb") as fd:
                                seeds.append(bytearray(fd.read()))
            
            # If no seeds found, generate one using opj_compress
            if not seeds:
                pgm_file = os.path.join(base_dir, "test.pgm")
                with open(pgm_file, "wb") as f:
                    # Create a 64x64 simple image
                    f.write(b"P5\n64 64\n255\n")
                    f.write(os.urandom(64*64))
                
                seed_j2k = os.path.join(base_dir, "seed.j2k")
                try:
                    subprocess.run([opj_compress, "-i", pgm_file, "-o", seed_j2k],
                                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    with open(seed_j2k, "rb") as f:
                        seeds.append(bytearray(f.read()))
                except Exception:
                    pass

            if not seeds:
                return b""

            # 4. Fuzzing Loop
            env = os.environ.copy()
            # Set ASAN to exit with a specific code on error to distinguish from normal errors
            env['ASAN_OPTIONS'] = 'exitcode=66:halt_on_error=1' 

            out_file = os.path.join(base_dir, "out.ppm")
            
            # Run fuzzing iterations
            for i in range(5000):
                seed = random.choice(seeds)
                mutated = bytearray(seed)
                
                method = random.random()
                
                # Targeted mutations for J2K markers
                if method < 0.5:
                    # Try to mutate COD marker (HTJ2K logic often in style/cap)
                    # COD marker is FF 52
                    pos = mutated.find(b'\xFF\x52')
                    if pos != -1 and pos + 10 < len(mutated):
                        # Mutate bytes in the marker segment (e.g. Style fields)
                        # Offset +4 to +10 roughly covers Scod, SGcod, SPcod
                        idx = pos + 4 + random.randint(0, 6)
                        if idx < len(mutated):
                            mutated[idx] ^= (1 << random.randint(0, 7))
                    
                    # Try to mutate SIZ marker (Dimensions)
                    # SIZ marker is FF 51
                    pos = mutated.find(b'\xFF\x51')
                    if pos != -1 and pos + 15 < len(mutated):
                        # Xsiz/Ysiz are at offset +6 to +13
                        idx = pos + 6 + random.randint(0, 7)
                        if idx < len(mutated):
                            mutated[idx] ^= (1 << random.randint(0, 7))
                            
                    # If no markers found or additional random flip
                    if pos == -1:
                        idx = random.randint(0, len(mutated)-1)
                        mutated[idx] ^= (1 << random.randint(0, 7))
                
                else:
                    # General random bit flips
                    num_flips = random.randint(1, 4)
                    for _ in range(num_flips):
                        idx = random.randint(0, len(mutated)-1)
                        mutated[idx] ^= (1 << random.randint(0, 7))
                
                poc_path = os.path.join(base_dir, "poc.j2k")
                with open(poc_path, "wb") as f:
                    f.write(mutated)
                
                # Execute vulnerable binary
                proc = subprocess.run(
                    [opj_decompress, "-i", poc_path, "-o", out_file],
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE
                )
                
                # Check for crash
                # 66 is our ASAN custom exit code
                # -11 is SIGSEGV
                if proc.returncode == 66 or proc.returncode == -11:
                    return bytes(mutated)
                
                # Fallback check for ASAN output in stderr
                if b"AddressSanitizer" in proc.stderr or b"heap-buffer-overflow" in proc.stderr:
                    return bytes(mutated)
            
            # Return a valid file if no crash found (fallback)
            return bytes(seeds[0])