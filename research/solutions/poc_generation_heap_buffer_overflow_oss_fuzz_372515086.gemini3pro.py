import os
import sys
import subprocess
import tarfile
import tempfile
import shutil
import glob

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability by compiling the target
        with ASAN/LibFuzzer and running it.
        """
        temp_dir = tempfile.mkdtemp()
        try:
            # Extract source code
            if src_path.endswith('.tar.gz') or src_path.endswith('.tgz'):
                with tarfile.open(src_path, "r:gz") as tar:
                    tar.extractall(path=temp_dir)
            elif src_path.endswith('.tar'):
                with tarfile.open(src_path, "r:") as tar:
                    tar.extractall(path=temp_dir)
            else:
                try:
                    with tarfile.open(src_path) as tar:
                        tar.extractall(path=temp_dir)
                except:
                    pass

            # Scan for source files, headers, and fuzzer harness
            c_files = []
            h_dirs = set()
            harness_candidates = []

            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    if file.endswith(".h"):
                        h_dirs.add(root)
                    elif file.endswith(".c") or file.endswith(".cc") or file.endswith(".cpp"):
                        try:
                            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read()
                                if "LLVMFuzzerTestOneInput" in content:
                                    harness_candidates.append((full_path, content))
                                    continue
                                if " main(" in content or " main (" in content:
                                    # Skip files with main to avoid link collisions
                                    continue
                                c_files.append(full_path)
                        except:
                            pass

            if not harness_candidates:
                return b""

            # Select the most appropriate harness
            # Priority: mentions 'polygonToCellsExperimental', then 'polygonToCells', then any.
            target_harness = harness_candidates[0][0]
            best_priority = 0
            
            for path, content in harness_candidates:
                priority = 1
                if "polygonToCells" in content:
                    priority = 2
                if "polygonToCellsExperimental" in content:
                    priority = 3
                
                if priority > best_priority:
                    best_priority = priority
                    target_harness = path

            # Prepare compilation
            compiler = "clang"
            if target_harness.endswith(".cc") or target_harness.endswith(".cpp"):
                compiler = "clang++"
            
            fuzzer_bin = os.path.join(temp_dir, "fuzz_target")
            
            cmd = [
                compiler,
                "-fsanitize=address,fuzzer",
                "-O1",
                "-g",
                "-D_GNU_SOURCE",
                "-Wno-everything"
            ]
            
            for inc in h_dirs:
                cmd.extend(["-I", inc])
            
            cmd.append(target_harness)
            cmd.extend(c_files)
            cmd.extend(["-o", fuzzer_bin, "-lm"])

            # Compile
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if not os.path.exists(fuzzer_bin):
                return b""

            # Run Fuzzer
            # Set time limit to find the crash.
            fuzz_cmd = [
                fuzzer_bin,
                "-max_total_time=45",
                "-rss_limit_mb=2048",
                "-print_final_stats=0"
            ]
            
            subprocess.run(fuzz_cmd, cwd=temp_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Retrieve crash artifact
            # LibFuzzer outputs files named crash-<sha1>, leak-<sha1>, etc.
            crashes = glob.glob(os.path.join(temp_dir, "crash-*"))
            if not crashes:
                crashes = glob.glob(os.path.join(temp_dir, "leak-*"))
            
            if crashes:
                with open(crashes[0], "rb") as f:
                    return f.read()

        except Exception:
            pass
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        return b""