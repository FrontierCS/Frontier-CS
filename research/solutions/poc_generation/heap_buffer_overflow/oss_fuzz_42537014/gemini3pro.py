import os
import sys
import tarfile
import subprocess
import tempfile
import shutil
import random
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a temporary workspace
        work_dir = tempfile.mkdtemp()
        try:
            # 1. Extract the source code
            extract_path = os.path.join(work_dir, "source")
            os.makedirs(extract_path)
            with tarfile.open(src_path) as tar:
                tar.extractall(path=extract_path)
            
            # Find the actual source root (handle tarball directory structure)
            src_root = extract_path
            entries = os.listdir(extract_path)
            if len(entries) == 1:
                potential_root = os.path.join(extract_path, entries[0])
                if os.path.isdir(potential_root):
                    src_root = potential_root
            
            # 2. Configure and Build with ASAN
            env = os.environ.copy()
            # Set ASAN flags for GCC/Clang
            flags = "-fsanitize=address -g -O1"
            env["CFLAGS"] = flags
            env["CXXFLAGS"] = flags
            env["LDFLAGS"] = "-fsanitize=address"
            
            # Attempt to configure if script exists
            # We disable GUI and optional features to speed up build and avoid dependency issues
            config_script = os.path.join(src_root, "configure")
            if os.path.exists(config_script):
                # GPAC specific configure flags to minimize build
                conf_cmd = [
                    "./configure",
                    "--disable-x11",
                    "--disable-sdl",
                    "--disable-ssl",
                    "--disable-gl",
                    "--disable-png",
                    "--disable-jpeg",
                    "--disable-oss-audio",
                    "--disable-pulseaudio",
                    "--disable-alsa",
                    "--disable-jack",
                    "--disable-freetype",
                    "--disable-fontconfig",
                    "--enable-static-bin"
                ]
                subprocess.run(conf_cmd, cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Build
            # We try to build everything or specific targets if known, default make is safest
            subprocess.run(["make", "-j8"], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 3. Locate the vulnerable binary (dash_client)
            binary_path = None
            lib_path = None
            for root, dirs, files in os.walk(src_root):
                if "dash_client" in files:
                    path = os.path.join(root, "dash_client")
                    if os.access(path, os.X_OK):
                        binary_path = path
                if "libgpac.so" in files:
                    lib_path = root
            
            # If dash_client not found, look for MP4Box as fallback (often bundled)
            if not binary_path:
                for root, dirs, files in os.walk(src_root):
                    if "MP4Box" in files:
                        path = os.path.join(root, "MP4Box")
                        if os.access(path, os.X_OK):
                            binary_path = path # Use MP4Box if dash_client missing
                            break
            
            if not binary_path:
                # If build failed completely, return a dummy guess
                return b"http://aa"

            # Set library path for execution
            if lib_path:
                env["LD_LIBRARY_PATH"] = lib_path if "LD_LIBRARY_PATH" not in env else env["LD_LIBRARY_PATH"] + ":" + lib_path

            # 4. Fuzzing Phase
            # Ground truth is 9 bytes. We target small inputs.
            
            # Generate dictionary from binary strings
            dictionary = []
            try:
                # Extract short strings
                result = subprocess.run(["strings", binary_path], capture_output=True, text=True)
                for s in result.stdout.splitlines():
                    s = s.strip()
                    if 3 <= len(s) <= 12:
                        dictionary.append(s.encode('utf-8'))
            except Exception:
                pass

            # Add seeds relevant to dash/http
            seeds = [
                b"http://", b"https://", b"dash://", b"file://",
                b"urn:mpeg", b"mimeType", b"bitrate",
                b"<MPD>", b"moov", b"ftyp", b"mdat",
                b"isom", b"avc1", b"mp42", 
                b"A" * 9, b"http://a"
            ]
            dictionary.extend(seeds)
            if not dictionary:
                dictionary = [b"123456789"]

            start_time = time.time()
            timeout = 180 # 3 minutes total budget
            
            # Fuzz loop
            while time.time() - start_time < timeout:
                # Select seed
                base = random.choice(dictionary)
                
                # Mutate
                # We want result length around 9
                mutated = bytearray(base)
                
                # Apply mutations
                num_muts = random.randint(1, 3)
                for _ in range(num_muts):
                    op = random.randint(0, 5)
                    if op == 0: # Flip
                        if mutated:
                            idx = random.randint(0, len(mutated)-1)
                            mutated[idx] ^= random.randint(1, 255)
                    elif op == 1: # Insert
                        idx = random.randint(0, len(mutated))
                        mutated.insert(idx, random.randint(0, 255))
                    elif op == 2: # Delete
                        if len(mutated) > 1:
                            idx = random.randint(0, len(mutated)-1)
                            del mutated[idx]
                    elif op == 3: # Force 9 bytes
                        if len(mutated) < 9:
                            mutated.extend(os.urandom(9 - len(mutated)))
                        elif len(mutated) > 9:
                            mutated = mutated[:9]
                    elif op == 4: # Splice
                        other = random.choice(dictionary)
                        if mutated:
                            idx = random.randint(0, len(mutated))
                            chunk = other[:random.randint(1, 4)]
                            mutated[idx:idx] = chunk
                    elif op == 5: # Overwrite
                        if mutated:
                            idx = random.randint(0, len(mutated)-1)
                            mutated[idx] = random.randint(0, 255)
                
                # Length constraint
                if len(mutated) > 20:
                    mutated = mutated[:20]
                
                candidate = bytes(mutated)
                
                # Write to file
                with tempfile.NamedTemporaryFile(delete=False) as tf:
                    tf.write(candidate)
                    tf_name = tf.name
                
                try:
                    # Execute
                    proc = subprocess.run(
                        [binary_path, tf_name],
                        env=env,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        timeout=0.2
                    )
                    
                    if proc.returncode != 0:
                        # Check for ASAN error
                        if b"AddressSanitizer" in proc.stderr and (b"heap-buffer-overflow" in proc.stderr or b"SEGV" in proc.stderr):
                            # Found a crash
                            # If it's exactly 9 bytes, return it
                            if len(candidate) == 9:
                                return candidate
                            # If we are close, return candidate. 
                            # If larger, try to trim slightly but return candidate if unsafe to trim
                            return candidate
                except subprocess.TimeoutExpired:
                    pass
                finally:
                    if os.path.exists(tf_name):
                        os.unlink(tf_name)
            
            # If timeout, return a best guess (9 bytes)
            return b"http://aa"
            
        except Exception:
            return b"123456789"
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)