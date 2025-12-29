import os
import sys
import tarfile
import tempfile
import subprocess
import glob
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=temp_dir)
            except Exception:
                return b""

            extracted_root = temp_dir
            entries = os.listdir(temp_dir)
            if len(entries) == 1 and os.path.isdir(os.path.join(temp_dir, entries[0])):
                extracted_root = os.path.join(temp_dir, entries[0])

            fuzzer_src = None
            target_func = "polygonToCellsExperimental"
            
            for root, dirs, files in os.walk(extracted_root):
                for f in files:
                    if f.endswith(".c") and "fuzzer" in f.lower():
                        fpath = os.path.join(root, f)
                        try:
                            with open(fpath, "r", errors="ignore") as fp:
                                content = fp.read()
                                if target_func in content and "LLVMFuzzerTestOneInput" in content:
                                    fuzzer_src = fpath
                                    break
                        except:
                            pass
                if fuzzer_src: break
            
            if not fuzzer_src:
                for root, dirs, files in os.walk(extracted_root):
                     if any(x in root for x in ["test", "benchmark"]): continue
                     for f in files:
                        if f.endswith(".c"):
                            fpath = os.path.join(root, f)
                            try:
                                with open(fpath, "r", errors="ignore") as fp:
                                    content = fp.read()
                                    if target_func in content and "LLVMFuzzerTestOneInput" in content:
                                        fuzzer_src = fpath
                                        break
                            except:
                                pass
                     if fuzzer_src: break

            if not fuzzer_src:
                return b""

            include_dirs = []
            header_found = False
            for root, dirs, files in os.walk(extracted_root):
                if "h3api.h" in files:
                    include_dirs.append(root)
                    header_found = True
            
            if not header_found:
                for root, dirs, files in os.walk(extracted_root):
                    if "h3api.h.in" in files:
                        try:
                            in_path = os.path.join(root, "h3api.h.in")
                            out_path = os.path.join(root, "h3api.h")
                            with open(in_path, "r") as fin:
                                data = fin.read()
                                data = data.replace("@H3_VERSION_MAJOR@", "3")
                                data = data.replace("@H3_VERSION_MINOR@", "7")
                                data = data.replace("@H3_VERSION_PATCH@", "0")
                            with open(out_path, "w") as fout:
                                fout.write(data)
                            include_dirs.append(root)
                        except:
                            pass
                        break

            lib_srcs = []
            for root, dirs, files in os.walk(extracted_root):
                if any(x in root for x in ["app", "test", "fuzzer", "example", "benchmark"]):
                    continue
                for f in files:
                    if f.endswith(".c"):
                        lib_srcs.append(os.path.join(root, f))
            
            include_dirs = list(set(include_dirs))
            for root, dirs, files in os.walk(extracted_root):
                if any(f.endswith(".h") for f in files):
                    if root not in include_dirs:
                        include_dirs.append(root)

            fuzzer_bin = os.path.join(temp_dir, "harness")
            cmd = ["clang", "-fsanitize=address,fuzzer", "-O2", "-g", "-fno-omit-frame-pointer"]
            for inc in include_dirs:
                cmd.append(f"-I{inc}")
            cmd.extend(lib_srcs)
            cmd.append(fuzzer_src)
            cmd.extend(["-o", fuzzer_bin, "-lm"])

            try:
                subprocess.run(cmd, cwd=temp_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                return b""

            run_cmd = [fuzzer_bin, "-max_total_time=60", "-print_final_stats=1"]
            try:
                subprocess.run(run_cmd, cwd=temp_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass
            
            crashes = glob.glob(os.path.join(temp_dir, "crash-*"))
            if not crashes:
                return b""
            
            target = crashes[0]
            
            min_cmd = [fuzzer_bin, "-minimize_crash=1", "-max_total_time=15", target]
            try:
                subprocess.run(min_cmd, cwd=temp_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass
            
            mins = glob.glob(os.path.join(temp_dir, "minimized-from-*"))
            if mins:
                mins.sort(key=os.path.getsize)
                target = mins[0]
            
            with open(target, "rb") as f:
                return f.read()