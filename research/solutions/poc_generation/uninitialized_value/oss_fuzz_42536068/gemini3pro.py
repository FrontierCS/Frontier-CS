import os
import sys
import tarfile
import subprocess
import tempfile
import glob
import re
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        work_dir = tempfile.mkdtemp()
        
        # Extract source code
        try:
            if tarfile.is_tarfile(src_path):
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=work_dir)
        except Exception:
            pass

        # Locate source files and potential harnesses
        potential_harnesses = []
        source_files = []
        include_dirs = set()
        
        cpp_exts = ('.cpp', '.cc', '.cxx', '.c')
        
        for root, dirs, files in os.walk(work_dir):
            include_dirs.add(root)
            for f in files:
                path = os.path.join(root, f)
                if f.lower().endswith(cpp_exts):
                    # Check if file is a fuzz harness
                    is_harness = False
                    try:
                        with open(path, 'r', encoding='latin-1') as fp:
                            content = fp.read()
                            if "LLVMFuzzerTestOneInput" in content:
                                is_harness = True
                            
                            if not is_harness:
                                # Skip files with main() to avoid link collisions
                                if re.search(r'\bint\s+main\s*\(', content):
                                    continue
                    except:
                        continue
                    
                    if is_harness:
                        potential_harnesses.append(path)
                    else:
                        # Exclude tests/examples which might be standalone and cause link errors
                        if "test" in f.lower() or "example" in f.lower():
                            continue
                        source_files.append(path)
                elif f.lower().endswith('.h'):
                    include_dirs.add(root)

        # Select the best harness
        harness_file = None
        # Prefer 'console' fuzzer if available as it likely exercises more API
        for h in potential_harnesses:
            if "console" in os.path.basename(h):
                harness_file = h
                break
        if not harness_file and potential_harnesses:
            harness_file = potential_harnesses[0]
            
        if not harness_file:
            # Cannot build without harness, return generic XML likely to trigger basic issues
            return b"<xml attr='val'/>"

        # Determine compiler
        all_files = [harness_file] + source_files
        is_cpp = any(f.lower().endswith(('.cpp', '.cc', '.cxx')) for f in all_files)
        compiler = "clang++" if is_cpp else "clang"
        
        fuzz_bin = os.path.join(work_dir, "fuzzer")
        
        # Compilation flags for MSan and Fuzzing
        # MSan is required for "Uninitialized Value" detection
        cflags = [
            "-g", "-O1", 
            "-fsanitize=fuzzer,memory", 
            "-fsanitize-memory-track-origins"
        ]
        inc_flags = [f"-I{d}" for d in include_dirs]
        
        # Compilation attempt 1: Harness + All Sources
        cmd = [compiler] + cflags + [harness_file] + source_files + inc_flags + ["-o", fuzz_bin]
        
        compiled = False
        try:
            subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            compiled = True
        except subprocess.CalledProcessError:
            # Compilation attempt 2: Harness + Sources in same dir only (minimize link errors)
            harness_dir = os.path.dirname(harness_file)
            subset_sources = [s for s in source_files if os.path.dirname(s) == harness_dir]
            cmd = [compiler] + cflags + [harness_file] + subset_sources + inc_flags + ["-o", fuzz_bin]
            try:
                subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                compiled = True
            except subprocess.CalledProcessError:
                pass
        
        if not compiled:
            return b"<xml attr='val'/>"

        # Prepare corpus with seeds targeting attribute conversion
        # The vulnerability description relates to unsuccessful attribute conversions.
        corpus_dir = os.path.join(work_dir, "corpus")
        os.makedirs(corpus_dir, exist_ok=True)
        
        seeds = [
            b"<a b='x'/>",
            b"<a b='0'/>",
            b"<a b='-1'/>",
            b"<doc><e attr='val'/></doc>",
            b"<?xml version='1.0'?><data value='true'/>",
            b"<x y='999999999999999999'/>",
            b"<e a=''/>",
            b"<e a='1.5'/>"
        ]
        
        for i, s in enumerate(seeds):
            with open(os.path.join(corpus_dir, f"seed_{i}"), 'wb') as f:
                f.write(s)

        # Run Fuzzer
        artifact_prefix = os.path.join(work_dir, "crash-")
        # Run with parallel jobs to utilize available vCPUs
        run_cmd = [
            fuzz_bin, 
            corpus_dir, 
            "-max_total_time=45", 
            "-jobs=8", 
            "-workers=8",
            f"-artifact_prefix={artifact_prefix}"
        ]
        
        try:
            subprocess.run(run_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass

        # Check for crashes
        crashes = glob.glob(artifact_prefix + "*")
        if crashes:
            # Return shortest crash to optimize score
            crashes.sort(key=os.path.getsize)
            with open(crashes[0], 'rb') as f:
                return f.read()

        # Fallback if no crash found
        return seeds[0]