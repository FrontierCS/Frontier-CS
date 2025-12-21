import os
import sys
import subprocess
import tempfile
import tarfile
import glob

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a temporary directory for build and execution
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract source code
            try:
                if src_path.endswith('.tar.gz') or src_path.endswith('.tgz'):
                    with tarfile.open(src_path, "r:gz") as tar:
                        tar.extractall(path=temp_dir)
                elif src_path.endswith('.tar'):
                    with tarfile.open(src_path, "r:") as tar:
                        tar.extractall(path=temp_dir)
                else:
                    # Attempt to treat as tar if extension is unknown but file exists
                    try:
                        with tarfile.open(src_path, "r:") as tar:
                            tar.extractall(path=temp_dir)
                    except:
                        pass
            except Exception:
                return b""

            # Locate source files and fuzzer candidates
            lib_srcs = []
            include_dirs = set()
            fuzzer_src = None
            candidate_fuzzers = []

            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    norm_path = os.path.normpath(file_path)
                    
                    if file.endswith(".c"):
                        # Check for libFuzzer entry point
                        try:
                            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                                if "LLVMFuzzerTestOneInput" in content:
                                    candidate_fuzzers.append(file_path)
                                else:
                                    # Heuristic: Library sources are usually in h3lib/lib
                                    # We exclude tests, apps, examples to avoid multiple main() definitions
                                    if "h3lib" in norm_path and "lib" in norm_path:
                                        lib_srcs.append(file_path)
                        except IOError:
                            pass
                    
                    # Collect include directories (looking for h3api.h)
                    if file == "h3api.h":
                        include_dirs.add(root)
            
            # Select the most relevant fuzzer based on keywords
            # The vulnerability is in polygonToCells (experimental)
            keywords = ["polygonToCells", "polyfill", "experimental"]
            
            for f in candidate_fuzzers:
                base = os.path.basename(f)
                if any(k in base for k in keywords):
                    fuzzer_src = f
                    break
            
            # Fallback to first available fuzzer
            if not fuzzer_src and candidate_fuzzers:
                fuzzer_src = candidate_fuzzers[0]
            
            if not fuzzer_src:
                return b""

            # Construct build command
            fuzzer_bin = os.path.join(temp_dir, "fuzzer_bin")
            cmd = [
                "clang",
                "-fsanitize=address,fuzzer",
                "-O2", "-g",
                "-o", fuzzer_bin,
                fuzzer_src
            ] + lib_srcs
            
            for inc in include_dirs:
                cmd.append(f"-I{inc}")
            
            # Add other header locations inside h3lib if needed
            extra_includes = set()
            for root, dirs, files in os.walk(temp_dir):
                if "h3lib" in root and any(f.endswith(".h") for f in files):
                    extra_includes.add(root)
            for inc in extra_includes:
                if inc not in include_dirs:
                    cmd.append(f"-I{inc}")

            # Compile the fuzzer
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                return b""

            # Run the fuzzer
            corpus_dir = os.path.join(temp_dir, "corpus")
            os.makedirs(corpus_dir, exist_ok=True)
            
            # We use parallel workers to increase the chance of finding the crash quickly
            # within the constraints.
            fuzz_cmd = [
                fuzzer_bin,
                corpus_dir,
                "-max_total_time=60",      # Limit execution time
                "-rss_limit_mb=2560",      # Memory limit
                "-workers=4",              # Parallel workers
                "-jobs=4",
                "-print_final_stats=0"
            ]
            
            try:
                # Fuzzer returns non-zero on crash, which is expected
                subprocess.run(fuzz_cmd, cwd=temp_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
            
            # Retrieve crash artifacts
            # libFuzzer writes artifacts like crash-<sha1> or leak-<sha1> to CWD
            crashes = glob.glob(os.path.join(temp_dir, "crash-*"))
            crashes += glob.glob(os.path.join(temp_dir, "leak-*"))
            
            if crashes:
                # Sort by size (smallest first) to maximize score
                crashes.sort(key=os.path.getsize)
                try:
                    with open(crashes[0], "rb") as f:
                        return f.read()
                except IOError:
                    pass
            
            return b""
