import os
import tarfile
import tempfile
import subprocess
import random
import string
from pathlib import Path
from typing import Optional

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(tmpdir)
            
            # Find the root directory (usually one level deep)
            extracted_items = list(Path(tmpdir).iterdir())
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                src_root = extracted_items[0]
            else:
                src_root = Path(tmpdir)
            
            # Try different approaches to generate PoC
            poc = self._try_compile_fuzzer(src_root)
            if poc:
                return poc
            
            poc = self._try_pattern_based(src_root)
            if poc:
                return poc
            
            # Fallback: generate synthetic data with patterns known to trigger uninitialized values
            return self._generate_fallback_poc()
    
    def _try_compile_fuzzer(self, src_root: Path) -> Optional[bytes]:
        """Try to compile and run existing fuzzer to generate PoC"""
        try:
            # Look for fuzzer source files
            fuzzer_files = list(src_root.rglob('*fuzz*.c')) + list(src_root.rglob('*fuzz*.cpp'))
            if not fuzzer_files:
                return None
            
            fuzzer_src = fuzzer_files[0]
            
            # Create a simple harness to capture crashing input
            harness = """
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

extern int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size);

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <input_file>\\n", argv[0]);
        return 1;
    }
    
    FILE *f = fopen(argv[1], "rb");
    if (!f) {
        perror("Failed to open input file");
        return 1;
    }
    
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    
    uint8_t *data = (uint8_t*)malloc(size);
    if (!data) {
        fclose(f);
        return 1;
    }
    
    fread(data, 1, size, f);
    fclose(f);
    
    int result = LLVMFuzzerTestOneInput(data, size);
    free(data);
    return result;
}
"""
            
            # Compile with memory sanitizer
            compile_cmd = [
                'clang', '-fsanitize=memory', '-fno-omit-frame-pointer', '-g',
                '-O2', str(fuzzer_src), '-c', '-o', 'fuzzer.o'
            ]
            
            subprocess.run(compile_cmd, cwd=src_root, capture_output=True, timeout=30)
            
            # Compile harness
            with open(src_root / 'harness.c', 'w') as f:
                f.write(harness)
            
            compile_harness = [
                'clang', '-fsanitize=memory', '-fno-omit-frame-pointer', '-g',
                '-O2', 'harness.c', 'fuzzer.o', '-o', 'fuzzer'
            ]
            
            result = subprocess.run(compile_harness, cwd=src_root, capture_output=True, timeout=30)
            if result.returncode != 0:
                return None
            
            # Try to generate crash with fuzzing
            for _ in range(100):
                test_input = self._generate_test_case()
                test_file = src_root / 'test_input'
                with open(test_file, 'wb') as f:
                    f.write(test_input)
                
                run_result = subprocess.run(
                    ['./fuzzer', 'test_input'],
                    cwd=src_root,
                    capture_output=True,
                    timeout=5
                )
                
                if run_result.returncode != 0:
                    # Found a crashing input
                    return test_input
            
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError):
            pass
        
        return None
    
    def _try_pattern_based(self, src_root: Path) -> Optional[bytes]:
        """Try to generate PoC based on common patterns for uninitialized value vulnerabilities"""
        # Common patterns that often trigger uninitialized value issues
        patterns = [
            # Large input with null bytes
            b'\x00' * 100 + b'A' * 100,
            # Malformed structures with invalid lengths
            b'\xff\xff\xff\xff' * 50,
            # Input that triggers edge cases in parsing
            b'\x01' + b'\x00' * 2178,
            # Pattern that might trigger attribute conversion issues
            b'attr=' + b'\xff' * 100 + b'&' + b'\x00' * 100,
        ]
        
        # Try each pattern
        for pattern in patterns:
            if self._test_pattern(src_root, pattern):
                return pattern
        
        return None
    
    def _test_pattern(self, src_root: Path, test_input: bytes) -> bool:
        """Test if a pattern causes a crash"""
        try:
            # Look for any executable that might accept input
            executables = list(src_root.rglob('*test*')) + list(src_root.rglob('*demo*'))
            executables = [e for e in executables if e.is_file() and os.access(e, os.X_OK)]
            
            if not executables:
                return False
            
            exe = executables[0]
            test_file = src_root / 'test_pattern'
            with open(test_file, 'wb') as f:
                f.write(test_input)
            
            # Try running with the test input
            result = subprocess.run(
                [str(exe), str(test_file)],
                cwd=src_root,
                capture_output=True,
                timeout=5
            )
            
            return result.returncode != 0
            
        except (subprocess.TimeoutExpired, PermissionError):
            return False
    
    def _generate_test_case(self) -> bytes:
        """Generate a test case with various patterns"""
        # Start with the ground truth length hint
        length = 2179
        
        # Mix different patterns that might trigger uninitialized reads
        parts = []
        
        # 1. Valid structure header (if any)
        parts.append(b'\x01\x00\x00\x00')  # Possible length field
        
        # 2. Malformed data that might cause failed conversions
        parts.append(b'attr=' + b'\xff' * 100)
        parts.append(b'&type=' + b'invalid\x00')
        
        # 3. Padding with zeros (common for uninitialized memory)
        parts.append(b'\x00' * 500)
        
        # 4. Random data to trigger edge cases
        random_part = ''.join(random.choices(string.printable, k=300)).encode('ascii', 'ignore')
        parts.append(random_part)
        
        # 5. More structured but invalid data
        parts.append(b'\xff\xff\xff\xff' * 10)  # Maximum values
        
        # 6. Valid-looking but problematic data
        parts.append(b'name=' + b'A' * 200 + b'\x00')
        parts.append(b'value=' + b'\x01' * 50 + b'\x00')
        
        # Combine and trim to target length
        combined = b''.join(parts)
        if len(combined) > length:
            return combined[:length]
        else:
            # Pad to target length
            return combined + b'\x00' * (length - len(combined))
    
    def _generate_fallback_poc(self) -> bytes:
        """Generate a fallback PoC when other methods fail"""
        # Create input that is likely to trigger uninitialized value issues
        # Based on common patterns in attribute parsing vulnerabilities
        
        # Structure: attribute=value pairs with malformed data
        parts = []
        
        # Start with what looks like a valid attribute
        parts.append(b'attribute=')
        
        # Add uninitialized-like data (mix of zeros and garbage)
        parts.append(b'\x00' * 100)
        parts.append(b'\xff' * 50)
        parts.append(b'\x00' * 50)
        
        # Add delimiter that might not be properly handled
        parts.append(b'&')
        
        # Another attribute with invalid data
        parts.append(b'type=')
        parts.append(b'\xff' * 100)
        
        # More delimiters and data
        parts.append(b'&data=')
        
        # Pattern that might cause conversion failure
        for i in range(100):
            parts.append(bytes([i % 256]))
        
        # Add null terminators in middle of data
        parts.append(b'\x00' * 10)
        
        # Add more structured but invalid data
        parts.append(b'length=')
        parts.append(b'999999999')
        parts.append(b'&')
        
        # Fill remaining space with pattern
        combined = b''.join(parts)
        remaining = 2179 - len(combined)
        
        if remaining > 0:
            # Add cyclic pattern that might expose uninitialized memory
            pattern = b'ABCD' * (remaining // 4)
            pattern += b'A' * (remaining % 4)
            combined += pattern
        
        return combined[:2179]
