import os
import sys
import tarfile
import tempfile
import subprocess
import glob
import re
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        Strategy:
        1. Extract the source code.
        2. Identify the existing fuzz harness (LLVMFuzzerTestOneInput).
        3. Compile the harness with AddressSanitizer and LibFuzzer.
        4. Run the fuzzer to crash the application.
        5. Return the crash input.
        """
        # Use a temporary directory for build artifacts
        with tempfile.TemporaryDirectory() as temp_dir:
            # 1. Extract source
            try:
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=temp_dir)
            except Exception:
                return b""

            # 2. Source Discovery
            fuzz_target = None
            source_files = []
            include_dirs = set()
            is_cpp = False
            
            # Regex to detect main function (to exclude from linking)
            main_regex = re.compile(r'\b(int|void)\s+main\s*\(')

            for root, dirs, files in os.walk(temp_dir):
                for f in files:
                    full_path = os.path.join(root, f)
                    
                    # Gather include paths
                    if f.endswith(('.h', '.hpp')):
                        include_dirs.add(root)
                        # Add parent directory for cases like <folder/header.h>
                        include_dirs.add(os.path.dirname(root))

                    # Gather source files
                    if f.endswith(('.c', '.cpp', '.cc')):
                        if f.endswith(('.cpp', '.cc')):
                            is_cpp = True
                        
                        try:
                            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f_obj:
                                content = f_obj.read()
                                
                                # Identify Fuzzer Harness
                                if 'LLVMFuzzerTestOneInput' in content:
                                    fuzz_target = full_path
                                    continue # Don't add harness to general sources
                                
                                # Exclude files with main()
                                if main_regex.search(content):
                                    continue
                                
                                source_files.append(full_path)
                        except IOError:
                            pass

            if not fuzz_target:
                # Cannot solve without a target
                return b""

            # 3. Compile
            compiler = 'clang++' if is_cpp else 'clang'
            out_bin = os.path.join(temp_dir, 'fuzzer_harness')
            
            # Filter include_dirs to only those within temp_dir to prevent noise
            valid_includes = [f'-I{d}' for d in include_dirs if d.startswith(temp_dir)]
            
            # Base flags for ASan and Fuzzer
            flags = ['-g', '-O1', '-fsanitize=address,fuzzer']
            
            # Attempt 1: Compile with all discovered sources
            cmd = [compiler] + flags + valid_includes + [fuzz_target] + source_files + ['-o', out_bin]
            
            compiled = False
            try:
                subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                compiled = True
            except subprocess.CalledProcessError:
                # Attempt 2: Fallback to local sources only (same dir as harness)
                # This helps if there are unrelated source files causing build errors
                fuzz_dir = os.path.dirname(fuzz_target)
                local_sources = [s for s in source_files if os.path.dirname(s) == fuzz_dir]
                cmd = [compiler] + flags + valid_includes + [fuzz_target] + local_sources + ['-o', out_bin]
                try:
                    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    compiled = True
                except subprocess.CalledProcessError:
                    pass
            
            if not compiled:
                return b""

            # 4. Fuzz
            # Run the fuzzer with a timeout. Stack buffer overflows usually trigger quickly.
            # artifact_prefix ensures crash files are written to our temp dir.
            fuzz_cmd = [
                out_bin,
                f'-artifact_prefix={temp_dir}/',
                '-max_total_time=45',
                '-print_final_stats=1'
            ]
            
            try:
                subprocess.run(fuzz_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.SubprocessError:
                pass

            # 5. Retrieve Crash
            # Look for crash-* files generated by libFuzzer
            crashes = glob.glob(os.path.join(temp_dir, 'crash-*'))
            if not crashes:
                # Also check for leaks or timeouts
                crashes = glob.glob(os.path.join(temp_dir, 'leak-*')) + glob.glob(os.path.join(temp_dir, 'timeout-*'))
            
            if crashes:
                # Return the smallest crashing input (closest to minimal PoC)
                crashes.sort(key=os.path.getsize)
                try:
                    with open(crashes[0], 'rb') as f:
                        return f.read()
                except IOError:
                    return b""
            
            return b""