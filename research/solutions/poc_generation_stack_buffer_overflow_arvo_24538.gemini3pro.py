import os
import tarfile
import subprocess
import tempfile
import shutil
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=tmp_dir)
            except:
                return b""

            src_file = None
            for root, dirs, files in os.walk(tmp_dir):
                for f in files:
                    if f.endswith(".c") or f.endswith(".cpp"):
                        src_file = os.path.join(root, f)
                        break
                if src_file:
                    break
            
            if not src_file:
                return b""

            bin_path = os.path.join(tmp_dir, "vuln")
            cc = "g++" if src_file.endswith(".cpp") else "gcc"
            
            cmd = [cc, src_file, "-o", bin_path, "-fsanitize=address", "-g", "-w"]
            try:
                subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                return b""

            prefixes = {b"", b"GNU", b"GNU\x01", b"\x65"}
            try:
                with open(src_file, "rb") as f:
                    content = f.read()
                    for m in re.findall(b'"([^"]+)"', content):
                        if len(m) < 50:
                            prefixes.add(m)
            except:
                pass
            
            crashes = []
            sorted_prefixes = sorted(list(prefixes), key=len)
            
            for prefix in sorted_prefixes:
                for length in range(0, 100):
                    payload = prefix + b"A" * length
                    
                    try:
                        proc = subprocess.run(
                            [bin_path], 
                            input=payload, 
                            stdout=subprocess.DEVNULL, 
                            stderr=subprocess.PIPE, 
                            timeout=0.1
                        )
                        if proc.returncode != 0 and b"AddressSanitizer" in proc.stderr:
                            crashes.append(payload)
                            break
                    except:
                        pass
                    
                    try:
                        poc_path = os.path.join(tmp_dir, "poc.bin")
                        with open(poc_path, "wb") as f:
                            f.write(payload)
                        proc = subprocess.run(
                            [bin_path, poc_path], 
                            stdout=subprocess.DEVNULL, 
                            stderr=subprocess.PIPE, 
                            timeout=0.1
                        )
                        if proc.returncode != 0 and b"AddressSanitizer" in proc.stderr:
                            crashes.append(payload)
                            break
                    except:
                        pass
            
            if crashes:
                crashes.sort(key=len)
                return crashes[0]
                
        return b""