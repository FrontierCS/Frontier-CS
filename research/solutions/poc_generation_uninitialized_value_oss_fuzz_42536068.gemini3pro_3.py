import os
import sys
import subprocess
import tempfile
import glob

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        Strategy:
        1. Extract the source code.
        2. Identify the fuzz target (LLVMFuzzerTestOneInput) and other source files.
        3. Compile the project with clang, MemorySanitizer, and libFuzzer.
        4. Run the fuzzer to find a crashing input.
        """
        with tempfile.TemporaryDirectory() as work_dir:
            # 1. Extract source
            try:
                subprocess.run(['tar', '-xf', src_path, '-C', work_dir], 
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                return b''

            # Find project root
            project_root = work_dir
            entries = os.listdir(work_dir)
            if len(entries) == 1 and os.path.isdir(os.path.join(work_dir, entries[0])):
                project_root = os.path.join(work_dir, entries[0])

            # 2. Identify source files and fuzz target
            fuzz_target_path = None
            source_files = []
            include_dirs = set()

            for root, dirs, files in os.walk(project_root):
                include_dirs.add(root)
                for filename in files:
                    file_path = os.path.join(root, filename)
                    if filename.endswith(('.c', '.cc', '.cpp', '.cxx')):
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if 'LLVMFuzzerTestOneInput' in content:
                                    fuzz_target_path = file_path
                                else:
                                    # Heuristic: exclude files with main() to avoid linker errors
                                    if 'int main' not in content and 'void main' not in content:
                                        source_files.append(file_path)
                        except IOError:
                            pass

            if not fuzz_target_path:
                return b''

            # 3. Compile
            bin_path = os.path.join(work_dir, 'fuzzer_bin')
            
            # Build command: clang++ with MSan and fuzzer
            cmd = [
                'clang++',
                '-g', '-O1',
                '-fsanitize=memory',
                '-fsanitize=fuzzer',
                '-fno-omit-frame-pointer',
                '-Wno-everything'  # Suppress warnings
            ]
            
            # Add include paths
            for inc in include_dirs:
                cmd.extend(['-I', inc])
            
            # Add sources
            cmd.append(fuzz_target_path)
            cmd.extend(source_files)
            cmd.extend(['-o', bin_path])

            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                # If compilation fails, we can't fuzz
                return b''

            # 4. Fuzz
            corpus_dir = os.path.join(work_dir, 'corpus')
            os.makedirs(corpus_dir, exist_ok=True)
            
            # Create seed inputs
            with open(os.path.join(corpus_dir, 'seed1'), 'wb') as f:
                f.write(b'\x00' * 128)
            with open(os.path.join(corpus_dir, 'seed2'), 'wb') as f:
                f.write(b'A' * 128)

            fuzz_cmd = [
                bin_path,
                corpus_dir,
                '-max_total_time=60',   # Limit execution time
                '-jobs=8',              # Use available CPUs
                '-workers=8',
                '-use_value_profile=1'  # Help comparisons
            ]

            try:
                # Run fuzzer. It returns non-zero on crash, so we ignore CalledProcessError
                subprocess.run(fuzz_cmd, cwd=work_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                pass

            # 5. Retrieve crash
            # libFuzzer saves artifacts starting with 'crash-' in the current working directory
            crashes = [f for f in os.listdir(work_dir) if f.startswith('crash-')]
            
            if crashes:
                # Return the content of the first crash found
                with open(os.path.join(work_dir, crashes[0]), 'rb') as f:
                    return f.read()

            return b''
