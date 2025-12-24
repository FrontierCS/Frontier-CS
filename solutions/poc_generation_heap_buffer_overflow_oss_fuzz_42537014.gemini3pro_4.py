import os
import sys
import tarfile
import tempfile
import subprocess
import glob
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract source code
            try:
                with tarfile.open(src_path) as tar:
                    tar.extractall(path=temp_dir)
            except Exception:
                return b'A' * 9

            # Find fuzz target and source files
            fuzz_target = None
            sources = []
            include_dirs = set()

            for root, dirs, files in os.walk(temp_dir):
                include_dirs.add(root)
                for file in files:
                    file_path = os.path.join(root, file)
                    if file.endswith(('.c', '.cc', '.cpp')):
                        try:
                            with open(file_path, 'r', errors='ignore') as f:
                                content = f.read()
                                if 'LLVMFuzzerTestOneInput' in content:
                                    fuzz_target = file_path
                                elif 'int main' not in content:
                                    sources.append(file_path)
                        except IOError:
                            pass

            if not fuzz_target:
                return b'A' * 9

            # Build compilation command
            fuzzer_bin = os.path.join(temp_dir, 'fuzzer')
            # Try clang++ first as it covers C++ and C
            compiler = 'clang++'
            
            cmd = [
                compiler,
                '-g', '-O1',
                '-fsanitize=address,fuzzer',
                '-o', fuzzer_bin,
                fuzz_target
            ] + sources
            
            for inc in include_dirs:
                cmd.extend(['-I', inc])

            # Compile
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                # Fallback to clang if pure C is preferred or C++ fails linking
                try:
                    cmd[0] = 'clang'
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except subprocess.CalledProcessError:
                    return b'A' * 9

            # Generate dictionary from source strings to speed up fuzzing
            dict_path = os.path.join(temp_dir, 'fuzz.dict')
            try:
                strings = set()
                with open(fuzz_target, 'r', errors='ignore') as f:
                    content = f.read()
                    # Find string literals
                    matches = re.findall(r'"([^"]+)"', content)
                    for m in matches:
                        if len(m) <= 32:
                            strings.add(m)
                
                if strings:
                    with open(dict_path, 'w') as f:
                        for s in strings:
                            # Simple escaping
                            s_esc = s.replace('\\', '\\\\').replace('"', '\\"')
                            f.write(f'"{s_esc}"\n')
            except Exception:
                pass

            # Run fuzzer
            # Use artifact_prefix to control where crashes are saved
            crash_prefix = os.path.join(temp_dir, 'crash-')
            fuzz_cmd = [
                fuzzer_bin,
                '-max_total_time=45',
                f'-artifact_prefix={crash_prefix}'
            ]
            if os.path.exists(dict_path):
                fuzz_cmd.append(f'-dict={dict_path}')

            try:
                subprocess.run(fuzz_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

            # Check for crashes
            crashes = glob.glob(f'{crash_prefix}*')
            if crashes:
                # Prefer smaller inputs
                crashes.sort(key=os.path.getsize)
                try:
                    with open(crashes[0], 'rb') as f:
                        return f.read()
                except IOError:
                    pass

            return b'A' * 9
