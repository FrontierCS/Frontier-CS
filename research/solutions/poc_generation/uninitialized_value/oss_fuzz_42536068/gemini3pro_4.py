import os
import sys
import tarfile
import subprocess
import shutil
import glob
import time

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a unique temporary directory
        work_dir = os.path.join("/tmp", f"poc_{int(time.time())}_{os.getpid()}")
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
        os.makedirs(work_dir)
        
        try:
            # Extract source code
            if src_path.endswith((".tar.gz", ".tgz")):
                with tarfile.open(src_path, "r:gz") as tar:
                    tar.extractall(path=work_dir)
            elif src_path.endswith(".tar"):
                with tarfile.open(src_path, "r:") as tar:
                    tar.extractall(path=work_dir)
            else:
                # Attempt generic extraction
                try:
                    with tarfile.open(src_path) as tar:
                        tar.extractall(path=work_dir)
                except:
                    pass

            # Find the fuzzer source file
            fuzzer_src = None
            for root, dirs, files in os.walk(work_dir):
                for file in files:
                    if file.endswith((".cc", ".cpp", ".c", ".cxx")):
                        path = os.path.join(root, file)
                        try:
                            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                                if "LLVMFuzzerTestOneInput" in f.read():
                                    fuzzer_src = path
                                    break
                        except:
                            continue
                if fuzzer_src:
                    break
            
            if not fuzzer_src:
                return b""

            # Identify include directories
            include_dirs = set()
            include_dirs.add(work_dir)
            for root, dirs, files in os.walk(work_dir):
                for file in files:
                    if file.endswith((".h", ".hpp")):
                        include_dirs.add(root)
            
            cflags = ["-g", "-O1", "-std=c++14"]
            for inc in include_dirs:
                cflags.append(f"-I{inc}")

            # Define target binary
            target_bin = os.path.join(work_dir, "fuzz_target")
            compiler = "clang++"
            if not shutil.which(compiler):
                compiler = "g++"

            # Build strategy:
            # Priority 1: MemorySanitizer (detects uninitialized values)
            # Priority 2: AddressSanitizer (detects memory errors, often triggered by uninit)
            # Priority 3: No sanitizer (just fuzzer)
            
            # Note: MSan requires code to be built with MSan. TinyGLTF is header-only, 
            # so building the fuzzer with MSan flags is sufficient.
            
            built = False
            
            # Attempt MSan build
            cmd_msan = [
                compiler, 
                "-fsanitize=fuzzer,memory", 
                "-fsanitize-memory-track-origins=2", 
                "-fno-omit-frame-pointer"
            ] + cflags + [fuzzer_src, "-o", target_bin]
            
            res = subprocess.run(cmd_msan, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0:
                built = True
            else:
                # Attempt ASan build
                cmd_asan = [
                    compiler, 
                    "-fsanitize=fuzzer,address", 
                    "-fno-omit-frame-pointer"
                ] + cflags + [fuzzer_src, "-o", target_bin]
                res = subprocess.run(cmd_asan, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if res.returncode == 0:
                    built = True
                else:
                    # Attempt plain Fuzzer build
                    cmd_plain = [
                        compiler, 
                        "-fsanitize=fuzzer"
                    ] + cflags + [fuzzer_src, "-o", target_bin]
                    res = subprocess.run(cmd_plain, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if res.returncode == 0:
                        built = True

            if not built or not os.path.exists(target_bin):
                return b""

            # Prepare Corpus
            corpus_dir = os.path.join(work_dir, "corpus")
            os.makedirs(corpus_dir, exist_ok=True)
            
            # Harvest seeds from source
            seed_extensions = {".gltf", ".glb", ".json", ".bin", ".xml", ".tiff", ".tif"}
            seeds_found = False
            for root, dirs, files in os.walk(work_dir):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in seed_extensions:
                        fpath = os.path.join(root, file)
                        # Filter out huge files to speed up fuzzing
                        if os.path.getsize(fpath) < 100 * 1024:
                            try:
                                shutil.copy(fpath, os.path.join(corpus_dir, file))
                                seeds_found = True
                            except:
                                pass
            
            if not seeds_found:
                with open(os.path.join(corpus_dir, "seed"), "wb") as f:
                    f.write(b" ")

            # Run Fuzzer
            artifact_prefix = os.path.join(work_dir, "crash-")
            fuzz_cmd = [
                target_bin,
                corpus_dir,
                "-max_total_time=60",      # Limit execution time
                "-minimize_crash=1",       # Try to reduce size (better score)
                f"-artifact_prefix={artifact_prefix}"
            ]
            
            subprocess.run(fuzz_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Check for crashes
            crashes = glob.glob(artifact_prefix + "*")
            if crashes:
                # Return the smallest crash input
                crashes.sort(key=os.path.getsize)
                with open(crashes[0], "rb") as f:
                    return f.read()
            
            return b""

        except Exception:
            return b""
        finally:
            # Cleanup
            if os.path.exists(work_dir):
                shutil.rmtree(work_dir, ignore_errors=True)