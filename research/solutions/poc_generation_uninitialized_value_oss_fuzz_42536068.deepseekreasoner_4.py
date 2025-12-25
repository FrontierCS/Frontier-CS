import tarfile
import tempfile
import os
import subprocess
import shutil
from pathlib import Path
import random

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:*') as tar:
                tar.extractall(tmpdir)
            
            # Find the root directory (assuming single top-level dir)
            extracted_items = list(Path(tmpdir).iterdir())
            if len(extracted_items) != 1 or not extracted_items[0].is_dir():
                # Fallback: use the tmpdir directly if structure is different
                source_root = Path(tmpdir)
            else:
                source_root = extracted_items[0]
            
            # Look for build configuration files
            build_sh = source_root / "build.sh"
            if build_sh.exists():
                # Build the project
                self._build_project(str(source_root))
                
                # Look for fuzz target binaries
                fuzz_target = self._find_fuzz_target(str(source_root))
                if fuzz_target:
                    # Generate PoC using the fuzzer
                    poc = self._generate_fuzz_input(fuzz_target)
                    if poc:
                        return poc
            
            # Fallback: generic PoC for uninitialized value vulnerabilities
            return self._generate_generic_poc()
    
    def _build_project(self, source_dir: str):
        """Attempt to build the project."""
        try:
            # Try common build patterns
            build_sh = os.path.join(source_dir, "build.sh")
            if os.path.exists(build_sh):
                subprocess.run(
                    ["bash", build_sh],
                    cwd=source_dir,
                    capture_output=True,
                    timeout=300
                )
            
            # Try CMake
            cmakelists = os.path.join(source_dir, "CMakeLists.txt")
            if os.path.exists(cmakelists):
                build_dir = os.path.join(source_dir, "build")
                os.makedirs(build_dir, exist_ok=True)
                subprocess.run(
                    ["cmake", ".."],
                    cwd=build_dir,
                    capture_output=True,
                    timeout=300
                )
                subprocess.run(
                    ["make", "-j", "8"],
                    cwd=build_dir,
                    capture_output=True,
                    timeout=300
                )
        except Exception:
            pass
    
    def _find_fuzz_target(self, source_dir: str) -> str:
        """Find fuzz target executable."""
        # Common fuzz target locations and patterns
        search_paths = [
            os.path.join(source_dir, "build"),
            os.path.join(source_dir, "out"),
            source_dir
        ]
        
        patterns = [
            "*fuzz*",
            "*Fuzz*",
            "*_fuzzer",
            "*_fuzz_target*",
            "fuzz*"
        ]
        
        for search_path in search_paths:
            if os.path.exists(search_path):
                for pattern in patterns:
                    for path in Path(search_path).rglob(pattern):
                        if os.access(str(path), os.X_OK):
                            return str(path)
        
        return None
    
    def _generate_fuzz_input(self, fuzz_target: str) -> bytes:
        """Generate input using the fuzzer."""
        try:
            # Try to run the fuzzer with a minimal input to see format
            test_input = b"A" * 100
            result = subprocess.run(
                [fuzz_target],
                input=test_input,
                capture_output=True,
                timeout=5
            )
            
            # If it runs without immediate crash, try to generate more complex input
            # that might trigger uninitialized value issues
            return self._generate_structured_poc()
        except Exception:
            return self._generate_generic_poc()
    
    def _generate_structured_poc(self) -> bytes:
        """Generate structured PoC that might trigger uninitialized value issues."""
        # Common patterns that can trigger uninitialized value vulnerabilities:
        # 1. Incomplete or malformed headers
        # 2. Missing required fields
        # 3. Invalid type conversions
        # 4. Boundary conditions
        
        poc_parts = []
        
        # Start with some valid header-like data
        poc_parts.append(b"HEADER")
        poc_parts.append(b"\x00" * 16)  # Potential uninitialized padding
        
        # Add various data types that might cause conversion issues
        for _ in range(10):
            # Mix of valid and invalid data
            poc_parts.append(struct.pack("<I", random.randint(0, 0xFFFFFFFF)))
            poc_parts.append(b"\xff" * 4)  # Invalid values
            poc_parts.append(b"\x00" * 8)  # Null data
        
        # Add malformed structure that might skip initialization
        poc_parts.append(b"\x01")  # Some flag
        poc_parts.append(b"\x00" * 255)  # Large zeroed area
        poc_parts.append(b"\xff" * 128)  # Garbage data
        
        # Add incomplete data structures
        poc_parts.append(struct.pack("<H", 0xFFFF))  # Max length
        poc_parts.append(b"\x00" * 100)  # But only partial data
        
        # Add edge cases
        poc_parts.append(b"\x80")  # High bit set
        poc_parts.append(b"\x00" * 63)
        poc_parts.append(b"\x01" * 64)
        
        poc = b"".join(poc_parts)
        
        # Ensure it's close to the target length (2179 bytes)
        if len(poc) < 2179:
            poc += b"\x00" * (2179 - len(poc))
        else:
            poc = poc[:2179]
        
        return poc
    
    def _generate_generic_poc(self) -> bytes:
        """Generate generic PoC for uninitialized value vulnerabilities."""
        # Create input that maximizes chances of hitting uninitialized memory:
        # 1. Varying patterns to defeat compression/optimization
        # 2. Partial structures
        # 3. Invalid sequences
        
        patterns = [
            b"\x00",  # Null bytes (common in uninitialized memory)
            b"\xff",  # All bits set
            b"\xaa",  # Alternating bits 10101010
            b"\x55",  # Alternating bits 01010101
            b"\xcc",  # Alternating bytes 11001100
            b"\x33",  # Alternating bytes 00110011
        ]
        
        # Build PoC with changing patterns to hit different code paths
        poc_parts = []
        current_pattern = 0
        
        for i in range(2179):
            # Change pattern every 64 bytes to create varied input
            if i % 64 == 0:
                current_pattern = (current_pattern + 1) % len(patterns)
            
            # Every 128 bytes, insert a special marker
            if i % 128 == 0:
                poc_parts.append(b"\x7f")  # DEL character
            elif i % 256 == 128:
                poc_parts.append(b"\x80")  # High bit set
            elif i % 512 == 256:
                poc_parts.append(b"\x00")  # Null byte cluster
            elif i % 1024 == 512:
                # Add what might look like a length field
                poc_parts.append(struct.pack("<H", 0xFFFF)[:1])
            else:
                poc_parts.append(patterns[current_pattern])
        
        poc = b"".join(poc_parts)
        
        # Trim or pad to exactly 2179 bytes
        if len(poc) > 2179:
            poc = poc[:2179]
        elif len(poc) < 2179:
            poc += b"\x00" * (2179 - len(poc))
        
        return poc

# Add struct import at the end since we use it in the methods
import struct
