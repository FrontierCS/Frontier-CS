import os
import sys
import subprocess
import tempfile
import glob
import random
import shutil
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp()
        try:
            # Extract source
            extract_dir = os.path.join(work_dir, "src")
            os.makedirs(extract_dir)
            subprocess.run(["tar", "xf", src_path, "-C", extract_dir], 
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            build_root = extract_dir
            for root, dirs, files in os.walk(extract_dir):
                if "configure" in files:
                    build_root = root
                    break
            
            # Setup build environment
            env = os.environ.copy()
            if shutil.which("clang"):
                env['CC'] = 'clang'
                env['CXX'] = 'clang++'
            else:
                env['CC'] = 'gcc'
                env['CXX'] = 'g++'
            
            env['CFLAGS'] = '-fsanitize=address -g -O1'
            env['CXXFLAGS'] = '-fsanitize=address -g -O1'
            env['LDFLAGS'] = '-fsanitize=address'
            
            # Configure
            subprocess.run(["./configure", "--static-bin", "--disable-X11", "--disable-ssl", "--disable-x11"], 
                           cwd=build_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Make
            subprocess.run(["make", "-j8"], cwd=build_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Find MP4Box binary
            mp4box = None
            for root, dirs, files in os.walk(build_root):
                if "MP4Box" in files:
                    path = os.path.join(root, "MP4Box")
                    if os.access(path, os.X_OK):
                        mp4box = path
                        break
            
            if not mp4box:
                return b""

            # Gather seeds
            seeds = []
            for ext in ["*.hevc", "*.hvc", "*.265"]:
                seeds.extend(glob.glob(os.path.join(build_root, "**", ext), recursive=True))
            
            # Fallback to mp4 seeds if no raw hevc found
            if not seeds:
                seeds.extend(glob.glob(os.path.join(build_root, "**", "*.mp4"), recursive=True))
                
            seeds = [s for s in seeds if os.path.getsize(s) < 100 * 1024]
            seeds.sort(key=os.path.getsize)
            
            # Fuzzing Loop
            start_time = time.time()
            # Run for up to 5 minutes
            while time.time() - start_time < 300:
                if seeds:
                    # Pick a small seed
                    seed_path = seeds[random.randint(0, min(len(seeds)-1, 20))]
                    with open(seed_path, "rb") as f:
                        data = bytearray(f.read())
                else:
                    # Fallback dummy seed
                    data = bytearray(b"\x00\x00\x00\x01\x40\x01\x0c\x01\xff\xff\x01\x60\x00\x00\x03\x00\x00\x03\x00\x00\x03\x00\x00\x03\x00\x78\xac\x09")

                # Mutate
                mutation = random.random()
                if mutation < 0.4:
                    # Bit flips
                    num_flips = random.randint(1, 8)
                    for _ in range(num_flips):
                        if len(data) > 0:
                            idx = random.randint(0, len(data) - 1)
                            data[idx] ^= (1 << random.randint(0, 7))
                elif mutation < 0.7:
                    # Insert zeros (to expand Exp-Golomb values common in slice headers)
                    if len(data) > 0:
                        idx = random.randint(0, len(data))
                        count = random.randint(1, 5)
                        for _ in range(count):
                            data.insert(idx, 0)
                else:
                    # Byte overwrite
                    if len(data) > 0:
                        idx = random.randint(0, len(data) - 1)
                        data[idx] = random.choice([0xFF, 0x00, 0x80, 0x7F])

                # Create temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".hevc") as tf:
                    tf.write(data)
                    tf_path = tf.name

                # Execute
                try:
                    # Use -add to force parsing/importing of the bitstream
                    cmd = [mp4box, "-add", tf_path, "-new", "/dev/null"]
                    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=2)
                    
                    if proc.returncode != 0:
                        stderr = proc.stderr.decode(errors='ignore')
                        if "AddressSanitizer" in stderr and "stack-buffer-overflow" in stderr:
                            os.remove(tf_path)
                            return bytes(data)
                except subprocess.TimeoutExpired:
                    pass
                finally:
                    if os.path.exists(tf_path):
                        os.remove(tf_path)

            return b""

        except Exception:
            return b""
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
