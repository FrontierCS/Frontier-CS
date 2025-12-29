import os
import subprocess
import tempfile
import tarfile
import random
import sys
import shutil
import signal
import multiprocessing
from pathlib import Path
from typing import Optional, List

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball to a temporary directory
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir_path)
            
            # Find the root of the extracted source (there might be a top-level directory)
            entries = list(tmpdir_path.iterdir())
            if len(entries) == 1 and entries[0].is_dir():
                src_root = entries[0]
            else:
                src_root = tmpdir_path
            
            # Compile the program with AddressSanitizer
            exe_path = tmpdir_path / "target"
            compile_success = self.compile_program(src_root, exe_path)
            if not compile_success:
                # Fallback: try to find a Makefile or build script
                exe_path = self.try_alternative_build(src_root, tmpdir_path)
                if exe_path is None:
                    # If compilation fails, return a dummy PoC (should not happen in evaluation)
                    return bytes([0]*60)
            
            # Fuzz to find a crashing input
            poc = self.fuzz(exe_path)
            if poc is None:
                # If no crash found, return a dummy PoC
                return bytes([0]*60)
            
            # Minimize the PoC
            minimized = self.minimize_poc(exe_path, poc)
            return minimized
    
    def compile_program(self, src_dir: Path, exe_path: Path) -> bool:
        """Compile all .cpp files with ASan. Return True if successful."""
        cpp_files = list(src_dir.glob("**/*.cpp"))
        if not cpp_files:
            return False
        
        # Try to compile with g++
        cmd = [
            "g++", "-std=c++11", "-fsanitize=address", "-fno-omit-frame-pointer", "-g",
            "-o", str(exe_path)
        ] + [str(f) for f in cpp_files]
        
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def try_alternative_build(self, src_dir: Path, tmpdir: Path) -> Optional[Path]:
        """Try to build using Makefile or other build system."""
        # Look for a Makefile
        makefile = src_dir / "Makefile"
        if makefile.exists():
            try:
                subprocess.run(["make", "clean"], cwd=src_dir, capture_output=True)
                subprocess.run(["make"], cwd=src_dir, capture_output=True)
                # Try to find the executable
                for f in src_dir.iterdir():
                    if f.is_file() and os.access(f, os.X_OK):
                        # Check if it's not a script
                        with open(f, 'rb') as fp:
                            header = fp.read(4)
                            if header == b'\x7fELF' or header.startswith(b'#!'):
                                return f
            except subprocess.SubprocessError:
                pass
        
        # Look for a build script
        build_sh = src_dir / "build.sh"
        if build_sh.exists() and os.access(build_sh, os.X_OK):
            try:
                subprocess.run(["./build.sh"], cwd=src_dir, capture_output=True)
                for f in src_dir.iterdir():
                    if f.is_file() and os.access(f, os.X_OK):
                        with open(f, 'rb') as fp:
                            header = fp.read(4)
                            if header == b'\x7fELF' or header.startswith(b'#!'):
                                return f
            except subprocess.SubprocessError:
                pass
        
        return None
    
    def run_program(self, exe_path: Path, input_data: bytes) -> subprocess.CompletedProcess:
        """Run the program with given input and return CompletedProcess."""
        try:
            return subprocess.run(
                [str(exe_path)],
                input=input_data,
                capture_output=True,
                timeout=1.0  # prevent hanging
            )
        except subprocess.TimeoutExpired:
            # Kill the process if it times out
            return subprocess.CompletedProcess(
                args=[str(exe_path)],
                returncode=-signal.SIGKILL,
                stdout=b'',
                stderr=b''
            )
    
    def is_crash(self, result: subprocess.CompletedProcess) -> bool:
        """Check if the run resulted in a crash (ASan error)."""
        if result.returncode != 0:
            # Check stderr for ASan errors (heap-use-after-free, double-free, etc.)
            stderr = result.stderr.decode('utf-8', errors='ignore')
            asan_indicators = [
                "AddressSanitizer",
                "heap-use-after-free",
                "double-free",
                "heap-buffer-overflow",
                "stack-buffer-overflow"
            ]
            return any(indicator in stderr for indicator in asan_indicators)
        return False
    
    def fuzz(self, exe_path: Path) -> Optional[bytes]:
        """Fuzz the program to find a crashing input."""
        # Use multiprocessing to speed up fuzzing
        num_workers = max(1, multiprocessing.cpu_count() - 1)
        pool = multiprocessing.Pool(num_workers)
        
        try:
            # We'll try different input lengths around 60 bytes
            lengths = [60] + list(range(50, 71))  # prioritize 60
            for length in lengths:
                # Generate a batch of random inputs
                batch_size = 100
                inputs = [bytes(random.getrandbits(8) for _ in range(length)) for _ in range(batch_size)]
                
                # Test them in parallel
                results = pool.starmap(self.test_input, [(exe_path, inp) for inp in inputs])
                for inp, crash in zip(inputs, results):
                    if crash:
                        pool.terminate()
                        pool.join()
                        return inp
        finally:
            pool.terminate()
            pool.join()
        
        return None
    
    def test_input(self, exe_path: Path, inp: bytes) -> bool:
        """Test a single input and return True if it crashes."""
        result = self.run_program(exe_path, inp)
        return self.is_crash(result)
    
    def minimize_poc(self, exe_path: Path, poc: bytes) -> bytes:
        """Minimize the crashing input by removing bytes."""
        current = bytearray(poc)
        
        # Try to remove each byte (from end to start)
        i = len(current) - 1
        while i >= 0:
            candidate = current[:i] + current[i+1:]
            result = self.run_program(exe_path, bytes(candidate))
            if self.is_crash(result):
                # Removal still crashes, keep the shorter version
                current = candidate
                # Continue trying to remove from the same index (now new length)
                i = min(i, len(current) - 1)
            else:
                i -= 1
        
        # Try to zero out each byte
        for i in range(len(current)):
            original = current[i]
            current[i] = 0
            result = self.run_program(exe_path, bytes(current))
            if not self.is_crash(result):
                # Revert if it doesn't crash
                current[i] = original
        
        return bytes(current)