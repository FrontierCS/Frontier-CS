import os
import sys
import tarfile
import subprocess
import shutil
import time
import glob
import random

class Solution:
    def solve(self, src_path: str) -> bytes:
        # 1. Setup workspace
        base_dir = "/tmp/work_dash_client"
        if os.path.exists(base_dir):
            shutil.rmtree(base_dir)
        os.makedirs(base_dir)
        
        # 2. Extract source
        try:
            with tarfile.open(src_path) as tar:
                tar.extractall(path=base_dir)
        except Exception:
            pass

        # 3. Locate source root
        src_root = base_dir
        for root, dirs, files in os.walk(base_dir):
            if "configure" in files:
                src_root = root
                break
        
        # 4. Configure and Build
        env = os.environ.copy()
        cflags = "-fsanitize=address -g -O1"
        env['CFLAGS'] = cflags
        env['CXXFLAGS'] = cflags
        env['LDFLAGS'] = cflags
        
        # Minimal configure arguments to speed up build and avoid dependencies
        conf_args = [
            "./configure",
            "--disable-shared",
            "--enable-static",
            "--enable-debug",
            "--disable-x11",
            "--disable-gl",
            "--disable-ssl",
            "--disable-opt"
        ]
        
        # Run configure
        if os.path.exists(os.path.join(src_root, "configure")):
            try:
                subprocess.run(conf_args, cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
            except:
                pass
        
        # Run make
        try:
            subprocess.run(["make", "-j8"], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
        except:
            pass
        
        # 5. Locate binary
        target_bin = None
        # Prioritize fuzzers/tests
        for root, dirs, files in os.walk(src_root):
            for f in files:
                full_path = os.path.join(root, f)
                if os.access(full_path, os.X_OK) and not f.endswith(".sh") and not f.endswith(".py"):
                    if "fuzz" in f:
                        target_bin = full_path
                        break
            if target_bin: break
            
        # Fallback to dash_client or MP4Client
        if not target_bin:
             for root, dirs, files in os.walk(src_root):
                for f in files:
                    if f in ["dash_client", "MP4Client", "gpac"] and os.access(os.path.join(root, f), os.X_OK):
                        target_bin = os.path.join(root, f)
                        break
                if target_bin: break

        if not target_bin:
            # If no binary found, return a heuristic guess
            return b"http://a\x00"

        # 6. Fuzzing
        # Check if it's a libFuzzer binary
        is_libfuzzer = False
        try:
            res = subprocess.run([target_bin, "-help=1"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
            if b"libFuzzer" in res.stderr or b"libFuzzer" in res.stdout:
                is_libfuzzer = True
        except:
            pass
            
        corpus_dir = os.path.join(base_dir, "corpus")
        os.makedirs(corpus_dir, exist_ok=True)
        
        # Seeds appropriate for DASH/HTTP/Short inputs
        seeds = [
            b"http://", b"https://", b"dash://", b"file://",
            b"http://a", b"123456789", b"A"*9, b"\x00"*9,
            b"<MPD", b"urn:", b"segment"
        ]
        
        if is_libfuzzer:
            # Create seed corpus
            for i, s in enumerate(seeds):
                with open(os.path.join(corpus_dir, f"seed{i}"), "wb") as f:
                    f.write(s)
            
            # Run libFuzzer
            # Limit time and length
            cmd = [target_bin, corpus_dir, "-max_total_time=60", "-max_len=20"]
            try:
                subprocess.run(cmd, cwd=base_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=70)
            except:
                pass
            
            # Check for crash artifacts
            crashes = glob.glob(os.path.join(base_dir, "crash-*")) + glob.glob(os.path.join(base_dir, "leak-*"))
            if crashes:
                crashes.sort(key=lambda x: os.path.getsize(x))
                with open(crashes[0], "rb") as f:
                    return f.read()
        
        else:
            # CLI Fuzzing loop
            start_time = time.time()
            idx = 0
            while time.time() - start_time < 60:
                # Generate candidate
                if idx < len(seeds):
                    data = seeds[idx]
                else:
                    # Mutate
                    parent = random.choice(seeds)
                    if not parent: parent = b"A"
                    method = random.random()
                    if method < 0.4:
                        # Append
                        data = parent + os.urandom(1)
                    elif method < 0.8:
                        # Flip
                        ba = bytearray(parent)
                        pos = random.randint(0, len(ba)-1)
                        ba[pos] ^= random.randint(1, 255)
                        data = bytes(ba)
                    else:
                        # Random
                        data = os.urandom(random.randint(1, 15))
                
                # Keep length reasonable for 9 byte target
                if len(data) > 32: data = data[:32]
                idx += 1
                
                # Write input to file
                poc_file = os.path.join(base_dir, "input.bin")
                with open(poc_file, "wb") as f:
                    f.write(data)
                
                # Run binary
                try:
                    # Try passing file path
                    cmd = [target_bin, poc_file]
                    p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=0.2)
                    
                    if p.returncode != 0:
                        if b"AddressSanitizer" in p.stderr:
                            return data
                            
                    # Try passing as argument (if textual)
                    try:
                        str_data = data.decode('utf-8')
                        cmd2 = [target_bin, str_data]
                        p2 = subprocess.run(cmd2, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=0.2)
                        if p2.returncode != 0 and b"AddressSanitizer" in p2.stderr:
                            return data
                    except:
                        pass
                except:
                    pass
                    
        return b"123456789"