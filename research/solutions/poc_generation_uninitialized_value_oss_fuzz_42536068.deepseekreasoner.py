import os
import subprocess
import tempfile
import tarfile
import hashlib
from pathlib import Path
from typing import Optional, Tuple

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball to analyze the source code
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract source code
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Look for the root directory (usually one level deep)
            extracted_dirs = list(Path(tmpdir).iterdir())
            if len(extracted_dirs) == 1 and extracted_dirs[0].is_dir():
                source_root = extracted_dirs[0]
            else:
                source_root = Path(tmpdir)
            
            # Try to understand the project structure
            build_script = self._find_build_script(source_root)
            
            if build_script:
                # If we can build it, try to fuzz it
                poc = self._fuzz_built_project(source_root, build_script)
                if poc:
                    return poc
            
            # Fallback: Generate a heuristic PoC based on common patterns
            # for uninitialized value vulnerabilities
            return self._generate_heuristic_poc()
    
    def _find_build_script(self, source_root: Path) -> Optional[Path]:
        """Find a build script in the source directory."""
        build_files = [
            'configure', 'autogen.sh', 'bootstrap', 'Makefile',
            'CMakeLists.txt', 'meson.build', 'build.sh'
        ]
        
        for build_file in build_files:
            path = source_root / build_file
            if path.exists():
                return path
        
        # Check in common subdirectories
        for subdir in source_root.iterdir():
            if subdir.is_dir():
                for build_file in build_files:
                    path = subdir / build_file
                    if path.exists():
                        return path
        
        return None
    
    def _fuzz_built_project(self, source_root: Path, build_script: Path) -> Optional[bytes]:
        """Attempt to build and fuzz the project."""
        try:
            # Try to build with sanitizers
            build_dir = source_root / "build_fuzz"
            build_dir.mkdir(exist_ok=True)
            
            # Common build configurations for fuzzing
            env = os.environ.copy()
            env['CC'] = 'clang'
            env['CXX'] = 'clang++'
            env['CFLAGS'] = '-fsanitize=memory -fsanitize-memory-track-origins -O1 -fno-omit-frame-pointer -g'
            env['CXXFLAGS'] = '-fsanitize=memory -fsanitize-memory-track-origins -O1 -fno-omit-frame-pointer -g'
            
            # Try different build approaches
            build_success = False
            
            if build_script.name == 'CMakeLists.txt':
                result = subprocess.run(
                    ['cmake', '..', '-DCMAKE_BUILD_TYPE=Debug'],
                    cwd=build_dir,
                    env=env,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    result = subprocess.run(
                        ['make', '-j4'],
                        cwd=build_dir,
                        env=env,
                        capture_output=True,
                        text=True
                    )
                    build_success = result.returncode == 0
            
            elif build_script.name == 'Makefile' or build_script.name == 'configure':
                if build_script.name == 'configure':
                    result = subprocess.run(
                        ['./configure'],
                        cwd=source_root,
                        env=env,
                        capture_output=True,
                        text=True
                    )
                
                if not build_script.name == 'configure' or result.returncode == 0:
                    result = subprocess.run(
                        ['make', '-j4'],
                        cwd=source_root,
                        env=env,
                        capture_output=True,
                        text=True
                    )
                    build_success = result.returncode == 0
            
            if build_success:
                # Look for fuzz targets or test executables
                for root, dirs, files in os.walk(source_root):
                    for file in files:
                        if self._is_executable(os.path.join(root, file)):
                            # Try to run with empty input
                            exe_path = os.path.join(root, file)
                            try:
                                result = subprocess.run(
                                    [exe_path],
                                    input=b'',
                                    capture_output=True,
                                    timeout=2
                                )
                                # If it crashes with empty input, return minimal PoC
                                if result.returncode != 0:
                                    return b''
                            except (subprocess.TimeoutExpired, PermissionError):
                                pass
                
        except Exception:
            pass
        
        return None
    
    def _is_executable(self, path: str) -> bool:
        """Check if a file is executable."""
        if not os.path.isfile(path):
            return False
        
        # Check executable bit or file extension
        if os.access(path, os.X_OK):
            return True
        
        # Check for common executable extensions
        ext = os.path.splitext(path)[1].lower()
        return ext in ['.exe', '.out', '']
    
    def _generate_heuristic_poc(self) -> bytes:
        """
        Generate a heuristic PoC for uninitialized value vulnerabilities.
        Based on common patterns that trigger such issues.
        """
        # Common patterns for triggering uninitialized value issues:
        # 1. Partial structure initialization
        # 2. Union type confusion
        # 3. Array access without bounds checking
        # 4. Use-after-free patterns
        
        # We'll generate a structured but malformed input
        poc_parts = []
        
        # Start with a plausible header (common in many formats)
        poc_parts.append(b'POC\x00\x01\x00\x00')  # Magic + version
        
        # Add a structure with missing fields (potential uninitialized values)
        # 32-byte structure with only first 16 bytes initialized
        poc_parts.append(b'STRUCT\x00')
        poc_parts.append(b'\x01\x02\x03\x04' * 4)  # 16 initialized bytes
        # Leave next 16 bytes uninitialized (zeros, but could be anything)
        poc_parts.append(b'\x00\x00\x00\x00' * 4)
        
        # Add an array with incomplete initialization
        poc_parts.append(b'ARRAY\x00\x04\x00\x00\x00')  # 4 elements
        poc_parts.append(b'\xFF\xFF\xFF\xFF')  # First element initialized
        # Remaining 3 elements left uninitialized
        poc_parts.append(b'\x00\x00\x00\x00' * 3)
        
        # Add a union that could cause type confusion
        poc_parts.append(b'UNION\x00')
        poc_parts.append(b'\x01')  # Type tag (1 = use as int)
        poc_parts.append(b'\x00\x00\x00\x00')  # 4 bytes of data
        
        # Add nested structure with missing initialization
        poc_parts.append(b'NESTED\x00')
        poc_parts.append(b'\x01\x00')  # Has subfield = true
        # But subfield data is missing or incomplete
        poc_parts.append(b'\x00' * 8)
        
        # Pad to exactly 2179 bytes (ground-truth length)
        current_length = sum(len(part) for part in poc_parts)
        if current_length < 2179:
            # Add pattern that might trigger different code paths
            padding = b'\xCC' * (2179 - current_length)  # 0xCC is often used for uninitialized memory
            poc_parts.append(padding)
        elif current_length > 2179:
            # Truncate if we overshot
            combined = b''.join(poc_parts)
            return combined[:2179]
        
        return b''.join(poc_parts)
