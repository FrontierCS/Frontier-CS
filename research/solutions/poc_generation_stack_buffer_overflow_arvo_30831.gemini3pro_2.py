import os
import sys
import tarfile
import tempfile
import subprocess
import shutil
import glob
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        Args:
            src_path: Path to the vulnerable source code tarball
            
        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        base_dir = tempfile.mkdtemp()
        
        try:
            # Extract source code
            with tarfile.open(src_path) as tar:
                tar.extractall(path=base_dir)
            
            # Determine the root directory of the source
            src_root = base_dir
            items = os.listdir(base_dir)
            if len(items) == 1 and os.path.isdir(os.path.join(base_dir, items[0])):
                src_root = os.path.join(base_dir, items[0])
            
            # Detect project type and solve
            if os.path.exists(os.path.join(src_root, "go.mod")):
                return self._solve_go(src_root)
            else:
                return self._solve_cpp(src_root)
                
        except Exception:
            return b""
        finally:
            shutil.rmtree(base_dir, ignore_errors=True)

    def _solve_go(self, src_root):
        # Identify the Fuzz function
        fuzz_target = None
        for root, dirs, files in os.walk(src_root):
            for file in files:
                if file.endswith("_test.go"):
                    try:
                        with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            # Look for func FuzzName(f *testing.F)
                            m = re.search(r'func\s+(Fuzz\w+)\s*\(', content)
                            if m:
                                fuzz_target = m.group(1)
                                break
                    except:
                        continue
            if fuzz_target:
                break
        
        if not fuzz_target:
            return b""
            
        # Run Go fuzzer
        # We rely on 'go' being in the PATH
        cmd = ["go", "test", "-fuzz", fuzz_target, "-fuzztime", "45s", "./..."]
        try:
            # Run fuzzer, ignore exit code as we expect a crash
            subprocess.run(cmd, cwd=src_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        except:
            pass
            
        # Locate the crash file
        # Typically in testdata/fuzz/<FuzzName>/
        crash_dir = os.path.join(src_root, "testdata", "fuzz", fuzz_target)
        # Search if path is slightly different
        if not os.path.exists(crash_dir):
            for root, dirs, files in os.walk(src_root):
                if fuzz_target in root and "testdata" in root:
                    crash_dir = root
                    break
        
        if os.path.exists(crash_dir):
            candidates = [os.path.join(crash_dir, f) for f in os.listdir(crash_dir) if os.path.isfile(os.path.join(crash_dir, f))]
            # Sort by modification time to find the most recent (the crash)
            candidates.sort(key=os.path.getmtime, reverse=True)
            
            for c in candidates:
                data = self._parse_go_fuzz_file(c)
                if data:
                    return data
        return b""

    def _parse_go_fuzz_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Go fuzz corpus format:
            # go test fuzz v1
            # []byte("...")
            m = re.search(r'\[\]byte\("(.*)"\)', content)
            if m:
                escaped = m.group(1)
                # Unescape using Python's eval to handle standard escape sequences compatible with Go
                return eval(f'b"{escaped}"')
        except:
            pass
        return b""

    def _solve_cpp(self, src_root):
        fuzz_file = None
        sources = []
        includes = set()
        
        # Scan for source files and headers
        for root, dirs, files in os.walk(src_root):
            for file in files:
                filepath = os.path.join(root, file)
                if file.endswith(('.h', '.hpp')):
                    includes.add(root)
                elif file.endswith(('.c', '.cpp', '.cc', '.cxx')):
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if "LLVMFuzzerTestOneInput" in content:
                            fuzz_file = filepath
                        elif re.search(r'\bint\s+main\s*\(', content):
                            # Skip files containing main() to avoid link errors
                            pass
                        else:
                            sources.append(filepath)
                            
        if not fuzz_file:
            return b""
            
        compiler = "clang++"
        out_bin = os.path.join(src_root, "fuzz_bin")
        inc_flags = [f"-I{d}" for d in includes]
        
        # Compile command
        cmd = [compiler, "-g", "-O1", "-fsanitize=address,fuzzer", fuzz_file] + sources + inc_flags + ["-o", out_bin]
        
        try:
            subprocess.run(cmd, cwd=src_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            # Fallback strategy: compile only the fuzz target (in case it includes implementations)
            try:
                cmd = [compiler, "-g", "-O1", "-fsanitize=address,fuzzer", fuzz_file] + inc_flags + ["-o", out_bin]
                subprocess.run(cmd, cwd=src_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except:
                return b""
                
        # Run Fuzzer
        try:
            # -max_total_time=45s gives enough time to find simple overflows
            # -artifact_prefix=crash- ensures we know the filename prefix
            subprocess.run([out_bin, "-max_total_time=45", "-artifact_prefix=crash-"], 
                           cwd=src_root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=50)
        except:
            pass
            
        # Locate crash artifact
        crashes = glob.glob(os.path.join(src_root, "crash-*"))
        if crashes:
            # Return the shortest crash file (higher score for shorter PoC)
            crashes.sort(key=os.path.getsize)
            with open(crashes[0], 'rb') as f:
                return f.read()
                
        return b""
